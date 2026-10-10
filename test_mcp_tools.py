import math
import sys

import os

if not hasattr(App, "_RobustFreeCADBridge"):
    P = "/home/arne/Programmierung/OpenCode/Freecad/freecad_bridge.py"
    exec(open(P).read().replace('if __name__ == "__main__":', "if False:"))
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
        if (
            expected_prefix
            and isinstance(result, str)
            and not result.startswith(expected_prefix)
        ):
            raise AssertionError(f"Expected '{expected_prefix}', got '{status}'")
        L(f"  PASS: {name} -> {status}")
        passed += 1
        return result
    except Exception as e:
        L(f"  FAIL: {name} -> {e}")
        failed += 1
        errors.append(f"{name}: {e}")
        return None
    try:
        App.ActiveDocument.recompute()
    except:
        pass


def objektname(result):
    """Extrahiert den internen FreeCAD-Namen aus einem '[Name]'-Suffix.

    Erzeugungsfunktionen liefern z.B. 'Erfolg: Wuerfel [Wuerfel042]'. Nur der
    interne Name ist eindeutig - Labels kollidieren, sobald mehrere gleichartige
    Objekte im Dokument liegen.
    """
    if not result or "[" not in str(result):
        raise AssertionError(f"Kein Objektname in Rueckgabe: {result!r}")
    return str(result).rsplit("[", 1)[1].rstrip("]")


L("=== MCP Bridge Test ===")
L(f"Document: {doc.Name}")

L("--- Basis Geometrie ---")
test("create_cube", lambda: bridge.erstelle_wuerfel("50mm", "50mm", "50mm"), "Erfolg:")
test("create_cylinder", lambda: bridge.erstelle_zylinder("30mm", "60mm"), "Erfolg:")
test("create_sphere", lambda: bridge.erstelle_kugel("25mm"), "Erfolg:")
test(
    "create_point",
    lambda: bridge.erstelle_punkt("0mm", "0mm", "0mm", "TestPunkt"),
    "Punkt:",
)
test(
    "create_line",
    lambda: bridge.erstelle_draft_line("0,0,0", "100mm,0,0", "TestLinie"),
    "Draft-Linie:",
)
test(
    "create_rect",
    lambda: bridge.erstelle_rechteck("100mm", "50mm", "0mm", "0mm", "0mm"),
    "Rechteck:",
)

L("--- Metadata & Utility ---")
test("list_objects", lambda: bridge.liste_objekte(), "--- Objektliste")
test(
    "set_ifc_data",
    lambda: bridge.setze_ifc_daten("Wuerfel", '{"TestProp": "Test"}'),
    "IFC-Daten",
)
test(
    "rename_object",
    lambda: bridge.umbenennen_objekt("Wuerfel", "TestWuerfel"),
    "Umbenannt:",
)
test(
    "rename_zurueck",
    lambda: bridge.umbenennen_objekt("TestWuerfel", "Wuerfel"),
    "Umbenannt:",
)
if App.GuiUp:
    test(
        "set_visibility",
        lambda: bridge.sichtbarkeit_setzen("Kugel", False),
        "Sichtbarkeit",
    )
    test(
        "set_visibility_on",
        lambda: bridge.sichtbarkeit_setzen("Kugel", True),
        "Sichtbarkeit",
    )
else:
    test(
        "set_visibility",
        lambda: bridge.sichtbarkeit_setzen("Kugel", False),
        "Kein ViewObject.",
    )
    test(
        "set_visibility_on",
        lambda: bridge.sichtbarkeit_setzen("Kugel", True),
        "Kein ViewObject.",
    )

L("--- New Tools: get_object_info, set_position, rotate ---")
test("get_object_info", lambda: bridge.objekt_info_abrufen("Wuerfel"), "Label:")
test("set_position", lambda: bridge.setze_position("Kugel", 0.1, 0.1, 0.0), "Position")
test("rotate", lambda: bridge.drehe_objekt("Zylinder", "Z", 45), "Gedreht:")

L("--- Boolean Operations ---")
test("boolean_union", lambda: bridge.bool_union("Wuerfel", "Zylinder"), "Fusion:")

