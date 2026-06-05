"""
Test-Skript für alle MCP-Tools der FreeCAD Bridge.

Ausführung in FreeCAD-Python-Konsole (nachdem Bridge geladen wurde):
    exec(open("/pfad/zu/test_mcp_tools.py").read())
    
Oder via execute_python():
    execute_python(open("/pfad/zu/test_mcp_tools.py").read())
"""
import sys, os

bridge = RobustFreeCADBridge()

doc = App.newDocument("MCP_Test")
App.setActiveDocument(doc.Name)

passed = 0
failed = 0
errors = []

def test(name, func, expected_prefix=None):
    global passed, failed
    try:
        result = func()
        status = "?"
        if isinstance(result, str):
            status = result[:80]
            if expected_prefix and not result.startswith(expected_prefix):
                raise AssertionError(f"Erwartet Prefix '{expected_prefix}', bekam '{result[:80]}'")
        App.Console.PrintMessage(f"  PASS: {name} -> {status}\n")
        passed += 1
    except Exception as e:
        App.Console.PrintMessage(f"  FAIL: {name} -> {e}\n")
        failed += 1
        errors.append(f"{name}: {e}")
    App.ActiveDocument.recompute()

App.Console.PrintMessage("\n=== MCP Bridge Test ===\n")
App.Console.PrintMessage(f"Dokument: {doc.Name}\n\n")

# --- Basis-Geometrie ---
App.Console.PrintMessage("--- Basis-Geometrie ---\n")
test("create_cube", lambda: bridge.erstelle_wuerfel("50mm", "50mm", "50mm"), "Erfolg:")
test("create_cylinder", lambda: bridge.erstelle_zylinder("30mm", "60mm"), "Erfolg:")
test("create_sphere", lambda: bridge.erstelle_kugel("25mm"), "Erfolg:")
test("create_point", lambda: bridge.erstelle_punkt("0mm", "0mm", "0mm", "TestPunkt"), "Punkt:")
test("create_line", lambda: bridge.erstelle_draft_line("0,0,0", "100mm,0,0", "TestLinie"), "Draft-Linie:")
test("create_rectangle", lambda: bridge.erstelle_rechteck("100mm", "50mm", "0mm", "0mm", "0mm"), "Rechteck:")

# --- Metadaten & Utility ---
App.Console.PrintMessage("--- Metadaten & Utility ---\n")
test("list_objects", lambda: bridge.liste_objekte(), "Objekte:")
test("set_ifc_data", lambda: bridge.setze_ifc_daten("Wuerfel", '{"TestProp": "Test"}'), "IFC-Daten")
test("get_quantities", lambda: bridge.ermittle_mengen("Wuerfel"), "Mengen")
test("rename_object", lambda: bridge.umbenennen_objekt("Wuerfel", "TestWuerfel"), "Umbenannt:")
test("rename_zurueck", lambda: bridge.umbenennen_objekt("TestWuerfel", "Wuerfel"), "Umbenannt:")
test("set_visibility_aus", lambda: bridge.sichtbarkeit_setzen("Kugel", False), "Sichtbarkeit")
test("set_visibility_an", lambda: bridge.sichtbarkeit_setzen("Kugel", True), "Sichtbarkeit")

# --- Manipulation ---
App.Console.PrintMessage("--- Manipulation ---\n")
test("set_position", lambda: bridge.setze_position("Kugel", 0.1, 0.1, 0.0), "Position")
test("rotate_object", lambda: bridge.drehe_objekt("Zylinder", "Z", 45), "Gedreht:")

# --- Boolean ---
App.Console.PrintMessage("--- Boolean ---\n")
test("boolean_union", lambda: bridge.bool_union("Wuerfel", "Zylinder"), "Fusion:")

# Objekte für Cut
test("create_cube_cut", lambda: bridge.erstelle_wuerfel("50mm", "50mm", "50mm"), "Erfolg:")
# Das zweite "Wuerfel" bekommt Label "Wuerfel001" — per Name suchen
cut_base = doc.getObject("Wuerfel001")
cut_base_label = cut_base.Label if cut_base else "?"
test("create_cyl_cut", lambda: bridge.erstelle_zylinder("20mm", "60mm"), "Erfolg:")
# cleanup: alten ersten "Zylinder" verschieben, neuen "Zylinder001" nutzen
cut_tool = doc.getObject("Zylinder001")
if cut_tool:
    bridge.umbenennen_objekt("Zylinder001", "CutTool")
if cut_base:
    bridge.umbenennen_objekt("Wuerfel001", "CutBase")
test("boolean_cut", lambda: bridge.bool_cut("CutBase", "CutTool"), "Schnitt:")

