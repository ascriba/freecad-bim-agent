# FreeCAD MCP Bridge — BIM mit KI

MCP-Server + XML-RPC-Bridge für die Steuerung von FreeCAD via LLM (Claude, OpenCode etc.).
Ermöglicht vollständiges Building Information Modeling (BIM) über textuelle Befehle.

## Architektur

```
LLM (z.B. Claude/OpenCode)
    ↕ MCP-Protokoll
mcp_server.py  (Standalone-Prozess)
    ↕ XML-RPC (localhost:8000)
freecad_bridge.py  (läuft in FreeCAD Python-Konsole)
    ↕ FreeCAD-API (App, Part, Arch, Draft, ...)
```

## Schnellstart

### 1. Bridge starten (in FreeCAD Python Console)

```python
exec(open("/pfad/zu/freecad_bridge.py").read())
start_bridge()
```

Meldung: `--- Bridge AKTIV ---`

### 2. MCP-Server starten (separates Terminal)

```bash
python mcp_server.py
```

## Verfügbare Tools (61 Stück)

### Basis-Geometrie (Part)

| Tool | Beschreibung |
|------|-------------|
| `create_cube` | Würfel/Box mit Einheiten |
| `create_cylinder` | Zylinder |
| `create_sphere` | Kugel |
| `create_point` | Draft-Punkt |
| `create_line` | Draft-Linie |
| `create_polyline` | Draft-Linienzug |
| `create_rectangle` | Draft-Rechteck |
| `create_circle` | Draft-Kreis |
| `create_arc` | Draft-Kreisbogen |

### BIM/Arch — Bestehend

| Tool | Beschreibung |
|------|-------------|
| `create_site` | Grundstück (Arch Site) |
| `create_building` | Gebäude (Arch Building) |
| `create_floor` | Stockwerk (Arch Floor) |
| `create_wall` | Wand aus 2 Punkten (Meter) |
| `align_wall` | Wand ausrichten (Left/Center/Right) |
| `join_walls` | Wände vereinigen |
| `create_window` | Fenster/Tür in Wand einfügen |
| `add_to_wall` | Komponente zu Wand hinzufügen |
| `create_slab` | Bodenplatte |
| `create_structure` | Tragwerk (Balken/Säule) |
| `add_to_container` | Objekt in Container (z.B. EG→Gebäude) |

### BIM/Arch — Phase 1 (Hochpriorisiert)

| Tool | Beschreibung |
|------|-------------|
| `create_roof` | Dach (Arch.makeRoof) |
| `create_stairs` | Treppe (Arch.makeStairs) |
| `create_axis` | Einzelachse (Arch.makeAxis) |
| `create_axis_system` | Achssystem |
| `create_section_plane` | Schnittebene |
| `clone_object` | Draft-Klon |
| `mirror_object` | Spiegelung (Part::Mirroring) |

### BIM/Arch — Phase 2 (Mittelpriorisiert)

| Tool | Beschreibung |
|------|-------------|
| `create_text` | Draft-Text in 3D |
| `create_dimension` | Draft-Bemaßung |
| `fillet` | Verrundung (Part.makeFillet) |
| `chamfer` | Fase (Part.makeChamfer) |
| `create_panel` | Arch-Paneel/Platte |
| `import_dxf` | DXF-Import |
| `export_dxf` | DXF-Export |
| `export_pdf` | PDF-Export (TechDraw) |
| `export_svg` | SVG-Export |

### BIM/Arch — Phase 3 (Niedrigpriorisiert)

| Tool | Beschreibung |
|------|-------------|
| `create_window_sketch` | Fenster aus Rechteck-Skizze |
| `create_curtain_wall` | Vorhangfassade |
| `create_pipe` | Rohr (kreisförmig) |
| `create_duct` | Kanal (rechteckig, Part::Sweep) |
| `create_schedule` | Mengenauszug/Objektliste |
| `create_2d_view` | TechDraw-2D-Ansicht |

### Manipulation

| Tool | Beschreibung |
|------|-------------|
| `set_position` | Position setzen (X, Y, Z) |
| `rotate_object` | Drehen (Achse X/Y/Z, Winkel) |
| `delete_object` | Objekt löschen |
| `boolean_union` | Vereinigung (Fusion) |
| `boolean_cut` | Abzug (Cut) |

### Metadaten & Austausch

