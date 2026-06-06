# FreeCAD MCP Tools Verbesserungen

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) for tracking.

**Goal:** Implement alle Verbesserungen aus Fehlerprotokoll.md und Verbesserungsvorschlaege_MCP_Tools.md

**Architecture:** Two-tier: `freecad_bridge.py` (FreeCAD-intern, XML-RPC) + `mcp_server.py` (FastMCP). Änderungen immer in beiden Dateien.

**Tech Stack:** Python, FreeCAD Python API, FastMCP, XML-RPC

---

## Task 1: Batch `add_to_container` (Priorität 1.2)

**Files:**
- Modify: `freecad_bridge.py`
- Modify: `mcp_server.py`
- Modify: `test_mcp_tools.py`

- [ ] **Step 1: Add batch method to bridge**

Füge nach `fuege_zu_container_hinzu` in `freecad_bridge.py` ein:

```python
def fuege_mehrere_zu_container_hinzu(self, objekte_liste, container_name):
    try:
        cont = self._get_obj(container_name)
        if not cont: return f"Container '{container_name}' nicht gefunden."
        added = []
        errors = []
        for obj_name in objekte_liste:
            o = self._get_obj(obj_name)
            if not o:
                errors.append(f"'{obj_name}' nicht gefunden")
                continue
            if hasattr(cont, "addObject"):
                cont.addObject(o)
            elif hasattr(cont, "Group"):
                g = list(cont.Group); g.append(o); cont.Group = g
            added.append(o.Label)
        App.ActiveDocument.recompute()
        parts = []
        if added: parts.append(f"Hinzugefügt: {', '.join(added)}")
        if errors: parts.append(f"Fehler: {', '.join(errors)}")
        return "; ".join(parts) if parts else "Nichts hinzugefügt."
    except Exception as e: return f"Fehler: {str(e)}"
```

- [ ] **Step 2: Add MCP tool wrapper** in `mcp_server.py`

```python
@mcp.tool()
def add_to_container_batch(object_names: list[str], container_name: str) -> str:
    """
    Fügt mehrere Objekte auf einmal zu einem Container hinzu.
    """
    try:
        bridge = get_bridge()
        return bridge.fuege_mehrere_zu_container_hinzu(object_names, container_name)
    except Exception as e: return f"Fehler: {str(e)}"
```

- [ ] **Step 3: Add test** in `test_mcp_tools.py`

## Task 2: Batch `set_material` (Priorität 1.2)

**Files:**
- Modify: `freecad_bridge.py`
- Modify: `mcp_server.py`
- Modify: `test_mcp_tools.py`

- [ ] **Step 1: Add batch set_material to bridge**

```python
def setze_material_mehrere(self, objekte_liste, material_name, color_rgb=(0.8, 0.8, 0.8)):
    try:
        doc = App.ActiveDocument
        mat = doc.getObject(material_name)
        if not mat:
            mat = doc.addObject("App::MaterialObject", material_name)
            mat.Label = material_name
        if isinstance(color_rgb, list):
            color_rgb = tuple(color_rgb)
        if isinstance(color_rgb, (tuple, list)):
            color_str = f"{color_rgb[0]},{color_rgb[1]},{color_rgb[2]}"
            shape_color = color_rgb
        else:
            color_str = str(color_rgb)
            shape_color = (0.8, 0.8, 0.8)
        mat.Material = {'Name': material_name, 'DiffuseColor': color_str}
        set_count = 0
        for obj_name in objekte_liste:
            obj = self._get_obj(obj_name)
            if not obj: continue
            obj.Material = mat
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                obj.ViewObject.ShapeColor = shape_color
            set_count += 1
        doc.recompute()
        return f"Material '{material_name}' an {set_count} Objekt(e) gesetzt."
    except Exception as e: return f"Fehler: {str(e)}"
```

- [ ] **Step 2: Add MCP tool wrapper**

```python
@mcp.tool()
def set_material_batch(object_names: list[str], material_name: str, color_rgb: str = "(0.8, 0.8, 0.8)") -> str:
    """
    Weist mehreren Objekten auf einmal ein Material zu.
    """
    try:
        bridge = get_bridge()
        rgb_tuple = tuple(map(float, color_rgb.strip("()").split(",")))
        return bridge.setze_material_mehrere(object_names, material_name, rgb_tuple)
    except Exception as e: return f"Fehler: {str(e)}"
```