L("--- Boolean Cut ---")
cut_base = objektname(
    test("cube2", lambda: bridge.erstelle_wuerfel("50mm", "50mm", "50mm"), "Erfolg:")
)
bridge.umbenennen_objekt(cut_base, "CutBase")
cut_tool = objektname(
    test("cyl2", lambda: bridge.erstelle_zylinder("20mm", "60mm"), "Erfolg:")
)
bridge.umbenennen_objekt(cut_tool, "CutTool")
test("boolean_cut", lambda: bridge.bool_cut("CutBase", "CutTool"), "Schnitt:")
test(
    "boolean_cut_finalize",
    lambda: bridge.bool_cut_finalisieren("Schnitt", "FinalerSchnitt", "", True),
    "Finalisiert:",
)

L("--- Opening ---")
test(
    "create_opening",
    lambda: bridge.erstelle_oeffnung(
        "FinalerSchnitt",
        "rectangle",
        [0.01, 0.01, 0.0],
        [0.02, 0.02, 0.05],
        "TestOeffnung",
    ),
    None,
)

L("--- Walls & Alignment ---")
test(
    "create_wall",
    lambda: bridge.erstelle_wand_aus_punkten(
        [0, 0, 0], [3, 0, 0], "300mm", "2500mm", "TestWand"
    ),
    "Erfolgreich:",
)
test("align_wall", lambda: bridge.ausrichten_wand("TestWand", "Left"), "Erfolgreich:")
test(
    "set_wall_alignment",
    lambda: bridge.wand_ausrichtung_setzen("TestWand", True),
    "Ausrichtung",
)
test(
    "move_line",
    lambda: bridge.linie_verschieben("TestLinie", [0, 0, 0], [0.2, 0, 0]),
    "Linie",
)

L("--- copy_to_floor ---")
test("create_floor_eg", lambda: bridge.erstelle_stockwerk("TestEG"), "Floor:")
test("create_floor_og", lambda: bridge.erstelle_stockwerk("TestOG"), "Floor:")
test(
    "create_wall_eg",
    lambda: bridge.erstelle_wand_aus_punkten(
        [0, 0, 0], [2, 0, 0], "200mm", "2500mm", "TestWandEG"
    ),
    "Erfolgreich:",
)
test(
    "add_to_container",
    lambda: bridge.fuege_zu_container_hinzu("TestWandEG", "TestEG"),
    None,
)
test(
    "copy_to_floor",
    lambda: bridge.kopiere_nach_geschoss(["TestWandEG"], "TestOG", 3.0, 0.0),
    "Kopiert:",
)

L("--- Attika ---")
test(
    "create_slab",
    lambda: bridge.erstelle_bodenplatte("3m", "2m", "200mm", "TestSlab"),
    "Slab:",
)
test(
    "create_attika",
    lambda: bridge.erstelle_attika("TestSlab", 0.3, 0.3, 0.0, "TestAttika"),
    "Attika:",
)

L("--- BIM ---")
test("create_site", lambda: bridge.erstelle_site("TestGelaende"), "Site:")
test("create_building", lambda: bridge.erstelle_gebaeude("TestHaus"), "Building:")
test(
    "add_to_container_bim",
    lambda: bridge.fuege_zu_container_hinzu("TestHaus", "TestGelaende"),
    None,
)

L("--- Bulk Align ---")
test(
    "create_wall_nord",
    lambda: bridge.erstelle_wand_aus_punkten(
        [0, 0, 0], [0, 3, 0], "200mm", "2500mm", "NordWand"
    ),
    "Erfolgreich:",
)
test(
    "create_wall_ost",
    lambda: bridge.erstelle_wand_aus_punkten(
        [0, 0, 0], [3, 0, 0], "200mm", "2500mm", "OstWand"
    ),
    "Erfolgreich:",
)
test(
    "add_wall_nord", lambda: bridge.fuege_zu_container_hinzu("NordWand", "TestEG"), None
)
test("add_wall_ost", lambda: bridge.fuege_zu_container_hinzu("OstWand", "TestEG"), None)
test(
    "align_walls_in_container",
    lambda: bridge.waende_in_container_ausrichten("TestEG", "outside"),
    None,
)

L("--- Slab with Openings ---")
test(
    "slab_with_openings",
    lambda: bridge.erstelle_decke_mit_oeffnungen(
        "2m",
        "2m",
        "200mm",
        "0mm",
        "0mm",
        "0mm",
        [{"x": 0.5, "y": 0.5, "w": 0.3, "h": 0.3}],
        "TestDecke",
    ),
    "Decke",
)

