# FreeCAD MCP Bridge

## Architecture

Two-tier: **MCP Server** (`mcp_server.py`, standalone) ↔ XML-RPC (port 8000) ↔ **FreeCAD Bridge** (`freecad_bridge.py`, runs inside FreeCAD GUI).

The MCP server proxies all tool calls to the XML-RPC bridge. The bridge uses `FreeCADGui.addTimer` (or Qt fallback) to process requests on the main thread.

## Startup Order

1. **Start the Bridge** (inside FreeCAD Python console):
   ```
   exec(open("/path/to/freecad_bridge.py").read())
   start_bridge()
   ```
   Confirms with `--- Bridge AKTIV ---`. Port 8000 must be free.

2. **Start the MCP Server** (separate terminal):
   ```
   python mcp_server.py
   ```

## Unit Conventions

- MCP tool `list[float]` params (e.g. `create_wall p1=[0,5,0]`) = **meters**. The bridge auto-converts to mm (FreeCAD internal unit) by scaling ×1000.
- `float` params (e.g. `set_position x=-2.0`) are also **meters** (×1000 in bridge).
- String params (e.g. `"300mm"`, `"1.5m"`) parsed directly by bridge.
- Angles as strings: `"45deg"`.
- **Important:** `set_position` sets an **absolute** position (not relative). Values are in meters.

## Wall & Window Creation

- **Wall**: `Draft.make_line(v1, v2)` + `Arch.makeWall(line)` — base line is hidden. Points in meters.
- **Align**: `align="Left"|"Center"|"Right"`. Left/Right sind richtungsabhängig (siehe Tabelle unten). Alternativ kann `align_to="inside"/"outside"` verwendet werden.
- **Window/Door**: `create_window(sill_height="0mm")` for doors, `"900mm"` for windows. Finds nearest vertical face, computes position from wall baseline direction. Parameter alias: `wall_name` → `wall_ident`. Der `name`-Parameter setzt das Label des Fensters.

## Align-Richtungsabhängigkeit

`align="Left"` und `align="Right"` beziehen sich auf die Wandrichtung (p1→p2):

| Wandrichtung (p1→p2) | Left bedeutet | Right bedeutet |
|----------------------|---------------|----------------|
| Osten (+X) | Süden (−Y) | Norden (+Y) |
| Norden (+Y) | Osten (+X) | Westen (−X) |
| Westen (−X) | Norden (+Y) | Süden (−Y) |
| Süden (−Y) | Westen (−X) | Osten (+X) |

**Left = 90° im Uhrzeigersinn von Wandrichtung | Right = 90° gegen Uhrzeigersinn**

Mit `align_to="inside"` / `align_to="outside"` wird automatisch die korrekte Seite basierend auf der Wand-Normalen gewählt.

## All 61 MCP Tools

### Basis-Geometrie (9)
`create_cube`, `create_cylinder`, `create_sphere`, `create_point`, `create_line`,
`create_polyline`, `create_rectangle`, `create_circle`, `create_arc`

### BIM/Arch Bestehend (11)
`create_site`, `create_building`, `create_floor`, `create_wall`, `align_wall`, `join_walls`,
`create_window`, `add_to_wall`, `create_slab`, `create_structure`, `add_to_container`

### Phase 1 — Hochpriorisiert (7)
`create_roof` (`Arch.makeRoof` + `Angles[]`-Property), `create_stairs` (`Arch.makeStairs`),
`create_axis` (`Arch.makeAxis(count, spacing)` + Placement), `create_axis_system`,
`create_section_plane`, `clone_object` (`Draft.clone`), `mirror_object` (`Part::Mirroring`)

### Phase 2 — Mittelpriorisiert (9)
`create_text` (`Draft.makeText`), `create_dimension` (`Draft.makeDimension`),
`fillet` (`Part.Shape.makeFillet`), `chamfer` (`Part.Shape.makeChamfer`),
`create_panel` (`Arch.makePanel`), `import_dxf`, `export_dxf`, `export_pdf`, `export_svg`

### Phase 3 — Niedrigpriorisiert (6)
`create_window_sketch`, `create_curtain_wall` (`Arch.makeCurtainWall`),
`create_pipe` (`Arch.makePipe`), `create_duct` (`Part::Sweep`),
`create_schedule` (`Arch.makeSchedule`), `create_2d_view` (TechDraw)

### Manipulation (5)
`set_position`, `rotate_object`, `delete_object`, `boolean_union`, `boolean_cut`

### Metadaten & Utility (7)
`set_ifc_data`, `set_material`, `get_quantities`, `export_ifc`, `analyze_ifc`,
`capture_view`, `list_objects`, `execute_python`

### MCP Tool Lücken — Hochpriorisiert (7)
`get_object_info` (BBox/Align/State/Volumen), `rename_object` (Label setzen),
`set_visibility` (ViewObject.Visibility), `move_line` (Draft Line Endpunkte),
`create_opening` (Boolean-Cut für Durchbrüche), `copy_to_floor` (Wände auf Zielgeschoss),
`create_attika` (Attika aus Slab-Perimeter)