## Task 3: Verbesserte `validate_model` Fehlermeldungen (Priorität 1.3)

**Files:**
- Modify: `freecad_bridge.py`

- [ ] **Step 1: Ersetze `modell_validieren` mit detaillierten BBox-Infos**

```python
def modell_validieren(self):
    try:
        doc = App.ActiveDocument
        if not doc: return "Kein Dokument."
        lines = []
        objs = doc.Objects
        invalid = [o.Label for o in objs if hasattr(o, "State") and "Invalid" in str(o.State)]
        touched = [o.Label for o in objs if hasattr(o, "State") and "Touched" in str(o.State)]
        no_container = []
        for o in objs:
            has_parent = any(hasattr(p, "Group") and o in p.Group for p in objs)
            if not has_parent: no_container.append(o.Label)
        bad_bbox = []
        for o in objs:
            if not hasattr(o, "Shape") or not o.Shape: continue
            try:
                bb = o.Shape.BoundBox
                if any(v is None for v in [bb.XMin, bb.YMin, bb.ZMin, bb.XMax, bb.YMax, bb.ZMax]):
                    bad_bbox.append(f"{o.Label} ({o.Name}): BBox=({bb.XMin},{bb.YMin},{bb.ZMin})-({bb.XMax},{bb.YMax},{bb.ZMax})")
                elif bb.XMin == bb.XMax and bb.YMin == bb.YMax and bb.ZMin == bb.ZMax:
                    bad_bbox.append(f"{o.Label} ({o.Name}): Null-BBox ({bb.XMin},{bb.YMin},{bb.ZMin})")
            except:
                bad_bbox.append(f"{o.Label} ({o.Name}): BBox-Fehler")
        if invalid: lines.append(f"INVALID ({len(invalid)}): {', '.join(invalid)}")
        if touched: lines.append(f"TOUCHED ({len(touched)}): {', '.join(touched)}")
        if no_container: lines.append(f"Ohne Container ({len(no_container)}): {', '.join(no_container)}")
        if bad_bbox: lines.append(f"Ungültige BBox ({len(bad_bbox)}):\n  " + "\n  ".join(bad_bbox))
        overlaps = []
        for i, a in enumerate(objs):
            if not hasattr(a, "Shape") or not a.Shape: continue
            for j, b in enumerate(objs):
                if j <= i: continue
                if not hasattr(b, "Shape") or not b.Shape: continue
                try:
                    if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                        overlaps.append(f"{a.Label} ∩ {b.Label}")
                except: pass
        if overlaps:
            lines.append(f"Überlappungen ({len(overlaps)}):\n  " + "\n  ".join(overlaps[:10]))
        return "\n".join(lines) if lines else "OK — keine Probleme gefunden."
    except Exception as e: return f"Fehler: {str(e)}"
```

## Task 4: `export_ifc` Fallback mit Arch.export (Priorität 1.1)

**Files:**
- Modify: `freecad_bridge.py`

- [ ] **Step 1: Aktuellen ifcopenshell-Ast vereinfachen — Arch.export als Fallback**

Der ifcopenshell-Ast wird auf einen klaren Arch.export-Fallback reduziert:

```python
    try:
        import importIFC
        importIFC.export(App.ActiveDocument.Objects, safe_path)
        return f"Exportiert: {os.path.basename(safe_path)}"
    except ImportError:
        if hasattr(Arch, "export"):
            Arch.export(App.ActiveDocument.Objects, safe_path)
            return f"Exportiert (via Arch.Fallback): {os.path.basename(safe_path)}"
        return ("Fehler: Export-Modul nicht gefunden. Weder importIFC noch Arch.export verfügbar. "
                "Bitte installiere 'importIFC' über den FreeCAD-Addon-Manager.")
```

## Task 5: Batch `create_axes` (Priorität 2.1)

**Files:**
- Modify: `freecad_bridge.py`
- Modify: `mcp_server.py`

