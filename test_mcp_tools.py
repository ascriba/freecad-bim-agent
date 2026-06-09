import sys, os

if not hasattr(App, "_RobustFreeCADBridge"):
    P = "/home/arne/Programmierung/OpenCode/Freecad/freecad_bridge.py"
    exec(open(P).read().replace('if __name__ == "__main__":', 'if False:'))
    App._RobustFreeCADBridge = RobustFreeCADBridge

bridge = App._RobustFreeCADBridge()
doc = App.newDocument("MCP_Test")
App.setActiveDocument(doc.Name)

log = []
def L(msg):
    log.append(str(msg))

passed = 0
failed = 0
errors = []

def test(name, func, expected_prefix=None):
    global passed, failed
    try:
        result = func()
        status = str(result)[:80] if result else "OK"
        if expected_prefix and isinstance(result, str) and not result.startswith(expected_prefix):
            raise AssertionError(f"Expected '{expected_prefix}', got '{status}'")
        L(f"  PASS: {name} -> {status}")
        passed += 1
    except Exception as e:
        L(f"  FAIL: {name} -> {e}")
        failed += 1
        errors.append(f"{name}: {e}")
    try:
        App.ActiveDocument.recompute()
    except:
        pass

L("=== MCP Bridge Test ===")
L(f"Document: {doc.Name}")

L("--- Basis Geometrie ---")
test("create_cube", lambda: bridge.erstelle_wuerfel("50mm", "50mm", "50mm"), "Erfolg:")
test("create_cylinder", lambda: bridge.erstelle_zylinder("30mm", "60mm"), "Erfolg:")
test("create_sphere", lambda: bridge.erstelle_kugel("25mm"), "Erfolg:")
test("create_point", lambda: bridge.erstelle_punkt("0mm", "0mm", "0mm", "TestPunkt"), "Punkt:")
test("create_line", lambda: bridge.erstelle_draft_line("0,0,0", "100mm,0,0", "TestLinie"), "Draft-Linie:")
test("create_rect", lambda: bridge.erstelle_rechteck("100mm", "50mm", "0mm", "0mm", "0mm"), "Rechteck:")

L("--- Metadata & Utility ---")
test("list_objects", lambda: bridge.liste_objekte(), "Objekte:")
test("set_ifc_data", lambda: bridge.setze_ifc_daten("Wuerfel", '{"TestProp": "Test"}'), "IFC-Daten")
test("rename_object", lambda: bridge.umbenennen_objekt("Wuerfel", "TestWuerfel"), "Umbenannt:")
test("rename_zurueck", lambda: bridge.umbenennen_objekt("TestWuerfel", "Wuerfel"), "Umbenannt:")
test("set_visibility", lambda: bridge.sichtbarkeit_setzen("Kugel", False), "Sichtbarkeit")
test("set_visibility_on", lambda: bridge.sichtbarkeit_setzen("Kugel", True), "Sichtbarkeit")

L("--- New Tools: get_object_info, set_position, rotate ---")
test("get_object_info", lambda: bridge.objekt_info_abrufen("Wuerfel"), "Label:")
test("set_position", lambda: bridge.setze_position("Kugel", 0.1, 0.1, 0.0), "Position")
test("rotate", lambda: bridge.drehe_objekt("Zylinder", "Z", 45), "Gedreht:")

L("--- Boolean Operations ---")
test("boolean_union", lambda: bridge.bool_union("Wuerfel", "Zylinder"), "Fusion:")

L("--- Boolean Cut ---")
test("cube2", lambda: bridge.erstelle_wuerfel("50mm", "50mm", "50mm"), "Erfolg:")
for o in App.ActiveDocument.Objects:
    if o.Label.startswith("Wuerfel") and o.Name != "Wuerfel":
        bridge.umbenennen_objekt(o.Name, "CutBase"); break
test("cyl2", lambda: bridge.erstelle_zylinder("20mm", "60mm"), "Erfolg:")
for o in App.ActiveDocument.Objects:
    if o.Label.startswith("Zylinder") and o.Name != "Zylinder":
        bridge.umbenennen_objekt(o.Name, "CutTool"); break
