# MCP Tool Lücken — Design Spec

## Übersicht

13 neue MCP-Tools für die FreeCAD-Bridge, basierend auf ~30+ `execute_python`-Aufrufen während der BIM-Modellierung von "MONOLITH – Residenz 01".

## Architektur

Zweischichtig wie bestehend:
- **MCP Server** (`mcp_server.py`): Jedes Tool als `@mcp.tool()` → XML-RPC-Aufruf an Bridge
- **Bridge** (`freecad_bridge.py`): Jedes Tool als Methode auf `RobustFreeCADBridge` → FreeCAD API

Bestehende Muster werden konsequent weitergeführt: `_get_obj()`, `_parse_unit()`, `to_vector()`, Fehlerbehandlung.

## Tool 1: `get_object_info` — Hoch

**MCP:**
```python
def get_object_info(object_name: str) -> str:
```

**Bridge:** `objekt_info_abrufen(name)`

Gibt strukturierten String zurück:
- Typ, Label, Name
- Bounding Box (Xmin/Xmax, Ymin/Ymax, Zmin/Zmax)
- Align, Width, Height, Length (falls vorhanden)
- State, Volume (falls Shape existiert)
- Base-Wire Start/End (für Wände: `obj.Base.Shape.Vertexes`)

Implementierung:
```python
def objekt_info_abrufen(self, name):
    obj = self._get_obj(name)
    if not obj: return "Nicht gefunden."
    lines = [f"Label: {obj.Label}", f"Name: {obj.Name}", f"Type: {obj.TypeId}"]
    if hasattr(obj, "Shape") and obj.Shape:
        bb = obj.Shape.BoundBox
        lines.append(f"BBox: X({bb.XMin:.1f}..{bb.XMax:.1f}) Y({bb.YMin:.1f}..{bb.YMax:.1f}) Z({bb.ZMin:.1f}..{bb.ZMax:.1f})")
        lines.append(f"Volume: {obj.Shape.Volume:.1f}")
    for attr in ["Align", "Width", "Height", "Length"]:
        if hasattr(obj, attr):
            lines.append(f"{attr}: {getattr(obj, attr)}")
    if hasattr(obj, "State"):
        lines.append(f"State: {obj.State}")
    if hasattr(obj, "Base") and obj.Base and hasattr(obj.Base, "Shape"):
        vs = obj.Base.Shape.Vertexes
        if len(vs) >= 2:
            lines.append(f"Start: ({vs[0].Point.x:.1f}, {vs[0].Point.y:.1f}, {vs[0].Point.z:.1f})")
            lines.append(f"End: ({vs[-1].Point.x:.1f}, {vs[-1].Point.y:.1f}, {vs[-1].Point.z:.1f})")
    return "\n".join(lines)
```

---

## Tool 2: `rename_object` — Hoch

**MCP:**
```python
def rename_object(object: str, new_label: str) -> str:
```

**Bridge:** `umbenennen_objekt(obj_name, neues_label)`

```python
def umbenennen_objekt(self, obj_name, neues_label):
    obj = self._get_obj(obj_name)
    if not obj: return "Nicht gefunden."
    obj.Label = neues_label
    App.ActiveDocument.recompute()
    return f"Umbenannt: {obj.Name} -> '{neues_label}'"
```

---

## Tool 3: `set_visibility` — Hoch

**MCP:**
```python
def set_visibility(object: str, visible: bool) -> str:
```

**Bridge:** `sichtbarkeit_setzen(name, sichtbar)`

```python
def sichtbarkeit_setzen(self, name, sichtbar):
    obj = self._get_obj(name)
    if not obj: return "Nicht gefunden."
    if hasattr(obj, "ViewObject") and obj.ViewObject:
        obj.ViewObject.Visibility = bool(sichtbar)
        return f"Sichtbarkeit {name}: {sichtbar}"
    return "Kein ViewObject."
```

---

## Tool 4: `move_line` — Hoch

**MCP:**
```python
def move_line(line: str, start: list[float], end: list[float]) -> str:
```
`start`/`end` in Metern.

**Bridge:** `linie_verschieben(name, start_pkt, end_pkt)`