- [ ] **Step 1: Add batch axis creation to bridge**

```python
def erstelle_mehrere_achsen(self, achsen_liste):
    try:
        import Arch
        doc = App.ActiveDocument or App.newDocument("BIM")
        created = []
        for a in achsen_liste:
            label = a.get("label", "?")
            x = a.get("x", "0mm"); y = a.get("y", "0mm"); z = a.get("z", "0mm")
            richtung = a.get("direction", "Z")
            achse = Arch.makeAxis(1, 10000)
            achse.Label = f"Achse_{label}"
            achse.Placement.Base = App.Vector(self._parse_unit(x), self._parse_unit(y), self._parse_unit(z))
            if richtung.upper() == "X":
                achse.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), -90)
            elif richtung.upper() == "Y":
                achse.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 0)
            else:
                achse.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
            if hasattr(achse, "Labels"): achse.Labels = [label]
            created.append(achse.Label)
        doc.recompute()
        return f"Achsen erstellt: {', '.join(created)}"
    except Exception as e: return f"Fehler: {str(e)}"
```

- [ ] **Step 2: Add MCP tool wrapper**

```python
@mcp.tool()
def create_axes(axes: list[dict]) -> str:
    """
    Erstellt mehrere Bauachsen auf einmal.
    
    Args:
        axes: Liste von Dicts mit label, x, y, z, direction.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_mehrere_achsen(axes)
    except Exception as e: return f"Fehler: {str(e)}"
```

## Task 6: Erweiterte `list_objects` Ausgabe (Priorität 2.2)

**Files:**
- Modify: `freecad_bridge.py`
- Modify: `test_mcp_tools.py`

- [ ] **Step 1: Verbessere `liste_objekte` mit klarem Label→Name Mapping**

```python
def liste_objekte(self):
    try:
        if not App.ActiveDocument: return "Kein Dokument."
        res = ["--- Objektliste (Label → Name) ---"]
        for o in App.ActiveDocument.Objects:
            line = f"  {o.Label} → {o.Name} [{o.TypeId}]"
            if hasattr(o, "IfcRole"):
                line += f" IFC:{o.IfcRole}"
            elif hasattr(o, "IfcType") and o.IfcType:
                line += f" IFC:{o.IfcType}"
            if hasattr(o, "Material") and o.Material:
                m_label = getattr(o.Material, "Label", str(o.Material))
                line += f" Mat:{m_label}"
            res.append(line)
        res.append(f"--- {len(App.ActiveDocument.Objects)} Objekte ---")
        return "\n".join(res)
    except Exception as e: return f"Fehler: {str(e)}"
```

## Task 7: `create_structure` mit Position (Priorität 2.3)

**Files:**
- Modify: `freecad_bridge.py`
- Modify: `mcp_server.py`

- [ ] **Step 1: Position-Parameter zur Bridge-Methode hinzufügen**

```python
def erstelle_struktur(self, length="100mm", width="20mm", height="2000mm", name="Balken",
                     position_x=None, position_y=None, position_z=None):
    try:
        import Arch
        doc = App.ActiveDocument or App.newDocument("BIM")
        base = doc.addObject("Part::Box", "StructBase")
        base.Length, base.Width, base.Height = self._parse_unit(length), self._parse_unit(width), self._parse_unit(height)
        if hasattr(base, "ViewObject"): base.ViewObject.Visibility = False
        struct = Arch.makeStructure(base)
        struct.Label = name
        if position_x is not None and position_y is not None:
            x = position_x * 1000.0 if isinstance(position_x, (int, float)) else self._parse_unit(position_x)
            y = position_y * 1000.0 if isinstance(position_y, (int, float)) else self._parse_unit(position_y)
            z = (position_z or 0) * 1000.0 if isinstance(position_z if position_z else 0, (int, float)) else self._parse_unit(position_z or "0mm")
            struct.Placement.Base = App.Vector(x, y, z)
        doc.recompute()
        return f"Struktur: {struct.Label}"
    except Exception as e: return f"Fehler: {str(e)}"
```

- [ ] **Step 2: MCP-Wrapper aktualisieren**