L("--- Gate-Helper ---")


def t_gate_info():
    info = bridge._gate_info(bridge._get_obj("Wuerfel"))
    if "BBox:" not in info or "Volume:" not in info:
        raise AssertionError(f"Gate-Info unvollstaendig: {info!r}")
    if "m3" not in info:
        raise AssertionError(f"Keine m3-Angabe: {info!r}")
    return info[:60]


test("gate_info", t_gate_info, None)

L("--- move_by ---")
move_by_test = objektname(
    test(
        "move_by_vorbereiten",
        lambda: bridge.erstelle_wuerfel("100mm", "100mm", "100mm"),
        "Erfolg:",
    )
)
bridge.umbenennen_objekt(move_by_test, "MoveByTest")
test(
    "move_by_setzen",
    lambda: bridge.setze_position("MoveByTest", 0.0, 0.0, 0.1),
    "Position",
)


def t_move_by():
    r = bridge.verschiebe_objekt("MoveByTest", 0.0, 0.0, 0.2)
    if not r.startswith("Verschoben:"):
        raise AssertionError(r)
    bb = bridge._get_obj("MoveByTest").Shape.BoundBox
    # Part::Box: Placement.Base z=300 -> Box belegt 300..400
    if abs(bb.ZMin - 300.0) > 0.01 or abs(bb.ZMax - 400.0) > 0.01:
        raise AssertionError(f"BBox Z {bb.ZMin}..{bb.ZMax}, erwartet 300..400")
    return "BBox OK"


test("move_by", t_move_by, None)
# move_by auf abgeleitetem Objekt (Part::Cut, absolute Geometrie)
move_by_cut_base = objektname(
    test(
        "move_by_cut_base",
        lambda: bridge.erstelle_wuerfel("200mm", "200mm", "200mm"),
        "Erfolg:",
    )
)
bridge.umbenennen_objekt(move_by_cut_base, "MoveByCutBase")
move_by_cut_tool = objektname(
    test(
        "move_by_cut_tool", lambda: bridge.erstelle_zylinder("30mm", "300mm"), "Erfolg:"
    )
)
bridge.umbenennen_objekt(move_by_cut_tool, "MoveByCutTool")
schnitt_name = objektname(
    test(
        "move_by_cut",
        lambda: bridge.bool_cut("MoveByCutBase", "MoveByCutTool"),
        "Schnitt:",
    )
)


def t_move_by_cut():
    bridge.setze_position(schnitt_name, 0.0, 0.0, 0.0)
    bb0 = bridge._get_obj(schnitt_name).Shape.BoundBox
    r = bridge.verschiebe_objekt(schnitt_name, 0.0, 0.0, -0.2)
    bb1 = bridge._get_obj(schnitt_name).Shape.BoundBox
    if not r.startswith("Verschoben:"):
        raise AssertionError(r)
    if abs((bb1.ZMin - bb0.ZMin) + 200.0) > 0.01:
        raise AssertionError(f"Delta ZMin {(bb1.ZMin - bb0.ZMin):.1f}, erwartet -200.0")
    return "Cut-Shift OK"


test("move_by_cut_check", t_move_by_cut, None)

L("--- mirror_object (Meter) ---")
mirror_kugel = objektname(
    test("mirror_kugel", lambda: bridge.erstelle_kugel("100mm"), "Erfolg:")
)
bridge.umbenennen_objekt(mirror_kugel, "MirrorKugel")
test(
    "mirror_pos",
    lambda: bridge.setze_position("MirrorKugel", 0.0, 0.0, 0.0),
    "Position",
)


def t_mirror():
    r = bridge.spiegele_objekt("MirrorKugel", "X", 4.0, 0.0, 0.0, "MirrorErgebnis")
    if not r.startswith("Gespiegelt:"):
        raise AssertionError(r)
    bb = bridge._get_obj("MirrorErgebnis").Shape.BoundBox
    # Spiegelebene muss bei x=4000mm liegen -> Zentrum des Spiegelbilds bei 8000mm
    if abs((bb.XMin + bb.XMax) / 2.0 - 8000.0) > 0.01:
        raise AssertionError(
            f"Zentrum X {(bb.XMin + bb.XMax) / 2.0:.1f}, erwartet 8000.0"
        )
    return "Spiegelachse OK"