Punkte werden via `to_vector()` konvertiert (×1000 für Float-Listen). Draft-Linien haben `StartPoint`/`EndPoint`-Properties.

```python
def linie_verschieben(self, name, start_pkt, end_pkt):
    obj = self._get_obj(name)
    if not obj: return "Nicht gefunden."
    if not hasattr(obj, "StartPoint") or not hasattr(obj, "EndPoint"):
        return "Keine Draft-Linie."
    obj.StartPoint = self.to_vector(start_pkt)
    obj.EndPoint = self.to_vector(end_pkt)
    App.ActiveDocument.recompute()
    return f"Linie {name} verschoben."
```

---

## Tool 5: `set_wall_alignment` — Mittel

**MCP:**
```python
def set_wall_alignment(wall: str, ref_at_outside: bool = True) -> str:
```

**Bridge:** `wand_ausrichtung_setzen(wand_name, ref_aussen)`

Shifted die Baseline an Außenkante + setzt Align, ohne die Wandgeometrie zu bewegen.

```python
def wand_ausrichtung_setzen(self, wand_name, ref_aussen=True):
    wall = self._get_obj(wand_name)
    if not wall: return "Nicht gefunden."
    if not hasattr(wall, "Base") or not wall.Base: return "Keine Basislinie."
    vs = wall.Base.Shape.Vertexes
    if len(vs) < 2: return "Ungültige Basis."
    v_start, v_ende = vs[0].Point, vs[-1].Point
    w_dir = (v_ende - v_start).normalize()
    w_breite = self._parse_unit(wall.Width) if hasattr(wall, "Width") else 200
    linke_normale = App.Vector(0, 0, 1).cross(w_dir).normalize()
    versatz = w_breite / 2.0
    if ref_aussen:
        wall.Base.StartPoint = v_start + linke_normale * versatz
        wall.Base.EndPoint = v_ende + linke_normale * versatz
        wall.Align = "Right"
    else:
        wall.Base.StartPoint = v_start - linke_normale * versatz
        wall.Base.EndPoint = v_ende - linke_normale * versatz
        wall.Align = "Left"
    App.ActiveDocument.recompute()
    return f"Ausrichtung gesetzt: {wand_name}, ref_aussen={ref_aussen}"
```

---

## Tool 6: `boolean_cut_finalize` — Mittel

**MCP:**
```python
def boolean_cut_finalize(
    cut_result: str,
    new_label: str,
    container: str = "",
    hide_sources: bool = True
) -> str:
```

**Bridge:** `bool_cut_finalisieren(schnitt_name, neues_label, container, verstecken)`

```python
def bool_cut_finalisieren(self, schnitt_name, neues_label, container="", verstecken=True):
    cut = self._get_obj(schnitt_name)
    if not cut: return "Nicht gefunden."
    cut.Label = neues_label
    if verstecken:
        if hasattr(cut, "Base") and cut.Base and hasattr(cut.Base, "ViewObject"):
            cut.Base.ViewObject.Visibility = False
        if hasattr(cut, "Tool") and cut.Tool and hasattr(cut.Tool, "ViewObject"):
            cut.Tool.ViewObject.Visibility = False
    if container:
        cont = self._get_obj(container)
        if cont:
            if hasattr(cont, "addObject"): cont.addObject(cut)
            elif hasattr(cont, "Group"):
                g = list(cont.Group); g.append(cut); cont.Group = g
    App.ActiveDocument.recompute()
    return f"Finalisiert: {neues_label}"
```

---

## Tool 7: `create_opening` — Hoch

**MCP:**
```python
def create_opening(
    base_object: str,
    shape: str = "rectangle",
    position: list[float] = [0.0, 0.0, 0.0],
    size: list[float] = [1.0, 1.0, 0.2],
    name: str = "Oeffnung"
) -> str:
```

**Bridge:** `erstelle_oeffnung(base_obj_name, form, pos, groesse, name)`

Position in Metern (→ ×1000 in bridge). Erzeugt Boolean-Cut mit versteckten Quellen.