# --- Neue Tools (MCP Tool Lücken) ---
App.Console.PrintMessage("--- Neue Tools ---\n")

test("get_object_info", lambda: bridge.objekt_info_abrufen("Fusion"), "Label:")

test("move_line", lambda: bridge.linie_verschieben("TestLinie", [0, 0, 0], [0.2, 0, 0]), "Linie")

# Wand für Alignment
test("create_wall", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [3, 0, 0], "300mm", "2500mm", "TestWand"), "Erfolgreich:")
test("get_object_info_wall", lambda: bridge.objekt_info_abrufen("TestWand"), "Label:")
test("align_wall", lambda: bridge.ausrichten_wand("TestWand", "Left"), "Erfolgreich:")
test("set_wall_alignment", lambda: bridge.wand_ausrichtung_setzen("TestWand", True), "Ausrichtung")

test("boolean_cut_finalize", lambda: bridge.bool_cut_finalisieren("Schnitt", "FinalerSchnitt", "", True), "Finalisiert:")

# Opening
test("create_opening", lambda: bridge.erstelle_oeffnung("FinalerSchnitt", "rectangle", [0.01, 0.01, 0.0], [0.02, 0.02, 0.05], "TestOeffnung"), "Öffnung:")

# copy_to_floor
test("create_floor_eg", lambda: bridge.erstelle_stockwerk("TestEG"), "Floor:")
test("create_floor_og", lambda: bridge.erstelle_stockwerk("TestOG"), "Floor:")
test("create_wall_copy", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [2, 0, 0], "200mm", "2500mm", "TestWandEG"), "Erfolgreich:")
test("add_to_container_eg", lambda: bridge.fuege_zu_container_hinzu("TestWandEG", "TestEG"), "->")
test("copy_to_floor", lambda: bridge.kopiere_nach_geschoss(["TestWandEG"], "TestOG", 3.0, 0.0), "Kopiert:")

# Attika
test("create_slab_attika", lambda: bridge.erstelle_bodenplatte("3m", "2m", "200mm", "TestSlab"), "Slab:")
test("create_attika", lambda: bridge.erstelle_attika("TestSlab", 0.3, 0.3, 0.0, "TestAttika"), "Attika:")

# validate_model
test("validate_model", lambda: bridge.modell_validieren(), None)

# --- BIM ---
App.Console.PrintMessage("--- BIM ---\n")
test("create_site", lambda: bridge.erstelle_site("TestGelaende"), "Site:")
test("create_building", lambda: bridge.erstelle_gebaeude("TestHaus"), "Building:")
test("add_to_container_bim", lambda: bridge.fuege_zu_container_hinzu("TestHaus", "TestGelaende"), "->")

# validate_ifc_export
test("validate_ifc_export", lambda: bridge.validiere_ifc_export(), "IFC")

# align_walls_in_container
test("create_wall_nord", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [0, 3, 0], "200mm", "2500mm", "NordWand"), "Erfolgreich:")
test("add_container_nord", lambda: bridge.fuege_zu_container_hinzu("NordWand", "TestEG"), "->")
test("align_walls_container", lambda: bridge.waende_in_container_ausrichten("TestEG", "outside"), "Wände")

# slab_with_openings
test("slab_with_openings", lambda: bridge.erstelle_decke_mit_oeffnungen(
    "2m", "2m", "200mm", "0mm", "0mm", "0mm",
    [{"x": 0.5, "y": 0.5, "w": 0.3, "h": 0.3}], "TestDecke"), "Decke")

# --- Draft ---
App.Console.PrintMessage("--- Draft ---\n")
test("create_circle", lambda: bridge.erstelle_kreis("30mm", "0mm", "0mm", "0mm"), "Kreis:")
test("create_arc", lambda: bridge.erstelle_kreisbogen("0mm", "0mm", "0mm", "30mm", "0deg", "180deg"), "Bogen:")
test("delete_object", lambda: bridge.delete_object("TestPunkt"), "Gelöscht:")

# Zusammenfassung
App.Console.PrintMessage("\n=== TEST ERGEBNIS ===\n")
App.Console.PrintMessage(f"Bestanden: {passed}\n")
App.Console.PrintMessage(f"Fehlgeschlagen: {failed}\n")
if errors:
    App.Console.PrintMessage("Fehlerdetails:\n")
    for e in errors:
        App.Console.PrintMessage(f"  - {e}\n")
App.Console.PrintMessage(f"Tests: {passed + failed}, Pass: {passed}, Fail: {failed}\n")
App.Console.PrintMessage("=====================\n")