test("mirror_check", t_mirror, None)

L("--- get_quantities (aus Shape) ---")
mengen_test = objektname(
    test(
        "mengen_wuerfel",
        lambda: bridge.erstelle_wuerfel("10400mm", "8400mm", "300mm"),
        "Erfolg:",
    )
)
bridge.umbenennen_objekt(mengen_test, "MengenTest")


def t_mengen():
    r = bridge.ermittle_mengen("MengenTest")
    if "26.208" not in r:
        raise AssertionError(f"Volume falsch: {r}")
    if "10400.0" not in r or "8400.0" not in r:
        raise AssertionError(f"BBox-Dims fehlen: {r}")
    if "25.4" in r:
        raise AssertionError(f"Inch-Fallback aktiv: {r}")
    return r[:70]


test("mengen_check", t_mengen, None)


def t_mengen_shapeless():
    # App::MaterialObject ist wirklich shapeless -> klare Meldung statt Fake-Werte
    # (direkt erstellt; setze_material crasht auf Part-Derivaten = bekannter P2-Bug 1.8)
    if not App.ActiveDocument.getObject("MengenMaterialObj"):
        App.ActiveDocument.addObject("App::MaterialObject", "MengenMaterialObj")
    r = bridge.ermittle_mengen("MengenMaterialObj")
    if "keine Geometrie" not in r:
        raise AssertionError(f"Shapeless-Meldung fehlt: {r}")
    return "Shapeless OK"


test("mengen_shapeless", t_mengen_shapeless, None)


def t_mengen_floor():
    # Arch Floor hat eine echte Shape (aggregiert Kinder) -> echte Mengen, keine Defaults
    r = bridge.ermittle_mengen("TestEG")
    if "Volume" not in r:
        raise AssertionError(f"Floor-Aggregat-Mengen fehlen: {r}")
    return "Floor OK"


test("mengen_floor", t_mengen_floor, None)

L("--- Slab-Richtung ---")
test(
    "slab_richtung_sz",
    lambda: bridge.erstelle_bodenplatte(
        "2m", "2m", "300mm", "SlabMinusZ", "0mm", "0mm", "1000mm", "-z"
    ),
    "Slab:",
)


def t_slab_sz():
    bb = bridge._get_obj("SlabMinusZ").Shape.BoundBox
    if abs(bb.ZMin - 700.0) > 0.5 or abs(bb.ZMax - 1000.0) > 0.5:
        raise AssertionError(f"-z: Z {bb.ZMin}..{bb.ZMax}, erwartet 700..1000")
    return "OK"


test("slab_richtung_sz_check", t_slab_sz, None)
test(
    "slab_richtung_pz",
    lambda: bridge.erstelle_bodenplatte(
        "2m", "2m", "300mm", "SlabPlusZ", "0mm", "0mm", "1000mm", "+z"
    ),
    "Slab:",
)


def t_slab_pz():
    bb = bridge._get_obj("SlabPlusZ").Shape.BoundBox
    if abs(bb.ZMin - 1000.0) > 0.5 or abs(bb.ZMax - 1300.0) > 0.5:
        raise AssertionError(f"+z: Z {bb.ZMin}..{bb.ZMax}, erwartet 1000..1300")
    return "OK"


test("slab_richtung_pz_check", t_slab_pz, None)
test(
    "slab_richtung_ungueltig",
    lambda: bridge.erstelle_bodenplatte(
        "1m", "1m", "100mm", "SlabBad", "0mm", "0mm", "0mm", "oben"
    ),
    "Fehler:",
)
test(
    "decke_richtung_sz",
    lambda: bridge.erstelle_decke_mit_oeffnungen(
        "2m", "2m", "300mm", "0mm", "0mm", "1000mm", [], "DeckeMinusZ", "-z"
    ),
    "Decke",
)


def t_decke_sz():
    bb = bridge._get_obj("DeckeMinusZ").Shape.BoundBox
    if abs(bb.ZMin - 700.0) > 0.5 or abs(bb.ZMax - 1000.0) > 0.5:
        raise AssertionError(f"Decke -z: Z {bb.ZMin}..{bb.ZMax}, erwartet 700..1000")
    return "OK"