```python
def erstelle_oeffnung(self, base_obj_name, form="rectangle", pos=None, groesse=None, name="Oeffnung"):
    if pos is None: pos = [0, 0, 0]
    if groesse is None: groesse = [1, 1, 0.2]
    doc = App.ActiveDocument
    base = self._get_obj(base_obj_name)
    if not base: return "Base nicht gefunden."
    pos_v = self.to_vector(pos)
    g_x = groesse[0] * 1000.0 if isinstance(groesse[0], (int, float)) else self._parse_unit(groesse[0])
    g_y = groesse[1] * 1000.0 if isinstance(groesse[1], (int, float)) else self._parse_unit(groesse[1])
    g_z = groesse[2] * 1000.0 if isinstance(groesse[2], (int, float)) else self._parse_unit(groesse[2])
    tool = doc.addObject("Part::Box", "OpeningTool")
    tool.Length, tool.Width, tool.Height = g_x, g_y, g_z
    tool.Placement.Base = pos_v
    cut = doc.addObject("Part::Cut", name)
    cut.Base, cut.Tool = base, tool
    if hasattr(base, "ViewObject"): base.ViewObject.Visibility = False
    if hasattr(tool, "ViewObject"): tool.ViewObject.Visibility = False
    cut.Label = name
    doc.recompute()
    return f"Öffnung: {cut.Label}"
```

---

## Tool 8: `copy_to_floor` — Hoch

**MCP:**
```python
def copy_to_floor(
    source_walls: list[str],
    target_floor: str,
    z_offset: float = 3.24,
    x_extension: float = 0.0
) -> str:
```

**Bridge:** `kopiere_nach_geschoss(wand_liste, ziel_geschoss, z_versatz, x_verlaengerung)`

Kopiert Wände auf Zielgeschoss-Höhe. `z_offset` in Metern.

```python
def kopiere_nach_geschoss(self, wand_liste, ziel_geschoss, z_versatz=3.24, x_verlaengerung=0.0):
    import Arch, Draft
    doc = App.ActiveDocument
    z_mm = z_versatz * 1000.0
    x_ext_mm = x_verlaengerung * 1000.0
    ziel = self._get_obj(ziel_geschoss)
    created = []
    for wn in wand_liste:
        src = self._get_obj(wn)
        if not src: continue
        if hasattr(src, "Base") and src.Base:
            vs = src.Base.Shape.Vertexes
            v1, v2 = vs[0].Point, vs[-1].Point
            v1_new = App.Vector(v1.x, v1.y, v1.z + z_mm)
            v2_new = App.Vector(v2.x, v2.y, v2.z + z_mm)
            if x_ext_mm != 0.0:
                richtung = (v2 - v1).normalize()
                v2_new = v2_new + richtung * x_ext_mm
            new_line = Draft.make_line(v1_new, v2_new)
            if hasattr(new_line, "ViewObject"): new_line.ViewObject.Visibility = False
            new_wall = Arch.makeWall(new_line)
            new_wall.Width = src.Width if hasattr(src, "Width") else 300
            new_wall.Height = src.Height if hasattr(src, "Height") else 2500
            new_wall.Align = src.Align if hasattr(src, "Align") else "Left"
            new_wall.Label = f"{src.Label}_OG"
            if ziel:
                if hasattr(ziel, "addObject"): ziel.addObject(new_wall)
                elif hasattr(ziel, "Group"):
                    g = list(ziel.Group); g.append(new_wall); ziel.Group = g
            created.append(new_wall.Label)
    doc.recompute()
    return f"Kopiert: {', '.join(created)}"
```

---

## Tool 9: `create_attika` — Hoch

**MCP:**
```python
def create_attika(
    roof_slab: str,
    height: float = 0.3,
    thickness: float = 0.365,
    offset: float = 0.0,
    name_prefix: str = "Attika"
) -> str:
```

**Bridge:** `erstelle_attika(platte_name, hoehe, dicke, versatz, prefix)`

Extrahiert Perimeter aus der Slab-Basis und erzeugt Wände entlang jeder Kante.