test("boolean_cut", lambda: bridge.bool_cut("CutBase", "CutTool"), "Schnitt:")
test("boolean_cut_finalize", lambda: bridge.bool_cut_finalisieren("Schnitt", "FinalerSchnitt", "", True), "Finalisiert:")

L("--- Opening ---")
test("create_opening", lambda: bridge.erstelle_oeffnung("FinalerSchnitt", "rectangle", [0.01, 0.01, 0.0], [0.02, 0.02, 0.05], "TestOeffnung"), None)

L("--- Walls & Alignment ---")
test("create_wall", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [3, 0, 0], "300mm", "2500mm", "TestWand"), "Erfolgreich:")
test("align_wall", lambda: bridge.ausrichten_wand("TestWand", "Left"), "Erfolgreich:")
test("set_wall_alignment", lambda: bridge.wand_ausrichtung_setzen("TestWand", True), "Ausrichtung")
test("move_line", lambda: bridge.linie_verschieben("TestLinie", [0, 0, 0], [0.2, 0, 0]), "Linie")

L("--- copy_to_floor ---")
test("create_floor_eg", lambda: bridge.erstelle_stockwerk("TestEG"), "Floor:")
test("create_floor_og", lambda: bridge.erstelle_stockwerk("TestOG"), "Floor:")
test("create_wall_eg", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [2, 0, 0], "200mm", "2500mm", "TestWandEG"), "Erfolgreich:")
test("add_to_container", lambda: bridge.fuege_zu_container_hinzu("TestWandEG", "TestEG"), None)
test("copy_to_floor", lambda: bridge.kopiere_nach_geschoss(["TestWandEG"], "TestOG", 3.0, 0.0), "Kopiert:")

L("--- Attika ---")
test("create_slab", lambda: bridge.erstelle_bodenplatte("3m", "2m", "200mm", "TestSlab"), "Slab:")
test("create_attika", lambda: bridge.erstelle_attika("TestSlab", 0.3, 0.3, 0.0, "TestAttika"), "Attika:")

L("--- BIM ---")
test("create_site", lambda: bridge.erstelle_site("TestGelaende"), "Site:")
test("create_building", lambda: bridge.erstelle_gebaeude("TestHaus"), "Building:")
test("add_to_container_bim", lambda: bridge.fuege_zu_container_hinzu("TestHaus", "TestGelaende"), None)

L("--- Bulk Align ---")
test("create_wall_nord", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [0, 3, 0], "200mm", "2500mm", "NordWand"), "Erfolgreich:")
test("create_wall_ost", lambda: bridge.erstelle_wand_aus_punkten([0, 0, 0], [3, 0, 0], "200mm", "2500mm", "OstWand"), "Erfolgreich:")
test("add_wall_nord", lambda: bridge.fuege_zu_container_hinzu("NordWand", "TestEG"), None)
test("add_wall_ost", lambda: bridge.fuege_zu_container_hinzu("OstWand", "TestEG"), None)
test("align_walls_in_container", lambda: bridge.waende_in_container_ausrichten("TestEG", "outside"), None)

L("--- Slab with Openings ---")
test("slab_with_openings", lambda: bridge.erstelle_decke_mit_oeffnungen("2m", "2m", "200mm", "0mm", "0mm", "0mm", [{"x": 0.5, "y": 0.5, "w": 0.3, "h": 0.3}], "TestDecke"), "Decke")

L("--- Validation ---")
test("validate_model", lambda: bridge.modell_validieren(), None)
test("validate_ifc_export", lambda: bridge.validiere_ifc_export(), None)

L("--- Draft ---")
test("create_circle", lambda: bridge.erstelle_kreis("30mm", "0mm", "0mm", "0mm"), "Kreis:")
test("create_arc", lambda: bridge.erstelle_kreisbogen("0mm", "0mm", "0mm", "30mm", "0deg", "180deg"), "Bogen:")
test("delete_object", lambda: bridge.delete_object("TestPunkt"), None)

L("")
L(f"=== RESULT: {passed}/{passed+failed} passed, {failed} failed ===")
if errors:
    L("Errors:")
    for e in errors:
        L(f"  - {e}")

# Return result as final line for execute_python to capture
sys.stdout.write("\n".join(log) + "\n")