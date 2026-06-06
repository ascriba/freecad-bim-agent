# **FreeCAD Model Context Protocol (MCP) Server**

Dieses Repository enthält einen **Model Context Protocol (MCP)** Server, der eine nahtlose Brücke zwischen KI-Modellen (LLMs) und **FreeCAD** schlägt. Der Server basiert auf dem FastMCP-Framework und ermöglicht es KI-Assistenten, komplexe 3D-Modelle, parametrische Bauteile und vollständige **BIM-Strukturen (Building Information Modeling)** direkt in FreeCAD zu generieren, zu modifizieren, zu analysieren und visuell zu überprüfen.  
Der MCP-Server wurde speziell dafür entwickelt, nativ in **Coding-Agents** eingebunden zu werden, um autonome, KI-gesteuerte CAD- und BIM-Workflows zu ermöglichen. Die Funktion und Integration wurde erfolgreich mit [**OpenCode**](https://opencode.ai/) getestet.  
Die Kommunikation mit FreeCAD erfolgt über eine XML-RPC-Schnittstelle (FreeCAD-Bridge), die Befehle interpretiert und direkt in der FreeCAD-Python-Laufzeitumgebung ausführt.

## **Systemarchitektur**

Der Server fungiert als Übersetzer zwischen dem standardisierten MCP-Protokoll und der FreeCAD-API:

```mermaid
graph TD
    Agent[Coding-Agent <br> z.B. OpenCode]
    Server[mcp_server.py <br> FastMCP Server]
    Bridge[FreeCAD-Bridge <br> XML-RPC Server]
    FC[FreeCAD Core <br> Python Runtime]

    Agent -- "MCP JSON-RPC" --> Server
    Server -- "High-Level Tools <br> (z.B. create_wall)" --> Bridge
    Bridge -- "XML-RPC <br> (localhost:8000)" --> FC

    style Agent fill:#1f77b4,stroke:#115588,stroke-width:2px,color:#fff
    style Server fill:#2ca02c,stroke:#1e6b1e,stroke-width:2px,color:#fff
    style Bridge fill:#ff7f0e,stroke:#cc5200,stroke-width:2px,color:#fff
    style FC fill:#d62728,stroke:#991b1b,stroke-width:2px,color:#fff
   ```

## **Features & Funktionsumfang**

* **Optimiert für Coding-Agents:** Abgestimmte Tool-Strukturen für autonome Agenten wie OpenCode zur KI-gestützten Konstruktion.  
* **Parametrische CSG-Modellierung:** Erstellung von Grundkörpern (Würfel, Zylinder, Kugeln) mit nativer Einheitenunterstützung (mm, cm, m).  
* **Erweiterte BIM/Architektur-Tools:** Strukturierte Erstellung von IFC-konformen Entitäten wie Sites, Buildings, Floors, Walls, Slabs, Roofs und Stairs.  
* **Automatisierte Wand- & Fensterplatzierung:** Intelligente Ausrichtung von Wänden (Innen-/Außenkante) und passgenaues Einschneiden von Fenstern und Türen.  
* **Draft- & 2D-Zeichnungswerkzeuge:** Erstellung von Linien, Polylinien, Kreisen, Texten und Bemaßungen im 3D-Raum.  
* **Modellvalidierung & Qualitätskontrolle:** Preflight-Checks für ungültige Geometrien, Bounding-Box-Überlappungen und IFC-Konformität vor dem Export.  
* **Visuelles Feedback:** Direktes Rendern und Zurückgeben von 3D-Ansichten als Base64/PNG an das KI-Modell zur visuellen Verifikation.  
* **Das Ultimative Werkzeug (execute\_python):** Ermöglicht der KI das Ausführen von freiem Python-Code direkt in FreeCAD, um Lücken bei hochspezifischen Operationen zu schließen.

## **⚠️ WICHTIGER SICHERHEITSHINWEIS (execute\_python)**

Das Tool execute\_python ist extrem mächtig und dient als Fallback für Operationen, die nicht durch spezialisierte Tools abgedeckt sind. **Die Ausführung von beliebigem Python-Code birgt jedoch erhebliche Sicherheitsrisiken** (z. B. unbefugter Dateizugriff, Systembefehle oder Schadcode-Ausführung, falls das LLM unvorhersehbar agiert).

* **Sicherheitsrisiko:** execute\_python führt den vom Agenten generierten Code mit den vollen Rechten des lokalen Benutzers aus, unter dem FreeCAD läuft.  
* **Deaktivierung:** Wenn dieses Tool in deiner Umgebung nicht gewünscht oder als zu unsicher eingestuft wird, **muss es im Quellcode (mcp\_server.py) manuell deaktiviert oder auskommentiert werden:**

```Python  
# Auskommentieren zum Deaktivieren:  
# @mcp.tool()  
# def execute\_python(script: str) \-\> str:  
#     ...
```

## **Installation & Setup**

### **1\. Voraussetzungen**

* Python 3.10 oder höher  
* Eine laufende FreeCAD-Instanz mit installierter und aktiver **FreeCAD-Bridge** (XML-RPC-Server auf Port 8000).  
* Ein kompatibler MCP-Agent (getestet mit **OpenCode**).

### **2\. Abhängigkeiten installieren**

Installiere die benötigten Python-Pakete über pip:

Bash  
pip install mcp python-dotenv

### **3\. Umgebungsvariablen (.env)**

Erstelle eine .env-Datei im Hauptverzeichnis, falls du Standardkonfigurationen anpassen möchtest (wird über load\_dotenv() geladen).

### **4\. Server in OpenCode / Coding-Agents einbinden**

Füge den Server zu deiner MCP-Konfigurationsdatei des jeweiligen Agents hinzu:

```JSON  
{
  "mcp": {
    "FreeCAD": {
      "type": "local",
      "command": [
        "/pfad/zu/deinem/repository/.venv/bin/python3",
        "/pfad/zu/deinem/repository/mcp_server.py"
      ],
      "enabled": true
    }
  }
}
```

## **API- & Tool-Referenz**

Der Server registriert eine Vielzahl von Werkzeugen. Hier ist die strukturierte Übersicht aller verfügbaren MCP-Tools, aufgeteilt nach Kategorien:

### **1\. Basiskonstruktion & Transformationen (CSG)**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| create\_cube | length, width, height (Strings mit Einheit) | Erstellt einen parametrischen Würfel. |
| create\_cylinder | radius, height (Strings mit Einheit) | Erstellt einen Zylinder. |
| create\_sphere | radius (String mit Einheit) | Erstellt eine Kugel. |
| set\_position | name (Str), x, y, z (Floats) | Verschiebt ein Objekt an absolute Koordinaten (in Metern). |
| rotate\_object | name (Str), axis (X/Y/Z), angle (Float) | Dreht ein Objekt um die angegebene Achse in Grad. |
| clone\_object | source\_name, new\_name | Erstellt einen parametrischen Entwurfs-Klon (Draft Clone). |
| mirror\_object | source\_name, axis, origin\_x/y/z, new\_name | Spiegelt ein Objekt an einer definierten Achsenebene. |

### **2\. Boolesche Operationen & Modifikatoren**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| boolean\_union | obj\_a, obj\_b | Vereinigt zwei Objekte (Fusion). |
| boolean\_cut | base\_obj, tool\_obj | Subtrahiert tool\_obj von base\_obj (z.B. für Aussparungen). |
| boolean\_cut\_finalize | cut\_result, new\_label, container, hide\_sources | Finalisiert einen Cut: Benennt das Ergebnis um, versteckt Quellobjekte und sortiert es in ein Geschoss ein. |
| fillet | object\_name, radius, edge\_indices | Verrundet Kanten eines Objekts. |
| chamfer | object\_name, length, edge\_indices | Fast Kanten eines Objekts ab. |

### **3\. BIM & Architektur (Arch/BIM Workbench)**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| create\_site | name | Erstellt das Projektgelände (Arch Site). |
| create\_building | name | Erstellt eine Gebäubestruktur (Arch Building). |
| create\_floor | name | Erstellt ein Stockwerk / Geschoss (Arch Floor). |
| add\_to\_container | object\_name, container\_name | Ordnet ein Objekt hierarchisch zu (z.B. Wand in Stockwerk). |
| add\_to\_container\_batch | object\_names (List\[Str\]), container\_name | Mehrere Objekte auf einmal einem Container zuordnen. |
| create\_slab | length, width, height, name, placement\_x/y/z | Erstellt eine Boden- oder Deckenplatte. |
| create\_slab\_with\_openings | *Identisch mit Slab*, \+ openings (List\[Dict\]) | Erstellt eine Deckenplatte mit vordefinierten Durchbrüchen. |
| create\_wall | p1 \[X,Y,Z\], p2 \[X,Y,Z\], width, height, name | Erstellt eine gerade Wand zwischen zwei 3D-Punkten (in METERN). |
| join\_walls | walls (List\[Str\]) | Verbindet/Vereinigt mehrere Wände zu einem Objekt. |
| add\_to\_wall | wall\_name, component\_name | Fügt ein Fenster/eine Tür in eine Wand ein (Host-Beziehung). |
| align\_wall | wand\_bezeichnung, align, align\_to | Richtet die Wand relativ zur Basislinie aus (Left, Center, Right, inside, outside). |
| align\_walls\_in\_container | container, ref\_at ("outside"/"inside") | Richtet alle Wände eines Geschosses automatisiert nach Himmelsrichtung aus. |
| set\_wall\_alignment | wall, ref\_at\_outside (Bool) | Verschiebt die Referenzlinie an die Außenkante und passt das Align an. |
| create\_window | wall\_ident, distance\_from\_start, width, height, sill\_height, windowtype, name | Fügt ein Fenster/eine Tür in eine Wand ein. Schneidet die Wand automatisch auf. |
| create\_window\_sketch | wall\_ident, width, height, sill\_height, name | Erstellt ein benutzerdefiniertes Fenster basierend auf einer Skizze. |
| create\_roof | basewire (List\[List\[float\]\]), overhang, thickness, angle, name | Generiert ein Dach aus einem geschlossenen Polygon-Umriss. |
| create\_stairs | length, width, height, steps\_count, stringer\_thickness | Erstellt eine parametrische Treppenanlage. |
| create\_opening | base\_object, shape, position \[X,Y,Z\], size \[W,H,D\], name | Erzeugt einen Durchbruch in einem Bauteil via Boolean-Cut. |
| copy\_to\_floor | source\_walls (List\[Str\]), target\_floor, z\_offset, x\_extension | Kopiert Wände auf ein anderes Geschoss mit Höhenversatz. |
| create\_attika | roof\_slab, height, thickness, offset, name\_prefix | Generiert automatisch Attika-Umfassungswände entlang einer Dachplatte. |

### **4\. Achsen & Schnittebenen**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| create\_axis | x, y, z, direction (X/Y/Z), label | Erstellt eine einzelne Bauachse. |
| create\_axes | axes (List\[Dict\]) | Batch-Erstellung mehrerer Bauachsen in einem Aufruf. |
| create\_axis\_system | axes (List\[Str\]), name | Fasst mehrere Achsen zu einem Achssystem zusammen. |
| create\_section\_plane | x, y, z, direction, name | Erstellt eine Schnittebene für Grundrisse und Ansichten. |

### **5\. MEP (Technische Gebäudeausrüstung) & Spezialstrukturen**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| create\_structure | length, width, height, name, position\_x/y/z (opt.) | Erstellt Tragwerkselemente wie Balken oder Stützen. Optional mit Position in Metern. |
| create\_panel | length, width, thickness, name | Erstellt ein Arch-Paneel (Platte). |
| create\_curtain\_wall | basewire, panel\_width, panel\_height, name | Erstellt eine Glas-Vorhangfassade entlang eines Pfades. |
| create\_pipe | basewire, outer\_diameter, wall\_thickness, name | Erstellt ein Rohrleitungssystem entlang eines 3D-Pfades. |
| create\_duct | basewire, width, height, name | Erstellt einen rechteckigen Luftkanal via Sweep-Operation. |

### **6\. Draft (2D-Zeichnen & Dokumentation)**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| create\_point | x, y, z, name | Erstellt einen Referenzpunkt. |
| create\_line | p1, p2, name (Strings) | Erstellt eine Draft-Linie (Unterstützt Einheiten-Strings). |
| move\_line | line, start \[X,Y,Z\], end \[X,Y,Z\] | Verschiebt Start- und Endpunkte einer Linie. |
| create\_polyline | points (List), closed (Bool), name | Erstellt einen offenen oder geschlossenen Linienzug. |
| create\_rectangle | length, width, placement\_x/y/z | Erstellt ein flaches Rechteck. |
| create\_circle | radius, placement\_x/y/z | Erstellt einen Draft-Kreis. |
| create\_arc | center\_x/y/z, radius, start\_angle, end\_angle | Erstellt einen Kreisbogen. |
| create\_text | text, x, y, z, font\_size, name | Platziert einen Text im 3D-Raum. |
| create\_dimension | p1, p2, p3, name | Erstellt eine 2D/3D-Bemaßung zwischen zwei Punkten. |

### **7\. Daten, IFC-Management & Datenexport**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| set\_ifc\_data | object\_name, properties\_json | Weist Objekten benutzerdefinierte IFC-Eigenschaften (Psets) zu. |
| set\_material | object\_name, material\_name, color\_rgb | Weist ein Material und eine Visualisierungsfarbe (R,G,B) zu. |
| set\_material\_batch | object\_names (List\[Str\]), material\_name, color\_rgb | Weist mehreren Objekten gleichzeitig das gleiche Material zu. |
| get\_quantities | object\_name | Berechnet Flächen, Volumen und Massen eines Objekts. |
| export\_ifc | file\_path | Exportiert das gesamte Modell als standardisierte BIM-IFC-Datei. (Fallback via Arch.export). |
| analyze\_ifc | file\_path | Analysiert eine IFC-Datei extern und wirft Projektstatistiken aus. |
| create\_schedule | object\_type, properties, name | Erstellt eine automatisierte Bauteilliste (Arch Schedule). |
| create\_2d\_view | source\_name, direction, name | Erzeugt eine TechDraw-2D-Projektion (Grundriss/Schnitt). |
| export\_dxf / import\_dxf | file\_path | Ex-/Importiert CAD-Daten im DXF-Format. |
| export\_pdf / export\_svg | file\_path | Exportiert TechDraw-Pläne als Vektorgrafik oder PDF. |

### **8\. Administration, Validierung & Diagnose**

| Tool | Argumente | Beschreibung |
| :---- | :---- | :---- |
| list\_objects | *keine* | Gibt eine Liste aller Objekte mit Label → Name Mapping zurück. |
| get\_object\_info | object\_name | Liefert detaillierte Metadaten (Typ, BoundingBox, Status, Volumen, Basislinie) eines Objekts. |
| rename\_object | object, new\_label | Ändert das sichtbare Label eines Objekts. |
| set\_visibility | object, visible (Bool) | Schaltet die Sichtbarkeit im 3D-Viewports um. |
| delete\_object | name | Löscht ein Objekt permanent aus dem Dokument. |
| boolean\_cut\_finalize | cut\_result, new\_label, container, hide\_sources | Finalisiert einen Cut: Benennt um, versteckt Quellen, sortiert ein. |
| capture\_view | view\_type ("iso"/"top"/"front"/"right") | **Gibt ein mcp.Image-Objekt (PNG) zurück.** Macht einen Screenshot des aktuellen 3D-Viewports zur visuellen Kontrolle. |
| validate\_model | *keine* | Validiert das Modell auf Fehler ("Invalid"-Flags), Kollisionen, ungültige Bounding-Boxes und verwaiste Objekte. |
| validate\_ifc\_export | *keine* | Preflight-Prüfung für fehlende IFC-Daten/Materialien vor dem Export. |
| execute\_python | script (Python-Code) | **Sicherheitskritisch.** Führt nativen Python-Code im FreeCAD-Kontext aus. Kann bei Bedarf auskommentiert werden. |

## **Code-Architektur (mcp\_server.py)**

Der Code zeichnet sich durch ein robustes, defensives Design aus:

1. **FastMCP-Instanziierung:** Über mcp \= FastMCP("FreeCAD") wird der Server deklariert.  
2. **Fehlertolerante XML-RPC-Kommunikation:** Jedes Tool kapselt den Aufruf der Bridge in einem try-except-Block. Tritt in FreeCAD ein Fehler auf (z.B. Geometrie-Instabilität oder fehlende Objekte), wird dieser abgefangen und als lesbarer String an den Agenten zurückgegeben. Dadurch stürzt der MCP-Server nicht ab, und der Coding-Agent (z. B. OpenCode) kann autonom Fehlerkorrekturen einleiten.  
3. **Typsichere Bildkonvertierung:** Das Tool capture\_view empfängt Bilddaten als Base64-String von der FreeCAD-Bridge, dekodiert sie in native Bytes und nutzt die mcp.Image-Klasse von FastMCP, um dem Sprachmodell ein echtes visuelles Verständnis der Szene zur Verifikation zu ermöglichen. Unterstützt verschiedene Ansichtstypen (iso, top, front, right).  
4. **Batch-Operationen:** Tools wie add\_to\_container\_batch und set\_material\_batch reduzieren die Anzahl benötigter Tool-Calls bei Massenoperationen von 30+ auf 2–3 Aufrufe.  
5. **Retry-Mechanismus:** Der Bridge-Dispatch (`_dispatch`) wiederholt fehlgeschlagene Requests automatisch (2 Versuche mit 45s Timeout), um sporadische Timeout-Fehler zu vermeiden.

## **Lizenz**

Dieses Projekt ist unter der **MIT-Lizenz** lizenziert. Siehe LICENSE für Details.