```python
def erstelle_attika(self, platte_name, hoehe=0.3, dicke=0.365, versatz=0.0, prefix="Attika"):
    import Arch, Draft
    doc = App.ActiveDocument
    slab = self._get_obj(platte_name)
    if not slab: return "Platte nicht gefunden."
    h_mm = hoehe * 1000.0; d_mm = dicke * 1000.0; v_mm = versatz * 1000.0
    base_shape = slab.Base if hasattr(slab, "Base") and slab.Base else slab
    shape = base_shape.Shape if hasattr(base_shape, "Shape") else None
    if not shape: return "Keine Shape."
    wires = shape.Wires
    if not wires: return "Keine Drähte."
    edges = wires[0].Edges if wires[0].isClosed() else wires[0].Edges
    created = []
    for i, edge in enumerate(edges):
        v1, v2 = edge.Vertexes[0].Point, edge.Vertexes[-1].Point
        if v_mm != 0.0:
            e_dir = (v2 - v1).normalize()
            n_dir = App.Vector(0, 0, 1).cross(e_dir).normalize()
            v1 += n_dir * v_mm; v2 += n_dir * v_mm
        line = Draft.make_line(v1, v2)
        if hasattr(line, "ViewObject"): line.ViewObject.Visibility = False
        wall = Arch.makeWall(line)
        wall.Width = d_mm; wall.Height = h_mm
        wall.Label = f"{prefix}_{i+1}"
        wall.Align = "Left"
        doc.recompute()
        created.append(wall.Label)
    return f"Attika: {', '.join(created)}"
```

---

## Tool 10: `create_slab_with_openings` — Mittel

**MCP:**
```python
def create_slab_with_openings(
    length: str = "10m", width: str = "8m", height: str = "300mm",
    placement_x: str = "0mm", placement_y: str = "0mm", placement_z: str = "0mm",
    openings: list[dict] = [],
    name: str = "Geschossdecke"
) -> str:
```
`openings` ist eine Liste von Dicts: `{"x": 1.4, "y": 0.9, "w": 3.7, "h": 1.2}`
- `x`, `y`: relativer Offset von der Slab-Platzierung (in **Metern**)
- `w`, `h`: Breite und Höhe der Öffnung (in **Metern**)

**Bridge:** `erstelle_decke_mit_oeffnungen(laenge, breite, hoehe, px, py, pz, oeffnungen, name)`

Slab erzeugen + Boolean-Cuts für Öffnungen.

```python
def erstelle_decke_mit_oeffnungen(self, laenge="10m", breite="8m", hoehe="300mm",
                                    px="0mm", py="0mm", pz="0mm", oeffnungen=None, name="Geschossdecke"):
    if oeffnungen is None: oeffnungen = []
    doc = App.ActiveDocument or App.newDocument("BIM")
    l = self._parse_unit(laenge); b = self._parse_unit(breite); h = self._parse_unit(hoehe)
    px_mm = self._parse_unit(px); py_mm = self._parse_unit(py); pz_mm = self._parse_unit(pz)
    slab = doc.addObject("Part::Box", "SlabBase")
    slab.Length, slab.Width, slab.Height = l, b, h
    slab.Placement.Base = App.Vector(px_mm, py_mm, pz_mm)
    current = slab
    for i, o in enumerate(oeffnungen):
        ox = o["x"] * 1000.0; oy = o["y"] * 1000.0
        ow = o["w"] * 1000.0; oh = o["h"] * 1000.0
        tool = doc.addObject("Part::Box", f"OpeningTool_{i}")
        tool.Length, tool.Width, tool.Height = ow, oh, h + 10
        tool.Placement.Base = App.Vector(px_mm + ox, py_mm + oy, pz_mm - 5)
        cut = doc.addObject("Part::Cut", f"SlabCut_{i}")
        cut.Base, cut.Tool = current, tool
        if hasattr(current, "ViewObject"): current.ViewObject.Visibility = False
        if hasattr(tool, "ViewObject"): tool.ViewObject.Visibility = False
        current = cut
    current.Label = name
    doc.recompute()
    return f"Decke mit {len(oeffnungen)} Öffnungen: {current.Label}"
```

---

## Tool 11: `align_walls_in_container` — Mittel

**MCP:**
```python
def align_walls_in_container(container: str, ref_at: str = "outside") -> str:
```

**Bridge:** `waende_in_container_ausrichten(container_name, ref_aussen)`

