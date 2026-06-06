from mcp.server.fastmcp import FastMCP, Image
import xmlrpc.client
import sys
import base64
import os
from dotenv import load_dotenv

# Lade Umgebungsvariablen aus .env Datei
load_dotenv()

# Initialisiere FastMCP
mcp = FastMCP("FreeCAD")

# Verbindung zur FreeCAD-Bridge
FREE_CAD_BRIDGE_URL = "http://localhost:8000"

def get_bridge():
    """Erstellt eine neue Verbindung zur Bridge."""
    return xmlrpc.client.ServerProxy(FREE_CAD_BRIDGE_URL)

@mcp.tool()
def create_cube(length: str = "10mm", width: str = "10mm", height: str = "10mm") -> str:
    """
    Erstellt einen Würfel. Unterstützt Einheiten (z.B. '10m', '50cm', '100mm').
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_wuerfel(length, width, height)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_cylinder(radius: str = "5mm", height: str = "10mm") -> str:
    """
    Erstellt einen Zylinder. Unterstützt Einheiten.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_zylinder(radius, height)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def list_objects() -> str:
    """
    Gibt eine Liste aller vorhandenen Objekte in der aktuellen FreeCAD-Sitzung zurück.
    Hilfreich, um zu sehen, was bereits modelliert wurde.
    """
    try:
        bridge = get_bridge()
        return bridge.liste_objekte()
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def delete_object(name: str) ->str:
    """Löscht ein Objekt in der aktuellen FreeCAD-Sitzung"""
    try:
        bridge = get_bridge()
        return bridge.delete_object(name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def set_position(name: str, x: float = 0.0, y: float = 0.0, z: float = 0.0) -> str:
    """
    Verschiebt ein Objekt in FreeCAD an eine neue Position (X, Y, Z).
    
    Args:
        name: Der Name des Objekts (z.B. 'Box', 'Cylinder')
        x: X-Koordinate
        y: Y-Koordinate
        z: Z-Koordinate
    """
    try:
        bridge = get_bridge()
        return bridge.setze_position(name, x, y, z)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def rotate_object(name: str, axis: str = "Z", angle: float = 45.0) -> str:
    """
    Dreht ein Objekt in FreeCAD um eine bestimmte Achse (X, Y oder Z).
    
    Args:
        name: Der Name des Objekts
        axis: Die Achse, um die gedreht werden soll ('X', 'Y' oder 'Z')
        angle: Der Winkel in Grad (Standard: 45.0)
    """
    try:
        bridge = get_bridge()
        return bridge.drehe_objekt(name, axis, angle)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def capture_view(view_type: str = "iso") -> Image:
    """
    Erstellt einen Screenshot der aktuellen 3D-Ansicht in FreeCAD.
    Ermöglicht dem Modell, das Ergebnis visuell zu prüfen.
    
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

@mcp.tool()
def boolean_union(obj_a: str, obj_b: str) -> str:
    """
    Vereinigt zwei Objekte in FreeCAD (Fusion).
    """
    try:
        bridge = get_bridge()
        return bridge.bool_union(obj_a, obj_b)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def boolean_cut(base_obj: str, tool_obj: str) -> str:
    """
    Zieht ein Objekt (tool_obj) von einem anderen (base_obj) ab.
    Nützlich, um Löcher zu bohren oder Formen auszuschneiden.
    """
    try:
        bridge = get_bridge()
        return bridge.bool_cut(base_obj, tool_obj)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_sphere(radius: str = "5mm") -> str:
    """
    Erstellt eine Kugel in FreeCAD. Unterstützt Einheiten (z.B. '2m').
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_kugel(radius)
    except Exception as e:
        return f"Fehler: {str(e)}"

# --- BIM / Arch Tools ---
#################################################################################
@mcp.tool()
def create_site(name: str = "ProjektGelaende") -> str:
    """
    Erstellt ein Grundstück (Arch Site).
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_site(name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_building(name: str = "MeinHaus") -> str:
    """
    Erstellt ein Gebäude (Arch Building).
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_gebaeude(name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_floor(name: str = "Erdgeschoss") -> str:
    """
    Erstellt ein Stockwerk (Arch Floor/Storey).
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_stockwerk(name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def add_to_container(object_name: str, container_name: str) -> str:
    """
    Fügt ein Objekt einem Container hinzu (z.B. Stockwerk zu Gebäude).
    """
    try:
        bridge = get_bridge()
        return bridge.fuege_zu_container_hinzu(object_name, container_name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def add_to_container_batch(object_names: list[str], container_name: str) -> str:
    """
    Fügt mehrere Objekte auf einmal zu einem Container hinzu.
    
    Args:
        object_names: Liste von Namen/Labeln der Objekte.
        container_name: Name/Label des Containers (z.B. "Erdgeschoss").
    """
    try:
        bridge = get_bridge()
        return bridge.fuege_mehrere_zu_container_hinzu(object_names, container_name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_slab(length: str = "10m", width: str = "8m", height: str = "300mm", name: str = "Bodenplatte",
                placement_x: str = "0mm", placement_y: str = "0mm", placement_z: str = "0mm") -> str:
    """
    Erstellt eine Slab (Bodenplatte).
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_bodenplatte(length, width, height, name, placement_x, placement_y, placement_z)
    except Exception as e: return f"Fehler: {str(e)}"


@mcp.tool()
def join_walls(
        walls: list[str] = ['Wall1', "Wall2", "Wall3"]):
    """
    Vereinigt Wände zu einem Wall-Objekt.
    Die Namen der Wände MÜSSEN als list übergeben werden.
    """
    try:
        bridge = get_bridge()
        # Übergabe der Punkte und Maße an deine Bridge
        return bridge.vereinigen_Wand(walls)
    except Exception as e: 
        return f"Fehler im MCP-Tool beim Erstellen der Wand: {str(e)}"


@mcp.tool()
def create_wall(
    p1: list[float] = [0.0, 0.0, 0.0],
    p2: list[float] = [5000.0, 0.0, 0.0],
    width: str = "300mm",
    height: str = "2500mm",
    name: str = "Aussenwand1"
) -> str:
    """
    Erstellt eine gerade Wand (Arch Wall) zwischen zwei 3D-Punkten.

    Args:
        p1: Startpunkt als [X, Y, Z] Koordinate in METERN (z.B. [0, 0, 0]).
        p2: Endpunkt als [X, Y, Z] Koordinate in METERN (z.B. [5.0, 0, 0] für eine 5m lange Wand).
        width: Die Dicke der Wand mit Einheit (z.B. '300mm').
        height: Die Höhe der Wand mit Einheit (z.B. '2500mm').
        name: Das sichtbare Label der Wand in FreeCAD.
    """
    try:
        bridge = get_bridge()
        # Übergabe der Punkte und Maße an deine Bridge
        return bridge.erstelle_wand_aus_punkten(p1, p2, width, height, name)
    except Exception as e: 
        return f"Fehler im MCP-Tool beim Erstellen der Wand: {str(e)}"

@mcp.tool()
def align_wall(wand_bezeichnung, align="Left", align_to=None):
    """
    Ausrichten einer Wand

    Args:
    wand_bezeichnung : Label oder Name der Wand
    align : zulässig sind "Left", "Center" oder "Right". Wirkt nur wenn align_to nicht gesetzt ist.
    align_to : Alternativ zu align: "inside" (zur Gebäudeinnenseite), "outside" (zur Außenseite),
               "left", "center", "right". Überschreibt align wenn gesetzt.
    """
    try:
        bridge = get_bridge()
        return bridge.ausrichten_wand(wand_bezeichnung, align, align_to)
    except Exception as e: 
        return f"Fehler im MCP-Tool Wand_ausrichten: {str(e)}"

@mcp.tool()
def create_window(
    wall_ident: str = "Wand",
    distance_from_start: str = "1.5m",
    width: str = "900mm",
    height: str = "2000mm",
    sill_height: str = "0mm",
    windowtype: str = "Simple door",
    name: str = "Fenster",
    wall_name: str | None = None
) -> str:
    """
    Erstellt ein Fenster oder eine Tür und fügt sie passgenau in eine bestehende Wand ein.

    Args:
        wall_ident: Das sichtbare Label der Wand in FreeCAD (z.B. 'Aussenwand1'). 
        distance_from_start: Abstand vom Startpunkt der Wand (z.B. '1.5m' oder '500mm').
        width: Breite des Fensters/der Tür (z.B. '900mm').
        height: Höhe des Fensters/der Tür (z.B. '2000mm').
        sill_height: Brüstungshöhe vom Boden aus. '0mm' für Türen, z.B. '900mm' für Fenster.
        windowtype: Der Standard-Typ des Fensters ist 'Fixed', der Standard-Typ für Türen ist 'Simple door'.
        mögliche windowtype sind: "Fixed", "Open 1-pane", "Open 2-pane", "Sash 2-pane",
                  "Sliding 2-pane", "Simple door", "Glass door", "Sliding 4-pane", "Awning"
        name: Das Label des Fensters in FreeCAD.
        wall_name: Alternativer Name/Label der Wand (Alias für wall_ident).
    """
    try:
        bridge = get_bridge()

        actual_wall = wall_name if wall_name else wall_ident

        result = bridge.fuege_fenster_ein(
            actual_wall,
            distance_from_start,
            width,
            height,
            sill_height,
            windowtype,
            name
        )
        return result

    except Exception as e:
        return f"Fehler im MCP-Tool create_window() beim Erstellen: {str(e)}"

@mcp.tool()
def create_point(x: str = "0mm", y: str = "0mm", z: str = "0mm", name: str = "Punkt") -> str:
    """
    Erstellt ein Draft-Punktobjekt bei den angegebenen Koordinaten.
    Koordinaten können als Einheiten-Strings angegeben werden (z.B. '100mm').
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_punkt(x, y, z, name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_line(p1: str = "0mm,0mm,0mm", p2: str = "1000mm,0mm,0mm", name: str = "Linie") -> str:
    """
    Erstellt eine Draft-Linie zwischen zwei Punkten.
    Punkte können als Komma-getrennte Strings (z.B. '0,0,0') oder mit Einheiten (z.B. '10m,2m,0m') angegeben werden.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_draft_line(p1, p2, name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_polyline(points: list, closed: bool = True, name: str = "Polyline") -> str:
    """
    Erstellt einen Draft-Linienzug aus einer Liste von Punkten.
    'points' sollte eine Liste von Koordinaten-Strings oder Listen sein, z.B. ['0,0,0', '10,0,0', '10,10,0'].
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_draft_polyline(points, closed)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_rectangle(length: str = "100mm", width: str = "50mm",
                    placement_x: str = "0mm", placement_y: str = "0mm", placement_z: str = "0mm") -> str:
    """
    Erstellt ein Draft-Rechteck.
    Dimensionen und Platzierung können als Einheiten-Strings angegeben werden.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_rechteck(length, width, placement_x, placement_y, placement_z)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_circle(radius: str = "50mm", placement_x: str = "0mm", placement_y: str = "0mm", placement_z: str = "0mm") -> str:
    """
    Erstellt einen Draft-Kreis.
    Radius und Platzierung können als Einheiten-Strings angegeben werden.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_kreis(radius, placement_x, placement_y, placement_z)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_arc(center_x: str = "0mm", center_y: str = "0mm", center_z: str = "0mm", 
               radius: str = "50mm", start_angle: str = "0deg", end_angle: str = "90deg") -> str:
    """
    Erstellt einen Draft-Kreisbogen.
    Zentrums-Koordinaten, Radius und Winkel können als Einheiten/Grad-Strings angegeben werden.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_kreisbogen(center_x, center_y, center_z, radius, start_angle, end_angle)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def set_ifc_data(object_name: str, properties_json: str = "{}") -> str:
    """
    Weist einem FreeCAD-Objekt zusätzliche benutzerdefinierte Eigenschaften zu.
    properties_json sollte ein JSON-String sein, z.B. '{"Material": "Beton", "Brandschutzklasse": "F90"}'.
    Beachten Sie, dass der 'ifc_type' jetzt implizit von FreeCAD verwaltet wird und dieses Tool sich auf benutzerdefinierte Eigenschaften konzentriert.
    """
    try:
        bridge = get_bridge()
        return bridge.setze_ifc_daten(object_name, properties_json)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def set_material(object_name: str, material_name: str, color_rgb: str = "(0.8, 0.8, 0.8)") -> str:
    """
    Weist einem FreeCAD-Objekt ein Material zu.
    `color_rgb` als String "(R, G, B)" mit Werten von 0.0 bis 1.0.
    """
    try:
        bridge = get_bridge()
        # Parse color_rgb string to tuple
        rgb_tuple = tuple(map(float, color_rgb.strip("()").split(",")))
        return bridge.setze_material(object_name, material_name, rgb_tuple)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def set_material_batch(object_names: list[str], material_name: str, color_rgb: str = "(0.8, 0.8, 0.8)") -> str:
    """
    Weist mehreren Objekten auf einmal ein Material zu.
    
    Args:
        object_names: Liste von Namen/Labeln der Objekte.
        material_name: Name des Materials.
        color_rgb: Farbe als String "(R, G, B)" mit Werten 0.0 bis 1.0.
    """
    try:
        bridge = get_bridge()
        rgb_tuple = tuple(map(float, color_rgb.strip("()").split(",")))
        return bridge.setze_material_mehrere(object_names, material_name, rgb_tuple)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def get_quantities(object_name: str) -> str:
    """
    Ermittelt mengenbezogene Informationen (Fläche, Volumen, etc.) eines FreeCAD-Objekts.
    """
    try:
        bridge = get_bridge()
        return bridge.ermittle_mengen(object_name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def add_to_wall(wall_name: str, component_name: str) -> str:
    """
    Fügt ein Fenster oder eine Tür in eine Wand ein. 
    Die Wand schneidet automatisch ein passendes Loch für das Objekt.
    """
    try:
        bridge = get_bridge()
        return bridge.fuege_zu_wand_hinzu(wall_name, component_name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_structure(length: str = "100mm", width: str = "20mm", height: str = "20mm", name: str = "Balken",
                    position_x: float | None = None,
                    position_y: float | None = None,
                    position_z: float | None = None) -> str:
    """
    Erstellt ein Tragwerk-Element (Arch Structure) wie einen Balken oder eine Säule. Unterstützt Einheiten.
    Optionale position_x/y/z setzen die Position in METERN.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_struktur(length, width, height, name, position_x, position_y, position_z)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def execute_python(script: str) -> str:
    """
    ULTIMATIVES WERKZEUG: Führt beliebigen Python-Code direkt in FreeCAD aus.
    Benutze dieses Tool IMMER, wenn es kein spezialisiertes Tool für eine Aufgabe gibt 
    (z.B. für Spheres (falls create_sphere fehlt), Torus, Lofts, Fillets, Offsets etc.).
    Du hast vollen Zugriff auf 'App', 'Gui' und 'Part'.
    
    Beispiel für eine Kugel: 'App.ActiveDocument.addObject("Part::Sphere", "MySphere")'
    """
    try:
        bridge = get_bridge()
        return bridge.run_python(script)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def export_ifc(file_path: str = "model.ifc") -> str:
    """
    Exportiert das aktuelle FreeCAD-Dokument als Industry Foundation Classes (IFC)-Datei.
    Dies ermöglicht den Datenaustausch mit anderer BIM-Software.
    """
    try:
        bridge = get_bridge()
        return bridge.exportiere_ifc(file_path)
    except Exception as e:
        return f"Fehler beim IFC-Export: {str(e)}"

@mcp.tool()
def analyze_ifc(file_path: str) -> str:
    """
    Analysiert eine IFC-Datei und gibt eine Zusammenfassung ihrer Inhalte zurück,
    einschließlich Projektname und enthaltener Entitätstypen.
    Erfordert die 'ifcopenshell'-Bibliothek in FreeCAD.
    """
    try:
        bridge = get_bridge()
        return bridge.analysiere_ifc(file_path)
    except Exception as e:
        return f"Fehler bei der IFC-Analyse: {str(e)}"

# --- BIM Erweiterung Phase 1 ---
@mcp.tool()
def create_roof(
    basewire: list[list[float]],
    overhang: str = "500mm",
    thickness: str = "100mm",
    angle: float = 30.0,
    name: str = "Dach"
) -> str:
    """
    Erstellt ein Dach (Arch Roof) aus einem geschlossenen Linienzug.

    Args:
        basewire: Liste von [X,Y,Z]-Punkten in METERN für den Dachumriss (z.B. [[0,0,0], [5,0,0], [5,4,0], [0,4,0]]).
        overhang: Dachüberstand mit Einheit (z.B. '500mm').
        thickness: Dicke der Dachdeckung mit Einheit (z.B. '100mm').
        angle: Dachneigung in Grad (z.B. 30.0).
        name: Label des Dachs in FreeCAD.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_dach(basewire, overhang, thickness, angle, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_stairs(
    length: str = "1000mm",
    width: str = "1200mm",
    height: str = "2500mm",
    steps_count: int = 14,
    stringer_thickness: str = "50mm",
    name: str = "Treppe"
) -> str:
    """
    Erstellt eine Treppe (Arch Stairs).

    Args:
        length: Gesamtlauflänge der Treppe (z.B. '1000mm').
        width: Breite der Treppe (z.B. '1200mm').
        height: Geschosshöhe (z.B. '2500mm').
        steps_count: Anzahl der Stufen (z.B. 14).
        stringer_thickness: Wangenstärke (z.B. '50mm').
        name: Label der Treppe in FreeCAD.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_treppe(length, width, height, steps_count, stringer_thickness, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_axes(axes: list[dict]) -> str:
    """
    Erstellt mehrere Bauachsen auf einmal.
    
    Args:
        axes: Liste von Dicts mit label, x, y, z, direction.
               Z.B. [{"label": "1", "x": "0mm", "y": "0mm", "direction": "Y"},
                      {"label": "2", "x": "5000mm", "y": "0mm", "direction": "Y"}]
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_mehrere_achsen(axes)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_axis(
    x: str = "0mm",
    y: str = "0mm",
    z: str = "0mm",
    direction: str = "Z",
    label: str = "1"
) -> str:
    """
    Erstellt eine Bauachse (Arch Axis).

    Args:
        x: X-Position mit Einheit (z.B. '0mm').
        y: Y-Position mit Einheit (z.B. '0mm').
        z: Z-Position mit Einheit (z.B. '0mm').
        direction: Achsenrichtung ('X', 'Y' oder 'Z').
        label: Achsenbezeichnung (z.B. '1', 'A').
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_achse(x, y, z, direction, label)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_axis_system(
    axes: list[str],
    name: str = "Achsensystem"
) -> str:
    """
    Erstellt ein Achssystem (Arch AxisSystem) aus mehreren Achsen.

    Args:
        axes: Liste von Achsen-Labels (z.B. ['1', '2', '3', 'A', 'B']).
        name: Label des Achssystems in FreeCAD.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_achsensystem(axes, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_section_plane(
    x: str = "0mm",
    y: str = "0mm",
    z: str = "1500mm",
    direction: str = "Z",
    name: str = "Schnitt_A"
) -> str:
    """
    Erstellt eine Schnittebene (Arch SectionPlane) für Grundrisse und Schnitte.

    Args:
        x: X-Position der Schnittebene (z.B. '0mm').
        y: Y-Position der Schnittebene (z.B. '0mm').
        z: Z-Position/Höhe der Schnittebene (z.B. '1500mm' für 1,5m Schnitthöhe).
        direction: Blickrichtung der Schnittebene ('X', 'Y' oder 'Z').
        name: Label der Schnittebene.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_schnittebene(x, y, z, direction, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def clone_object(
    source_name: str,
    new_name: str = "Klon"
) -> str:
    """
    Erstellt einen Klon eines bestehenden FreeCAD-Objekts (Draft Clone).

    Args:
        source_name: Name oder Label des zu klonenden Objekts.
        new_name: Label des Klons in FreeCAD.
    """
    try:
        bridge = get_bridge()
        return bridge.klone_objekt(source_name, new_name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def mirror_object(
    source_name: str,
    axis: str = "X",
    origin_x: float = 0.0,
    origin_y: float = 0.0,
    origin_z: float = 0.0,
    new_name: str = "Gespiegelt"
) -> str:
    """
    Spiegelt ein FreeCAD-Objekt an einer Achse (Part Mirror).

    Args:
        source_name: Name oder Label des zu spiegelnden Objekts.
        axis: Spiegelachse ('X', 'Y' oder 'Z').
        origin_x: X-Koordinate des Spiegelursprungs.
        origin_y: Y-Koordinate des Spiegelursprungs.
        origin_z: Z-Koordinate des Spiegelursprungs.
        new_name: Label des gespiegelten Objekts.
    """
    try:
        bridge = get_bridge()
        return bridge.spiegele_objekt(source_name, axis, origin_x, origin_y, origin_z, new_name)
    except Exception as e:
        return f"Fehler: {str(e)}"

# --- BIM Erweiterung Phase 2 ---
@mcp.tool()
def create_text(
    text: str,
    x: str = "0mm",
    y: str = "0mm",
    z: str = "0mm",
    font_size: str = "100mm",
    name: str = "Text"
) -> str:
    """
    Erstellt einen Draft-Text in der 3D-Ansicht.

    Args:
        text: Der anzuzeigende Text (String).
        x: X-Position mit Einheit (z.B. '0mm').
        y: Y-Position mit Einheit (z.B. '0mm').
        z: Z-Position mit Einheit (z.B. '0mm').
        font_size: Schriftgrösse mit Einheit (z.B. '100mm').
        name: Label des Textes in FreeCAD.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_text(text, x, y, z, font_size, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_dimension(
    p1: list[float],
    p2: list[float],
    p3: list[float],
    name: str = "Mass"
) -> str:
    """
    Erstellt eine Draft-Bemaessung zwischen zwei Punkten.

    Args:
        p1: Startpunkt als [X,Y,Z] in METERN.
        p2: Endpunkt als [X,Y,Z] in METERN.
        p3: Punkt fuer die Masslinien-Position als [X,Y,Z] in METERN.
        name: Label der Bemaessung.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_bemassung(p1, p2, p3, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def fillet(
    object_name: str,
    radius: str = "5mm",
    edge_indices: list[int] | None = None,
    name: str = "Verrundet"
) -> str:
    """
    Verrundet Kanten eines Objekts (Part Fillet).

    Args:
        object_name: Name oder Label des Objekts.
        radius: Radius der Verrundung mit Einheit (z.B. '5mm').
        edge_indices: Liste von Kanten-Indizes (z.B. [0, 1, 2]). Leere Liste = alle Kanten.
        name: Label des verrundeten Objekts.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_verrundung(object_name, radius, edge_indices or [], name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def chamfer(
    object_name: str,
    length: str = "5mm",
    edge_indices: list[int] | None = None,
    name: str = "Gefast"
) -> str:
    """
    Fast Kanten eines Objekts (Part Chamfer).

    Args:
        object_name: Name oder Label des Objekts.
        length: Laenge der Fase mit Einheit (z.B. '5mm').
        edge_indices: Liste von Kanten-Indizes (z.B. [0, 1, 2]). Leere Liste = alle Kanten.
        name: Label des gefasten Objekts.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_fase(object_name, length, edge_indices or [], name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_panel(
    length: str = "1000mm",
    width: str = "500mm",
    thickness: str = "50mm",
    name: str = "Paneel"
) -> str:
    """
    Erstellt ein Arch-Panel (Paneel/Platte).

    Args:
        length: Laenge des Paneels mit Einheit (z.B. '1000mm').
        width: Breite des Paneels mit Einheit (z.B. '500mm').
        thickness: Dicke des Paneels mit Einheit (z.B. '50mm').
        name: Label des Paneels.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_paneel(length, width, thickness, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def import_dxf(
    file_path: str
) -> str:
    """
    Importiert eine DXF-Datei in FreeCAD.

    Args:
        file_path: Pfad zur DXF-Datei.
    """
    try:
        bridge = get_bridge()
        return bridge.importiere_dxf(file_path)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def export_dxf(
    file_path: str = "export.dxf"
) -> str:
    """
    Exportiert das aktuelle FreeCAD-Dokument als DXF.

    Args:
        file_path: Zielpfad fuer die DXF-Datei.
    """
    try:
        bridge = get_bridge()
        return bridge.exportiere_dxf(file_path)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def export_pdf(
    file_path: str = "plan.pdf"
) -> str:
    """
    Exportiert die aktuelle Seite (TechDraw) als PDF.

    Args:
        file_path: Zielpfad fuer die PDF-Datei.
    """
    try:
        bridge = get_bridge()
        return bridge.exportiere_pdf(file_path)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def export_svg(
    file_path: str = "export.svg"
) -> str:
    """
    Exportiert das aktuelle FreeCAD-Dokument als SVG.

    Args:
        file_path: Zielpfad fuer die SVG-Datei.
    """
    try:
        bridge = get_bridge()
        return bridge.exportiere_svg(file_path)
    except Exception as e:
        return f"Fehler: {str(e)}"

# --- BIM Erweiterung Phase 3 ---
@mcp.tool()
def create_window_sketch(
    wall_ident: str,
    width: str = "900mm",
    height: str = "1200mm",
    sill_height: str = "900mm",
    name: str = "Fenster_Skizze"
) -> str:
    """
    Erstellt ein benutzerdefiniertes Fenster in einer Wand (aus Rechteck-Skizze).

    Args:
        wall_ident: Label der Zielwand.
        width: Breite des Fensters mit Einheit (z.B. '900mm').
        height: Hoehe des Fensters mit Einheit (z.B. '1200mm').
        sill_height: Brüstungshöhe mit Einheit (z.B. '900mm').
        name: Label des Fensters.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_fenster_skizze(wall_ident, width, height, sill_height, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_curtain_wall(
    basewire: list[list[float]],
    panel_width: str = "1000mm",
    panel_height: str = "2500mm",
    name: str = "Vorhangfassade"
) -> str:
    """
    Erstellt eine Vorhangfassade (Arch CurtainWall) entlang eines Linienzugs.

    Args:
        basewire: Liste von [X,Y,Z]-Punkten in METERN fuer den Verlauf.
        panel_width: Panelbreite mit Einheit (z.B. '1000mm').
        panel_height: Panelhoehe mit Einheit (z.B. '2500mm').
        name: Label der Vorhangfassade.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_vorhangfassade(basewire, panel_width, panel_height, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_pipe(
    basewire: list[list[float]],
    outer_diameter: str = "100mm",
    wall_thickness: str = "5mm",
    name: str = "Rohr"
) -> str:
    """
    Erstellt ein Rohr (Arch Pipe) entlang eines Linienzugs.

    Args:
        basewire: Liste von [X,Y,Z]-Punkten in METERN fuer den Rohrverlauf.
        outer_diameter: Aussendurchmesser mit Einheit (z.B. '100mm').
        wall_thickness: Wandstaerke mit Einheit (z.B. '5mm').
        name: Label des Rohrs.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_rohr(basewire, outer_diameter, wall_thickness, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_duct(
    basewire: list[list[float]],
    width: str = "300mm",
    height: str = "200mm",
    name: str = "Kanal"
) -> str:
    """
    Erstellt einen rechteckigen Luftkanal entlang eines Linienzugs (Part Sweep).

    Args:
        basewire: Liste von [X,Y,Z]-Punkten in METERN fuer den Kanalverlauf.
        width: Kanalbreite mit Einheit (z.B. '300mm').
        height: Kanalhoehe mit Einheit (z.B. '200mm').
        name: Label des Kanals.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_kanal(basewire, width, height, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_schedule(
    object_type: str = "Window",
    properties: str = "Label,Width,Height",
    name: str = "Ausgabe_Auszug"
) -> str:
    """
    Erstellt einen Mengenauszug / eine Objektliste (Arch Schedule).

    Args:
        object_type: Zu filternder Objekt-Typ (z.B. 'Window', 'Door', 'Wall').
        properties: Komma-getrennte Liste der anzuzeigenden Eigenschaften.
        name: Label des Auszugs.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_auszug(object_type, properties, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

@mcp.tool()
def create_2d_view(
    source_name: str,
    direction: str = "Front",
    name: str = "2D_Ansicht"
) -> str:
    """
    Erstellt eine TechDraw-2D-Ansicht eines Objekts.

    Args:
        source_name: Name oder Label des Quellobjekts.
        direction: Blickrichtung ('Front', 'Top', 'Right').
        name: Label der 2D-Ansicht.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_2d_ansicht(source_name, direction, name)
    except Exception as e:
        return f"Fehler: {str(e)}"

# --- MCP Tool Lücken (13 neue Tools) ---
@mcp.tool()
def get_object_info(object_name: str) -> str:
    """
    Gibt detaillierte Informationen zu einem FreeCAD-Objekt zurück:
    Typ, Label, Name, Bounding Box, Align, State, Volumen, Basislinie (für Wände).
    """
    try:
        bridge = get_bridge()
        return bridge.objekt_info_abrufen(object_name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def rename_object(object: str, new_label: str) -> str:
    """
    Benennt ein FreeCAD-Objekt um (setzt das Label).
    
    Args:
        object: Name oder aktuelles Label des Objekts.
        new_label: Neues Label für das Objekt.
    """
    try:
        bridge = get_bridge()
        return bridge.umbenennen_objekt(object, new_label)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def set_visibility(object: str, visible: bool) -> str:
    """
    Setzt die Sichtbarkeit eines Objekts in der 3D-Ansicht.
    Wichtig nach Boolean-Cut: Quellen verstecken (visible=false) damit das Cut-Ergebnis gültig bleibt.
    """
    try:
        bridge = get_bridge()
        return bridge.sichtbarkeit_setzen(object, visible)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def move_line(line: str, start: list[float], end: list[float]) -> str:
    """
    Verschiebt die Start/End-Punkte einer Draft-Linie.
    Nützlich für Baseline-Korrekturen bei Wänden.
    
    Args:
        line: Name oder Label der Draft-Linie.
        start: Neuer Startpunkt als [X, Y, Z] in METERN.
        end: Neuer Endpunkt als [X, Y, Z] in METERN.
    """
    try:
        bridge = get_bridge()
        return bridge.linie_verschieben(line, start, end)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def set_wall_alignment(wall: str, ref_at_outside: bool = True) -> str:
    """
    Verschiebt die Referenzlinie einer Wand an die Außenkante und setzt das Align.
    In einem Schritt: Baseline verschieben + korrektes Align setzen.
    
    Args:
        wall: Name oder Label der Wand.
        ref_at_outside: Wenn True, wird die Referenzlinie an die Außenseite gelegt.
    """
    try:
        bridge = get_bridge()
        return bridge.wand_ausrichtung_setzen(wall, ref_at_outside)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def boolean_cut_finalize(cut_result: str, new_label: str, container: str = "", hide_sources: bool = True) -> str:
    """
    Schließt einen Boolean-Cut ab: Ergebnis umbenennen, Quellen verstecken, in Container einsortieren.
    Erspart die manuellen Nachbearbeitungsschritte.
    
    Args:
        cut_result: Name des Cut-Objekts (z.B. "Schnitt").
        new_label: Neues Label für das Cut-Ergebnis.
        container: Optionaler Container (z.B. "Obergeschoss") für die Einsortierung.
        hide_sources: Quellobjekte verstecken (Standard: True).
    """
    try:
        bridge = get_bridge()
        return bridge.bool_cut_finalisieren(cut_result, new_label, container, hide_sources)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_opening(base_object: str, shape: str = "rectangle", position: list[float] = None, size: list[float] = None, name: str = "Oeffnung") -> str:
    """
    Erstellt eine Öffnung (Durchbruch) in einem Bauteil via Boolean-Cut.
    IFC-konforme Alternative zu manuellem Schneiden.
    
    Args:
        base_object: Name oder Label des Basis-Objekts (z.B. Decke, Wand).
        shape: Form der Öffnung (nur 'rectangle' unterstützt).
        position: Position als [X, Y, Z] in METERN.
        size: Größe als [Width, Height, Depth] in METERN.
        name: Label der Öffnung.
    """
    if position is None: position = [0, 0, 0]
    if size is None: size = [1, 1, 0.2]
    try:
        bridge = get_bridge()
        return bridge.erstelle_oeffnung(base_object, shape, position, size, name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def copy_to_floor(source_walls: list[str], target_floor: str, z_offset: float = 3.24, x_extension: float = 0.0) -> str:
    """
    Kopiert Wände von einem Geschoss auf ein anderes (z.B. EG -> OG).
    Die kopierten Wände werden auf die Zielgeschoss-Höhe verschoben und können verlängert werden.
    
    Args:
        source_walls: Liste von Wand-Namen/Labeln (z.B. ["KA_Nord_EG", "KA_Ost_EG"]).
        target_floor: Ziel-Container (z.B. "Obergeschoss").
        z_offset: Höhenversatz in METERN (z.B. 3.24 für 3,24m Geschosshöhe).
        x_extension: Verlängerung der Wand in METERN (0 = keine).
    """
    try:
        bridge = get_bridge()
        return bridge.kopiere_nach_geschoss(source_walls, target_floor, z_offset, x_extension)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_attika(roof_slab: str, height: float = 0.3, thickness: float = 0.365, offset: float = 0.0, name_prefix: str = "Attika") -> str:
    """
    Erzeugt Attika-Wände automatisch entlang des Slab-Perimeters.
    
    Args:
        roof_slab: Name oder Label der Dachplatte.
        height: Attikahöhe in METERN (z.B. 0.3 für 30cm).
        thickness: Attikadicke in METERN (z.B. 0.365 für 36,5cm).
        offset: Versatz vom Plattenrand in METERN (0 = bündig).
        name_prefix: Namenspräfix für die Attika-Wände.
    """
    try:
        bridge = get_bridge()
        return bridge.erstelle_attika(roof_slab, height, thickness, offset, name_prefix)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def create_slab_with_openings(length: str = "10m", width: str = "8m", height: str = "300mm",
                             placement_x: str = "0mm", placement_y: str = "0mm", placement_z: str = "0mm",
                             openings: list[dict] = None, name: str = "Geschossdecke") -> str:
    """
    Erstellt eine Geschossdecke mit rechteckigen Durchbrüchen in einem Schritt.
    'openings' ist eine Liste von Dicts: {"x": 1.4, "y": 0.9, "w": 3.7, "h": 1.2}
    wobei x,y relative Offsets von der Slab-Platzierung in METERN sind und w,h die Öffnungsgrösse in METERN.
    
    Args:
        length: Länge der Decke als String (z.B. '10m').
        width: Breite der Decke als String (z.B. '8m').
        height: Dicke der Decke als String (z.B. '300mm').
        placement_x: X-Platzierung.
        placement_y: Y-Platzierung.
        placement_z: Z-Platzierung (Oberkante).
        openings: Liste von Öffnungs-Dicts mit x,y,w,h in METERN.
        name: Label der Decke.
    """
    if openings is None: openings = []
    try:
        bridge = get_bridge()
        return bridge.erstelle_decke_mit_oeffnungen(length, width, height, placement_x, placement_y, placement_z, openings, name)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def align_walls_in_container(container: str, ref_at: str = "outside") -> str:
    """
    Richtet alle Wände in einem Container (Geschoss) einheitlich aus.
    Erkennt automatisch Nord/Süd/Ost/West und setzt korrektes Align.
    
    Args:
        container: Name des Containers (z.B. "Erdgeschoss").
        ref_at: "outside" für Außenausrichtung, "inside" für Innenausrichtung.
    """
    try:
        bridge = get_bridge()
        return bridge.waende_in_container_ausrichten(container, ref_at)
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def validate_model() -> str:
    """
    Validiert das gesamte FreeCAD-Modell:
    - Objekte mit State="Invalid" oder "Touched"
    - Überlappungen zwischen Objekten (Bounding Box)
    - Objekte ohne Container-Zuordnung
    """
    try:
        bridge = get_bridge()
        return bridge.modell_validieren()
    except Exception as e: return f"Fehler: {str(e)}"

@mcp.tool()
def validate_ifc_export() -> str:
    """
    Preflight-Check vor IFC-Export:
    Prüft IFC-Typ, Material und Container-Zugehörigkeit für alle Objekte.
    Gibt Warnungen für fehlende Angaben aus.
    """
    try:
        bridge = get_bridge()
        return bridge.validiere_ifc_export()
    except Exception as e: return f"Fehler: {str(e)}"

if __name__ == "__main__":
    # Startet den MCP-Server
    mcp.run()