| Tool | Beschreibung |
|------|-------------|
| `set_ifc_data` | IFC-Eigenschaften setzen |
| `set_material` | Material + Farbe zuweisen |
| `get_quantities` | Mengen (Fläche, Volumen etc.) |
| `export_ifc` | IFC-Export |
| `analyze_ifc` | IFC-Analyse (ifcopenshell) |
| `capture_view` | Screenshot der 3D-Ansicht |
| `list_objects` | Objektliste mit IFC/Material |
| `execute_python` | Beliebiger Python-Code (Escape Hatch) |

### Tools (MCP Tool Lücken — Hochpriorisiert)

| Tool | Beschreibung |
|------|-------------|
| `get_object_info` | Objekt-Info: BBox, Align, State, Volumen, Basispunkte |
| `rename_object` | Objekt umbenennen (Label setzen) |
| `set_visibility` | Sichtbarkeit ein/aus (wichtig für Boolean-Cut) |
| `move_line` | Draft-Linien-Start/End-Punkte verschieben |
| `create_opening` | Öffnung/Durchbruch via Boolean-Cut |
| `copy_to_floor` | Wände auf Zielgeschoss kopieren (+ Höhenversatz) |
| `create_attika` | Attika-Wände aus Slab-Perimeter generieren |

### Tools (MCP Tool Lücken — Mittelpriorisiert)

| Tool | Beschreibung |
|------|-------------|
| `set_wall_alignment` | Baseline + Align in einem Schritt an Außenkante |
| `boolean_cut_finalize` | Cut-Nachsorge: umbenennen, verstecken, Container |
| `slab_with_openings` | Decke mit Durchbrüchen in einem Schritt |
| `align_walls_in_container` | Alle Wände eines Containers automatisch ausrichten |
| `validate_model` | Invalid/Touched/Overlaps/Container-Prüfung |
| `validate_ifc_export` | Preflight-Check: IFC-Typ, Material, Container |

## Einheiten-Konvention

- `list[float]` Parameter (z.B. `p1=[0,5,0]` für `create_wall`) = **Meter** ×1000 → mm
- `str` Parameter (z.B. `"300mm"`, `"1.5m"`) = direkt mit Einheit
- Winkel als Grad: `"45deg"` oder `float`

## Sicherheitshinweis

Dieser MCP-Server stellt über XML-RPC (localhost:8000) eine direkte Schnittstelle zur FreeCAD-Python-Umgebung bereit.

**`execute_python`** führt beliebigen Python-Code in FreeCAD aus — dies ist ein bewusstes RCE-Tool (Escape Hatch). Auch nach Entfernen von `os` aus dem exec-Namespace kann Code-Escaping nicht verhindert werden.

**Path-Traversal-Schutz:** Alle Import/Export-Tools (`import_dxf`, `export_dxf`, `export_pdf`, `export_svg`, `export_ifc`, `analyze_ifc`, `capture_view`) beschränken Dateizugriffe auf das Arbeitsverzeichnis. `../`-Traversal wird via `os.path.realpath()` blockiert.

**Audit-Log:** Sicherheitskritische Aktionen (DELETE, EXPORT, IMPORT, ANALYZE, EXECUTE_PYTHON) werden in der FreeCAD-Konsole ausgegeben.

**Nutzung nur in vertrauenswürdigen Umgebungen.** Der Server ist nur für localhost ausgelegt und sollte nicht exposed werden.

## Entwicklung

### Test- und Debug-Plan

Siehe `Plan/TEST_DEBUG.md` für detaillierte Testprozeduren und Debugging.

### Projekt-Plan

Siehe `Plan/README.md` für die vollständige Spezifikation aller 22 neuen Tools.

### Hot-Reload (Bridge aktualisieren ohne FreeCAD-Neustart)

Nach Code-Änderungen in `freecad_bridge.py`:
```python
# In FreeCAD Console:
exec(open("/pfad/zu/freecad_bridge.py").read())
# Definiert die Klasse neu und patcht die laufende Instanz
```

**Bekanntes Problem:** Hot-Patch via `__class__` kann Bridge hängen lassen.
Sicherste Methode: FreeCAD + Bridge neustarten nach Code-Änderungen.

## Bekannte Bugs & Limits

- `export_svg` schlägt bei komplexen Arch-Objekten fehl (FreeCAD-API-Limit)
- `set_material` funktioniert nur mit FreeCAD 0.21+ Material-API
- `create_stairs` erfordert FreeCAD ≥ 0.19
- `create_2d_view` erfordert TechDraw-Workbench

## Lizenz

MIT