Erkennt Himmelsrichtung jeder Wand und setzt korrektes Align.

```python
def waende_in_container_ausrichten(self, container_name, ref_aussen="outside"):
    doc = App.ActiveDocument
    cont = self._get_obj(container_name)
    if not cont: return "Container nicht gefunden."
    objs = cont.Group if hasattr(cont, "Group") else []
    aligned = 0
    for obj in objs:
        if "Wall" not in obj.TypeId: continue
        if not hasattr(obj, "Base") or not obj.Base: continue
        vs = obj.Base.Shape.Vertexes
        if len(vs) < 2: continue
        w_dir = (vs[-1].Point - vs[0].Point).normalize()
        is_east = abs(w_dir.x) > abs(w_dir.y)
        if ref_aussen == "outside":
            if is_east:
                obj.Align = "Right" if w_dir.x > 0 else "Left"
            else:
                obj.Align = "Left" if w_dir.y > 0 else "Right"
        else:
            if is_east:
                obj.Align = "Left" if w_dir.x > 0 else "Right"
            else:
                obj.Align = "Right" if w_dir.y > 0 else "Left"
        aligned += 1
    doc.recompute()
    return f"{aligned} Wände ausgerichtet in '{container_name}'"
```

---

## Tool 12: `validate_model` — Mittel

**MCP:**
```python
def validate_model() -> str:
```

**Bridge:** `modell_validieren()`

Prüft States, Overlaps (Bounding Box), fehlende Container.

```python
def modell_validieren(self):
    doc = App.ActiveDocument
    if not doc: return "Kein Dokument."
    lines = []
    objs = doc.Objects
    invalid = []
    touched = []
    no_container = []
    for o in objs:
        if hasattr(o, "State"):
            if "Invalid" in str(o.State): invalid.append(o.Label)
            if "Touched" in str(o.State): touched.append(o.Label)
        has_parent = False
        for p in objs:
            if hasattr(p, "Group") and o in p.Group:
                has_parent = True; break
        if not has_parent: no_container.append(o.Label)
    if invalid: lines.append(f"INVALID: {', '.join(invalid)}")
    if touched: lines.append(f"TOUCHED: {', '.join(touched)}")
    if no_container: lines.append(f"Ohne Container: {', '.join(no_container)}")
    # Overlap check (BBox)
    overlaps = []
    for i, a in enumerate(objs):
        if not hasattr(a, "Shape") or not a.Shape: continue
        for j, b in enumerate(objs):
            if j <= i: continue
            if not hasattr(b, "Shape") or not b.Shape: continue
            if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                overlaps.append(f"{a.Label} ∩ {b.Label}")
    if overlaps: lines.append(f"Überlappungen:\n  " + "\n  ".join(overlaps[:10]))
    return "\n".join(lines) if lines else "OK"
```

---

## Tool 13: `validate_ifc_export` — Mittel

**MCP:**
```python
def validate_ifc_export() -> str:
```

**Bridge:** `validiere_ifc_export()`

Prüft IFC-Typ, Material, Container für alle Objekte.

```python
def validiere_ifc_export(self):
    doc = App.ActiveDocument
    if not doc: return "Kein Dokument."
    warnings = []
    for o in doc.Objects:
        issues = []
        if not hasattr(o, "IfcType") or not o.IfcType:
            issues.append("kein IFC-Typ")
        if not hasattr(o, "Material") or not o.Material:
            issues.append("kein Material")
        in_container = False
        for p in doc.Objects:
            if hasattr(p, "Group") and o in p.Group:
                in_container = True; break
        if not in_container:
            issues.append("nicht in Container")
        if issues:
            warnings.append(f"  {o.Label} ({o.Name}): {', '.join(issues)}")
    if warnings:
        return "IFC-Warnungen:\n" + "\n".join(warnings)
    return "IFC-Export bereit."
```

---

## Zusammenfassung der Änderungen

| Datei | Änderung |
|-------|----------|
| `freecad_bridge.py` | +13 Methoden auf `RobustFreeCADBridge` (ca. 300 Zeilen) |
| `mcp_server.py` | +13 `@mcp.tool()`-Funktionen (ca. 200 Zeilen) |