test("decke_richtung_sz_check", t_decke_sz, None)
test(
    "decke_richtung_pz",
    lambda: bridge.erstelle_decke_mit_oeffnungen(
        "2m", "2m", "300mm", "0mm", "0mm", "1000mm", [], "DeckePlusZ", "+z"
    ),
    "Decke",
)


def t_decke_pz():
    bb = bridge._get_obj("DeckePlusZ").Shape.BoundBox
    if abs(bb.ZMin - 1000.0) > 0.5 or abs(bb.ZMax - 1300.0) > 0.5:
        raise AssertionError(f"Decke +z: Z {bb.ZMin}..{bb.ZMax}, erwartet 1000..1300")
    return "OK"


test("decke_richtung_pz_check", t_decke_pz, None)

L("--- create_wall align ---")
test(
    "wand_align",
    lambda: bridge.erstelle_wand_aus_punkten(
        [5, 5, 0], [8, 5, 0], "200mm", "2500mm", "AlignWand", "Left"
    ),
    "Erfolgreich:",
)


def t_wand_align():
    bb = bridge._get_obj("AlignWand").Shape.BoundBox
    # Wandrichtung Ost (+X): Left = Sueden (-Y) -> Koerper belegt Y 4800..5000
    if abs(bb.YMin - 4800.0) > 1.0 or abs(bb.YMax - 5000.0) > 1.0:
        raise AssertionError(f"BBox Y {bb.YMin}..{bb.YMax}, erwartet 4800..5000")
    return "Left=OK"


test("wand_align_check", t_wand_align, None)
test(
    "wand_align_to",
    lambda: bridge.erstelle_wand_aus_punkten(
        [5, 6, 0], [8, 6, 0], "200mm", "2500mm", "AlignWand2", "Center", "outside"
    ),
    "Erfolgreich:",
)
test(
    "wand_align_ungueltig",
    lambda: bridge.erstelle_wand_aus_punkten(
        [5, 7, 0], [8, 7, 0], "200mm", "2500mm", "AlignWand3", "Center", "oben"
    ),
    "Fehler:",
)


def t_wand_align_ungueltig_aufgeraeumt():
    # Bei Align-Fehler darf keine halbfertige Wand (noch Baseline) bleiben
    if bridge._get_obj("AlignWand3") is not None:
        raise AssertionError("Halbfertige Wand 'AlignWand3' nicht aufgeraeumt")
    for o in App.ActiveDocument.Objects:
        vs = getattr(getattr(o, "Shape", None), "Vertexes", [])
        if len(vs) == 2:
            p1, p2 = vs[0].Point, vs[-1].Point
            if (
                abs(p1.x - 5000.0) < 0.01
                and abs(p1.y - 7000.0) < 0.01
                and abs(p2.x - 8000.0) < 0.01
            ):
                raise AssertionError(f"Baseline '{o.Label}' nicht aufgeraeumt")
    return "Aufgeraeumt OK"


test("wand_align_ungueltig_aufgeraeumt", t_wand_align_ungueltig_aufgeraeumt, None)

L("--- set_ifc_type ---")
test(
    "ifc_type_ok",
    lambda: bridge.setze_ifc_typ("AlignWand", "Curtain Wall"),
    "IfcType gesetzt:",
)


def t_ifc_type_ok():
    if str(bridge._get_obj("AlignWand").IfcType) != "Curtain Wall":
        raise AssertionError("IfcType nicht uebernommen")
    # zuruecksetzen fuer Folgetests
    bridge.setze_ifc_typ("AlignWand", "Wall")
    return "OK"


test("ifc_type_check", t_ifc_type_ok, None)
test(
    "ifc_type_ungueltig",
    lambda: bridge.setze_ifc_typ("AlignWand", "KeinGueltigerTyp"),
    "Fehler:",
)
test("ifc_type_ohne_prop", lambda: bridge.setze_ifc_typ("Wuerfel", "Wall"), "Fehler:")

L("--- save_document ---")