### MCP Tool Lücken — Mittelpriorisiert (6)
`set_wall_alignment` (Baseline + Align kombiniert), `boolean_cut_finalize` (Cut-Nachsorge),
`create_slab_with_openings` (Decke mit Durchbrüchen),
`align_walls_in_container` (Bulk-Align pro Geschoss),
`validate_model` (Invalid/Touched/Overlaps), `validate_ifc_export` (Preflight-Check)

## Material API (FreeCAD 0.21+)
```
mat.Material = {'Name': name, 'DiffuseColor': '0.8,0.2,0.2'}
```
`DiffuseColor` muss ein String mit Komma-Separation sein, kein Tupel/Dict.

## create_slab — Extrusionsrichtung

Die `Arch Structure` (die `create_slab` intern nutzt) extrudiert das Base-Sketch **abwärts** (−Z).
- `Placement.Base.z` = gewünschte **Oberkante** der Platte
- `Height` = Dicke der Platte (nach unten)

## create_curtain_wall — Label vs. interner Name

`create_curtain_wall(name="...")` setzt das `Label`, aber der interne FreeCAD-`Name` wird automatisch vergeben.
- Für Zugriffe via `getObject()` immer `_get_obj()` (Label-Fallback) in der Bridge nutzen
- Die Tool-Rückgabe enthält beide: `Label (Name)`

## Arch.makeAxis API (diese FreeCAD-Version)
```python
axis = Arch.makeAxis(count=1, spacing=10000)  # NICHT: Arch.makeAxis(line)
```
Erzeugt `count` parallele Achsen mit Abstand `spacing`.

## Roof API
```python
roof = Arch.makeRoof(wire, thickness=100)
roof.Angles = [30.0] * n  # angle per face, NOT kwarg
roof.Overhang = 500
```

## Duct Creation
```python
sweep = doc.addObject("Part::Sweep", "Kanal")
sweep.Sections = [rect]      # Draft Rectangle
sweep.Spine = path            # Draft Wire
sweep.Solid = True
sweep.Frenet = True
```

## Mirror API
```python
mirror = doc.addObject("Part::Mirroring", "Gespiegelt")
mirror.Source = obj
mirror.Normal = App.Vector(1, 0, 0)
mirror.Base = App.Vector(0, 0, 0)
```

## Escape Hatch

`execute_python(script)` runs arbitrary Python in FreeCAD with access to `App`, `Part`, `Gui`. Use for anything without a dedicated tool (torus, loft, fillet, offset, etc.).

## Skill Reference

The `.agents/skills/freecad-scripts/SKILL.md` skill provides comprehensive FreeCAD Python API reference (Part, Mesh, Sketcher, Draft, Arch, FeaturePython, GUI, Coin3D).

## Style Notes

- Bridge code and docstrings are in **German**; MCP tool wrappers use **English** names.
- `list_objects` shows `Label (Name) [TypeId]` with optional IFC/Material info.
- IFC export prefers `importIFC.export()`, falls back to `Arch.export()`.
- IFC analysis requires `ifcopenshell` inside FreeCAD.

## Sicherheitshinweise

### Kritisch: `execute_python`

`execute_python` ist ein **ungefiltertes RCE-Tool** (`exec()` in FreeCAD). Auch nach Entfernen von `os` aus dem Namespace kann Code-Escaping nicht verhindert werden. **Jede Ausführung wird geloggt.**

- Das Tool ist bewusst als "Escape Hatch" für nicht-abgedeckte FreeCAD-Operationen gedacht
- Das `os`-Modul wurde aus dem exec-Namespace entfernt
- Jeder Aufruf wird ins Audit-Log geschrieben und in der FreeCAD-Konsole ausgegeben
- Nutzung nur durch vertrauenswürdige LLM-Prompts

### Path Traversal Schutz

Import/Export-Tools (`import_dxf`, `export_dxf`, `export_pdf`, `export_svg`, `export_ifc`, `analyze_ifc`, `capture_view`) verwenden `_sanitize_path()`:
- Pfad wird via `os.path.realpath()` aufgelöst (eliminiert `..`-Traversal)
- Zugriff nur innerhalb von `ALLOWED_EXPORT_DIR` (dem Arbeitsverzeichnis) erlaubt
- `PermissionError` bei unerlaubten Pfaden — kein Leaken des tatsächlichen Pfads in der Fehlermeldung

### Audit-Log

Sicherheitskritische Aktionen werden geloggt: `DELETE`, `EXPORT`, `IMPORT`, `ANALYZE`, `EXECUTE_PYTHON`. Das Log erscheint in der FreeCAD-Konsole und im In-Memory-Audit-Log.

## Hot-Reload (Bridge-Code aktualisieren)

Nach Änderungen an `freecad_bridge.py`:
```
# In FreeCAD Console:
exec(open("/pfad/zu/freecad_bridge.py").read())
```
Die Klasse `RobustFreeCADBridge` wird neudefiniert. Die laufende Instanz wird via
`gc.get_objects()` gefunden und `__class__` aktualisiert.

⚠️ **Bekanntes Problem:** Hot-Patch kann Bridge hängen lassen. Sicherste Methode:
FreeCAD neustarten + Bridge frisch laden.

## Bekannte Limits

- `export_svg` schlägt bei komplexen Arch-Objekten fehl
- `create_stairs` erfordert FreeCAD ≥ 0.19
- `create_2d_view` erfordert TechDraw-Workbench