```python
@mcp.tool()
def create_structure(length: str = "100mm", width: str = "20mm", height: str = "20mm",
                    name: str = "Balken",
                    position_x: float | None = None,
                    position_y: float | None = None,
                    position_z: float | None = None) -> str:
    """
    Erstellt ein Tragwerk-Element (Arch Structure). Optionale position_x/y/z in METERN.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_struktur(length, width, height, name, position_x, position_y, position_z)
    except Exception as e:
        return f"Fehler: {str(e)}"
```

## Task 8: `execute_python` mit vollständigem Traceback (Priorität 3.3)

**Files:**
- Modify: `freecad_bridge.py`

- [ ] **Step 1: traceback zu Fehlerausgabe hinzufügen**

```python
def run_python(self, script):
    try:
        import FreeCADGui as Gui
        import io, sys, traceback
        restricted_globals = {"App": App, "Part": Part, "Gui": Gui, "FreeCAD": App, "time": time}
        self._audit("EXECUTE_PYTHON", f"Skript ({len(script)} Z.): {script[:200]}")
        stdout_capture = io.StringIO()
        old_stdout = sys.stdout
        sys.stdout = stdout_capture
        try:
            exec(script, restricted_globals)
            if App.ActiveDocument: App.ActiveDocument.recompute()
        finally:
            sys.stdout = old_stdout
        output = stdout_capture.getvalue()
        return output if output else "OK."
    except Exception as e:
        tb = traceback.format_exc()
        return f"Fehler: {str(e)}\n{tb}"
```

## Task 9: `capture_view` mit Ansichtstypen (Priorität 3.2)

**Files:**
- Modify: `freecad_bridge.py`
- Modify: `mcp_server.py`

- [ ] **Step 1: view_type-Parameter zur Bridge**

```python
def capture_view(self, filename="freecad_view.png", view_type="iso", camera_position=None, target=None):
    try:
        import FreeCADGui
        if not App.ActiveDocument: return "Fehler: Kein Dokument."
        view = FreeCADGui.ActiveDocument.ActiveView
        if not view: return "Fehler: Keine Ansicht."
        safe_path = self._sanitize_path(filename)
        if view_type == "top": view.viewTop()
        elif view_type == "front": view.viewFront()
        elif view_type == "right": view.viewRight()
        else: view.viewIsometric()
        view.saveImage(safe_path, 1280, 720, "White")
        if os.path.exists(safe_path):
            with open(safe_path, "rb") as f:
                return base64.b64encode(f.read()).decode('utf-8')
        return "Fehler: Bild wurde nicht gespeichert."
    except PermissionError as e: return f"Fehler: {str(e)}"
    except Exception as e: return f"Fehler: {str(e)}"
```

- [ ] **Step 2: MCP-Wrapper aktualisieren**

```python
@mcp.tool()
def capture_view(view_type: str = "iso") -> Image:
    """
    Erstellt einen Screenshot der aktuellen 3D-Ansicht.
    
    Args:
        view_type: "iso", "top", "front", oder "right".
    """
    try:
        bridge = get_bridge()
        base64_data = bridge.capture_view("freecad_view.png", view_type)
        if base64_data.startswith("Fehler"):
            raise Exception(base64_data)
        img_bytes = base64.b64decode(base64_data)
        return Image(data=img_bytes, format="png")
    except Exception as e:
        raise Exception(f"Screenshot-Fehler: {str(e)}")
```

## Task 10: Timeout-Erhöhung und Retry (Priorität 3.4)

**Files:**
- Modify: `freecad_bridge.py`

- [ ] **Step 1: `_dispatch` mit erhöhtem Timeout und Retry**

```python
def _dispatch(self, method, params, retries=2):
    if not hasattr(self, method):
        raise Exception(f"Methode {method} nicht gefunden.")
    func = getattr(self, method)
    for attempt in range(retries + 1):
        result_holder = {'event': threading.Event(), 'result': None, 'error': None}
        request_queue.put((func, params, {}, result_holder))
        if result_holder['event'].wait(timeout=45.0):
            return result_holder['error'] if result_holder['error'] else result_holder['result']
    return "Fehler: Timeout im Main Thread (nach 2 Versuchen)."
```