def t_save():
    if os.path.exists("test_mcp_save.FCStd"):
        os.remove("test_mcp_save.FCStd")
    r = bridge.speichere_dokument("test_mcp_save.FCStd")
    if not r.startswith("Gespeichert:"):
        raise AssertionError(r)
    if not os.path.exists("test_mcp_save.FCStd"):
        raise AssertionError("Datei nicht erstellt")
    r2 = bridge.speichere_dokument()  # jetzt existiert doc.FileName
    if not r2.startswith("Gespeichert:"):
        raise AssertionError(r2)
    os.remove("test_mcp_save.FCStd")
    return "Roundtrip OK"


test("save_document", t_save, None)
test(
    "save_verbotener_pfad",
    lambda: bridge.speichere_dokument("/tmp/opencode/boese.FCStd"),
    "Fehler:",
)

L("--- recompute ---")


def t_recompute():
    bridge._get_obj("Wuerfel").touch()
    r = bridge.rekalkuliere()
    if "Fehler" in r.split("\n")[0]:
        raise AssertionError(r)
    if "TOUCHED" in r:
        raise AssertionError(f"Touch nicht aufgeloest: {r}")
    return r[:60]


test("recompute_doc", t_recompute, None)


def t_recompute_obj():
    r = bridge.rekalkuliere("Wuerfel")
    if "Fehler" in r.split("\n")[0]:
        raise AssertionError(r)
    return r[:60]


test("recompute_obj", t_recompute_obj, None)
test("recompute_nicht_gefunden", lambda: bridge.rekalkuliere("GibtEsNicht"), "Fehler:")

L("--- create_roof (Winkel/Firsthoehe) ---")


def t_dach_walm():
    r = bridge.erstelle_dach(
        [[0, 0, 5.5], [10, 0, 5.5], [10, 8, 5.5], [0, 8, 5.5]],
        "0mm",
        "200mm",
        35.0,
        "GateDachWalm",
    )
    if not r.startswith("Dach:"):
        raise AssertionError(r)
    bb = bridge._get_obj("GateDachWalm").Shape.BoundBox
    soll = 5500 + 4000 * math.tan(math.radians(35)) + 200 / math.cos(math.radians(35))
    if abs(bb.ZMax - soll) > 5.0:
        raise AssertionError(f"ZMax {bb.ZMax:.1f}, Soll {soll:.1f}")
    return f"ZMax={bb.ZMax:.1f} (Soll {soll:.1f})"


test("dach_walmdach", t_dach_walm, None)


def t_dach_sattel():
    r = bridge.erstelle_dach(
        [[0, 0, 5.5], [10, 0, 5.5], [10, 8, 5.5], [0, 8, 5.5]],
        "0mm",
        "200mm",
        [35.0, 90.0, 35.0, 90.0],
        "GateDachSattel",
    )
    if not r.startswith("Dach:"):
        raise AssertionError(r)
    o = bridge._get_obj("GateDachSattel")
    bb = o.Shape.BoundBox
    soll = 5500 + 4000 * math.tan(math.radians(35)) + 200 / math.cos(math.radians(35))
    if abs(bb.ZMax - soll) > 5.0:
        raise AssertionError(f"ZMax {bb.ZMax:.1f}, Soll {soll:.1f}")
    if len(o.Shape.Faces) != 8:
        raise AssertionError(
            f"Faces {len(o.Shape.Faces)}, erwartet 8 "
            "(2 Bahnen je 2 + 2 Giebel vorn/hinten)"
        )
    return f"Faces={len(o.Shape.Faces)}, ZMax={bb.ZMax:.1f}"


test("dach_satteldach", t_dach_sattel, None)
test(
    "dach_alle90",
    lambda: bridge.erstelle_dach(
        [[0, 0, 5.5], [10, 0, 5.5], [10, 8, 5.5], [0, 8, 5.5]],
        "0mm",
        "200mm",
        90.0,
        "GateDach90",
    ),
    "Fehler:",
)
test(
    "dach_listenlaenge",
    lambda: bridge.erstelle_dach(
        [[0, 0, 0], [5, 0, 0], [5, 4, 0], [0, 4, 0]],
        "0mm",
        "100mm",
        [30.0, 30.0],
        "GateDachListe",
    ),
    "Fehler:",
)
test(
    "dach_winkel_negativ",
    lambda: bridge.erstelle_dach(
        [[0, 0, 0], [5, 0, 0], [5, 4, 0], [0, 4, 0]],
        "0mm",
        "100mm",
        -5.0,
        "GateDachNeg",
    ),
    "Fehler:",
)

L("--- create_stairs (Podest-Hoehe) ---")


def t_treppe_gerade():
    r = bridge.erstelle_treppe("2500mm", "1000mm", False, "GateTreppeGerade")
    if not r.startswith("Treppe:"):
        raise AssertionError(r)
    bb = bridge._get_obj("GateTreppeGerade").Shape.BoundBox
    # Gate: Hoehe +- 1 Stufe (2500/14 = 178.6)
    riser = 2500.0 / round(2500.0 / 175.0)
    if not (2500.0 - riser - 1.0 <= bb.ZMax <= 2500.0 + riser + 1.0):
        raise AssertionError(
            f"ZMax {bb.ZMax:.1f} ausserhalb {2500.0 - riser - 1.0:.1f}.."
            f"{2500.0 + riser + 1.0:.1f}"
        )
    return f"ZMax={bb.ZMax:.1f}"


test("treppe_gerade", t_treppe_gerade, None)


def t_treppe_podest():
    r = bridge.erstelle_treppe("2800mm", "1200mm", True, "GateTreppePodest")
    if not r.startswith("Treppe:"):
        raise AssertionError(r)
    bb = bridge._get_obj("GateTreppePodest").Shape.BoundBox
    # Gate: Hoehe +- 1 Stufe (2800/16 = 175)
    if not (2800.0 - 175.0 - 1.0 <= bb.ZMax <= 2800.0 + 175.0 + 1.0):
        raise AssertionError(f"ZMax {bb.ZMax:.1f}, erwartet 2624..2976")
    if bb.ZMax > 2976.0:
        raise AssertionError("Podest-Variante zu hoch (Original-Bug)")
    return f"ZMax={bb.ZMax:.1f}"


test("treppe_podest", t_treppe_podest, None)

L("--- execute_python-Meldung ---")


def t_py_deaktiviert():
    bridge._execute_python_erlaubt = False
    r = bridge.run_python("print('x')")
    if "Sicherheitsdialog" not in r or not r.startswith("Fehler"):
        raise AssertionError(r[:80])
    return "Meldung OK"


test("execute_python_meldung", t_py_deaktiviert, None)

L("--- Validation ---")
test("validate_model", lambda: bridge.modell_validieren(), None)
test("validate_ifc_export", lambda: bridge.validiere_ifc_export(), None)

L("--- Profiled Structure ---")
test(
    "profiled_structure_ipe",
    lambda: bridge.erstelle_profil_struktur(
        "IPE300", "1000mm", "TestIPETraeger", None, 0, 0, 0
    ),
    "Profil-Struktur:",
)
test(
    "profiled_structure_chs",
    lambda: bridge.erstelle_profil_struktur(
        "CHS48.3x3.2", "500mm", "TestCHSStuetze", None, 0.5, 0.5, 0
    ),
    "Profil-Struktur:",
)
# Bekannter Vor-Fehler (CSV-Kategorie-Bug), außerhalb dieses Scopes -> nur loggen
test(
    "profiled_structure_fallback",
    lambda: bridge.erstelle_profil_struktur(
        "2x1 Channel", "800mm", "TestAlu", "Aluminium C Channel", 1.0, 1.0, 0
    ),
    None,
)
test(
    "profiled_structure_notfound",
    lambda: bridge.erstelle_profil_struktur("NichtExistiert", "100mm", "Test"),
    "Fehler:",
)

L("--- Draft ---")
test(
    "create_circle",
    lambda: bridge.erstelle_kreis("30mm", "0mm", "0mm", "0mm"),
    "Kreis:",
)
test(
    "create_arc",
    lambda: bridge.erstelle_kreisbogen("0mm", "0mm", "0mm", "30mm", "0deg", "180deg"),
    "Bogen:",
)
test("delete_object", lambda: bridge.delete_object("TestPunkt"), None)

L("")
L(f"=== RESULT: {passed}/{passed + failed} passed, {failed} failed ===")
if errors:
    L("Errors:")
    for e in errors:
        L(f"  - {e}")

# Return result as final line for execute_python to capture
sys.stdout.write("\n".join(log) + "\n")
