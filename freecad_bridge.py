import xmlrpc.server
import threading
import socket
import FreeCAD as App
import Part
import time
import os
import base64
import io
import sys
import queue

# --- Konfiguration ---
PORT = 8000
HOST = "localhost"

# Globaler Thread-sicherer Request-Queue
request_queue = queue.Queue()
_timer_obj = None

def process_requests():
    """Arbeitet die Queue im Main Thread ab."""
    try:
        while not request_queue.empty():
            func, args, kwargs, result_holder = request_queue.get_nowait()
            try:
                res = func(*args, **kwargs)
                result_holder['result'] = res
            except Exception as e:
                result_holder['error'] = str(e)
            finally:
                result_holder['event'].set()
                request_queue.task_done()
    except queue.Empty:
        pass
    except Exception as e:
        try: App.Console.PrintMessage(f"Fehler im Request Processor: {str(e)}\n")
        except: pass

class RobustFreeCADBridge:
    def _dispatch(self, method, params):
        if not hasattr(self, method):
            raise Exception(f"Methode {method} nicht gefunden.")
        func = getattr(self, method)
        result_holder = {'event': threading.Event(), 'result': None, 'error': None}
        request_queue.put((func, params, {}, result_holder))
        if not result_holder['event'].wait(timeout=30.0):
            return "Fehler: Timeout im Main Thread."
        return result_holder['error'] if result_holder['error'] else result_holder['result']

    def hot_reload(self):
        """Ersetzt diese Instanz durch die neudefinierte Klasse aus der Datei."""
        try:
            bridge_path = "/home/arne/Programmierung/OpenCode/Freecad/freecad_bridge.py"
            exec(open(bridge_path).read(), globals())
            self.__class__ = RobustFreeCADBridge
            return "Bridge-Code neu geladen."
        except Exception as e:
            return f"Hot-Reload Fehler: {str(e)}"

    # def _parse_unit(self, val):
    #     if isinstance(val, (int, float)): return float(val)
    #     try:
    #         from FreeCAD import Units
    #         return float(Units.Quantity(str(val)).Value)
    #     except:
    #         return float(str(val).replace('mm','').replace('m','')) if str(val) else 0.0
    def _parse_unit(self, val):
        # Falls das LLM schon eine reine Zahl liefert, direkt als Float zurückgeben
        if isinstance(val, (int, float)):
            return float(val)
            
        # Falls es ein String ist, deine bestehende Parsing-Logik anwenden
        val_str = str(val).lower().strip()
        if "mm" in val_str:
            return float(val_str.replace("mm", ""))
        if "m" in val_str:
            return float(val_str.replace("m", "")) * 1000.0
            
        # Wenn kein Suffix da ist, nimm an es sind bereits mm (FreeCAD Standard)
        try:
            return float(val_str)
        except ValueError:
            return 0.0
    
    def _get_obj(self, name_or_label):
        if not App.ActiveDocument: return None
        obj = App.ActiveDocument.getObject(name_or_label)
        return obj if obj else next((o for o in App.ActiveDocument.Objects if o.Label == name_or_label), None)

    # def to_vector(self, p):
    #     try:
    #         if hasattr(p, "x"): return p
    #         if isinstance(p, (list, tuple)):
    #             return App.Vector(float(p[0]), float(p[1]), float(p[2]) if len(p)>2 else 0.0)
    #         if isinstance(p, dict):
    #             return App.Vector(self._parse_unit(p.get("x",0)), self._parse_unit(p.get("y",0)), self._parse_unit(p.get("z",0)))
    #         if isinstance(p, str):
    #             parts = p.strip("[]() ").split(",")
    #             return App.Vector(float(parts[0]), float(parts[1]), float(parts[2]) if len(parts)>2 else 0.0)
    #     except: pass
    #     raise ValueError(f"Vektor-Fehler: {p}")
    def to_vector(self, p):
        try:
            if hasattr(p, "x"): 
                return p
                
            # 1. Wenn es eine Liste oder ein Tuple vom LLM ist (z.B. [0.0, 5.0, 0.0])
            if isinstance(p, (list, tuple)):
                # WICHTIG: Wenn der Wert ein roher Float/Int ist, behandeln wir ihn als Meter (mal 1000)
                # Wenn es ein String ist (z.B. "500mm"), regelt das _parse_unit.
                x = p[0] * 1000.0 if isinstance(p[0], (int, float)) else self._parse_unit(p[0])
                y = p[1] * 1000.0 if isinstance(p[1], (int, float)) else self._parse_unit(p[1])
                z = p[2] * 1000.0 if isinstance(p[2], (int, float)) else self._parse_unit(p[2]) if len(p) > 2 else 0.0
                return App.Vector(x, y, z)
                
            if isinstance(p, dict):
                return App.Vector(
                    self._parse_unit(p.get("x", 0)), 
                    self._parse_unit(p.get("y", 0)), 
                    self._parse_unit(p.get("z", 0))
                )
                
            # 2. Wenn es ein String ist
            if isinstance(p, str):
                parts = p.strip("[]() ").split(",")
                return App.Vector(
                    self._parse_unit(parts[0]), 
                    self._parse_unit(parts[1]), 
                    self._parse_unit(parts[2]) if len(parts) > 2 else 0.0
                )
        except Exception as e:
            raise ValueError(f"Vektor-Fehler bei der Konvertierung von {p}. Details: {str(e)}")
            
        raise ValueError(f"Vektor-Fehler: Ungültiges Format {p}")

    # --- Diagnose & Ansicht ---
    def capture_view(self, filename="freecad_view.png"):
        try:
            import FreeCADGui
            if not App.ActiveDocument: return "Fehler: Kein Dokument."
            view = FreeCADGui.ActiveDocument.ActiveView
            if not view: return "Fehler: Keine Ansicht."
            
            # Absoluter Pfad im Arbeitsverzeichnis
            full_path = os.path.abspath(filename)
            view.fitAll()
            view.saveImage(full_path, 1280, 720, "White")
            
            if os.path.exists(full_path):
                with open(full_path, "rb") as f:
                    return base64.b64encode(f.read()).decode('utf-8')
            return "Fehler: Bild wurde nicht gespeichert."
        except Exception as e: return f"Fehler: {str(e)}"

    def liste_objekte(self):
        try:
            if not App.ActiveDocument: return "Kein Dokument."
            res = []
            for o in App.ActiveDocument.Objects:
                info = f"{o.Label} ({o.Name}) [{o.TypeId}]"
                # IFC Info
                if hasattr(o, "IfcRole"):
                    info += f" (IFC: {o.IfcRole})"
                elif hasattr(o, "IfcType") and o.IfcType:
                    info += f" (IFC: {o.IfcType})"
                # Material Info
                if hasattr(o, "Material") and o.Material:
                    m_label = getattr(o.Material, "Label", str(o.Material))
                    info += f" (Material: {m_label})"
                res.append(info)
            return "Objekte:\n" + "\n".join(res)
        except Exception as e: return f"Fehler: {str(e)}"

    def delete_object(self, name):
        try:
            obj = self._get_obj(name)
            if not obj: return "Nicht gefunden."
            App.ActiveDocument.removeObject(obj.Name)
            App.ActiveDocument.recompute()
            return f"Gelöscht: {name}"
        except Exception as e: return f"Fehler: {str(e)}"

    # --- Geometrie ---
    def erstelle_wuerfel(self, l=10, w=10, h=10):
        try:
            doc = App.ActiveDocument or App.newDocument("MCP")
            box = doc.addObject("Part::Box", "Wuerfel")
            box.Length, box.Width, box.Height = self._parse_unit(l), self._parse_unit(w), self._parse_unit(h)
            doc.recompute()
            return f"Erfolg: {box.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_kugel(self, radius=5.0):
        try:
            doc = App.ActiveDocument or App.newDocument("MCP")
            s = doc.addObject("Part::Sphere", "Kugel")
            s.Radius = self._parse_unit(radius)
            doc.recompute()
            return f"Erfolg: {s.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_zylinder(self, radius=5.0, height=10.0):
        try:
            doc = App.ActiveDocument or App.newDocument("MCP")
            cyl = doc.addObject("Part::Cylinder", "Zylinder")
            cyl.Radius = self._parse_unit(radius)
            cyl.Height = self._parse_unit(height)
            doc.recompute()
            return f"Erfolg: {cyl.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def setze_position(self, name, x, y, z):
        try:
            obj = self._get_obj(name)
            if not obj: return "Nicht gefunden."
            # MCP-Tool übergibt Meter (float) → in mm konvertieren
            x_mm = x * 1000.0 if isinstance(x, (int, float)) else self._parse_unit(x)
            y_mm = y * 1000.0 if isinstance(y, (int, float)) else self._parse_unit(y)
            z_mm = z * 1000.0 if isinstance(z, (int, float)) else self._parse_unit(z)
            obj.Placement.Base = App.Vector(x_mm, y_mm, z_mm)
            App.ActiveDocument.recompute()
            return "Position gesetzt."
        except Exception as e: return f"Fehler: {str(e)}"

    def drehe_objekt(self, name, axis, angle):
        try:
            obj = self._get_obj(name)
            if not obj: return "Nicht gefunden."
            axis_v = App.Vector(1,0,0) if axis.upper()=='X' else App.Vector(0,1,0) if axis.upper()=='Y' else App.Vector(0,0,1)
            obj.Placement.Rotation = App.Rotation(axis_v, float(angle))
            App.ActiveDocument.recompute()
            return f"Gedreht: {name}"
        except Exception as e: return f"Fehler: {str(e)}"

    def bool_union(self, obj_a, obj_b):
        try:
            doc = App.ActiveDocument
            a, b = self._get_obj(obj_a), self._get_obj(obj_b)
            if not a or not b: return "Objekt nicht gefunden."
            fusion = doc.addObject("Part::MultiFuse", "Fusion")
            fusion.Shapes = [a, b]
            if hasattr(a, "ViewObject"): a.ViewObject.Visibility = False
            if hasattr(b, "ViewObject"): b.ViewObject.Visibility = False
            doc.recompute()
            return f"Fusion: {fusion.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def bool_cut(self, base_obj, tool_obj):
        try:
            doc = App.ActiveDocument
            b, t = self._get_obj(base_obj), self._get_obj(tool_obj)
            if not b or not t: return "Objekt nicht gefunden."
            cut = doc.addObject("Part::Cut", "Schnitt")
            cut.Base, cut.Tool = b, t
            if hasattr(b, "ViewObject"): b.ViewObject.Visibility = False
            if hasattr(t, "ViewObject"): t.ViewObject.Visibility = False
            doc.recompute()
            return f"Schnitt: {cut.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    # --- BIM ---
    def erstelle_site(self, name="Grundstueck"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            site = Arch.makeSite(); site.Label = name
            doc.recompute()
            return f"Site: {site.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_gebaeude(self, name="Gebaeude"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            b = Arch.makeBuilding(); b.Label = name
            doc.recompute()
            return f"Building: {b.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_stockwerk(self, name="Stockwerk"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            f = Arch.makeFloor(); f.Label = name
            doc.recompute()
            return f"Floor: {f.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_bodenplatte(self, length="10m", width="8m", height="200mm", name="Bodenplatte",
                          placement_x="0mm", placement_y="0mm", placement_z="0mm"):
        try:
            import Arch, Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            rect = Draft.makeRectangle(self._parse_unit(length), self._parse_unit(width))
            if hasattr(rect, "ViewObject"): rect.ViewObject.Visibility = False
            slab = Arch.makeStructure(rect)
            slab.IfcType = "Slab"
            h_val = self._parse_unit(height)
            slab.Height = h_val
            slab.touch()
            slab.Normal = (0, 0, -1)
            slab.Label = name
            slab.Placement.Base = App.Vector(self._parse_unit(placement_x), self._parse_unit(placement_y), self._parse_unit(placement_z))
            doc.recompute()
            # Sicherstellen, dass Height korrekt übernommen wurde
            if float(slab.Height) != h_val:
                slab.Height = str(h_val)
                slab.touch()
                doc.recompute()
            return f"Slab: {slab.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_wand_aus_punkten(self, p1, p2, width="300mm", height="2500mm", name="Wand"):
        try:
            import Arch
            import Draft
            
            doc = App.ActiveDocument or App.newDocument("BIM")
            
            # 1. Deine vorhandene Vektor-Konvertierung nutzen
            v1 = self.to_vector(p1)
            v2 = self.to_vector(p2)
            
            # 2. Die echte Draft-Linie im Hintergrund erstellen
            # (Nutzt die korrekte FreeCAD-Syntax Draft.make_line)
            base_line = Draft.make_line(v1, v2)
            
            # Basislinie unsichtbar schalten, damit nur die Wand zu sehen ist
            if hasattr(base_line, "ViewObject"): 
                base_line.ViewObject.Visibility = False
            
            # 3. Wand aus der Linie erzeugen
            wall = Arch.makeWall(base_line)
            
            # 4. Dimensionen direkt der Wand zuweisen
            wall.Width = self._parse_unit(width)
            wall.Height = self._parse_unit(height)
            wall.Label = name
            wall.IfcType = "Wall"
            
            doc.recompute()
            return f"Erfolgreich: Wand '{wall.Label}' wurde von {p1} nach {p2} erstellt."
            
        except Exception as e:
            return f"Fehler in Bridge: {str(e)}"
    
    def ausrichten_wand(self, wand_bezeichnung, align="Left", align_to=None):
        try:
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."

            wall = None
            for obj in doc.Objects:
                if obj.Label == wand_bezeichnung:
                    wall = obj
                    break

            if wall is None:
                return f"Fehler: Wand '{wand_bezeichnung}' nicht gefunden."

            # align_to überschreibt align wenn gesetzt
            if align_to is not None:
                align_lookup = {
                    "left": "Left",
                    "center": "Center",
                    "right": "Right",
                }
                if align_to.lower() in align_lookup:
                    align = align_lookup[align_to.lower()]
                elif align_to.lower() in ("inside", "outside"):
                    # Richtung der Wand ermitteln
                    if hasattr(wall, "Base") and wall.Base:
                        v_start = wall.Base.Shape.Vertexes[0].Point
                        v_ende = wall.Base.Shape.Vertexes[-1].Point
                        w_dir = (v_ende - v_start).normalize()
                        # Linke Normale: 90° im Uhrzeigersinn von Wandrichtung
                        linke_normale = App.Vector(0, 0, 1).cross(w_dir).normalize()
                    else:
                        linke_normale = App.Vector(0, -1, 0)
                    # "Left" = Wand geht zur linken Seite der Richtung
                    # Für "outside" nehmen wir "Left", für "inside" "Right"
                    if align_to.lower() == "outside":
                        align = "Left"
                    else:
                        align = "Right"
                else:
                    return f"Fehler: Unbekannter align_to-Wert '{align_to}'. Erlaubt: left, center, right, inside, outside."

            wall.Align = align
            doc.recompute()
            return f"Erfolgreich: Wand '{wand_bezeichnung}' auf '{align}' ausgerichtet."

        except Exception as e:
            return f"Fehler in Bridge im tool Wand_ausrichten: {str(e)}"
        
    def vereinigen_Wand(self, wand_liste):
        try:
            import Arch
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."

            # 1. Wand anhand des Labels finden
            walls = []
            for obj in doc.Objects:
                if obj.Label in wand_liste:
                    walls.append(obj)
                                
            if len(walls) <= 1:
                return f"Fehler: Wand '{wand_liste}' nicht gefunden. {walls}"
            elif len(walls) == 2:
                Arch.addComponents(walls[0], walls[-1])
            else:
                Arch.addComponents(walls[:-1], walls[-1])
                  
            doc.recompute()
            return f"Erfolgreich: Wand '{wand_liste}' vereinigt."
        
        except Exception as e:
            return f"Fehler in Bridge in tool vereinigen_Wand: {str(e)}"
        


    def fuege_fenster_ein(self, wand_bezeichnung, distance_from_start="1.5m", width="900mm", height="2000mm", sill_height="0mm", windowtype="Simple door", name="Fenster"):
        try:
            import Arch

            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."

            wall = None
            for obj in doc.Objects:
                if obj.Label == wand_bezeichnung:
                    wall = obj
                    break

            if not wall:
                wall = doc.getObject(wand_bezeichnung)

            if not wall:
                return f"Fehler: Wand '{wand_bezeichnung}' nicht gefunden."

            dist = self._parse_unit(distance_from_start)
            w_val = self._parse_unit(width)
            h_val = self._parse_unit(height)
            s_val = self._parse_unit(sill_height)

            if hasattr(wall, "Base") and wall.Base:
                wand_start = wall.Base.Shape.Vertexes[0].Point
                wand_ende = wall.Base.Shape.Vertexes[-1].Point
                wand_vektor = (wand_ende - wand_start).normalize()
            else:
                wand_start = App.Vector(0, 0, 0)
                wand_vektor = App.Vector(1, 0, 0)

            vektor_oben = App.Vector(0, 0, 1)
            wand_normale = wand_vektor.cross(vektor_oben).normalize()

            m = App.Matrix()
            m.A11 = wand_vektor.x;   m.A21 = wand_vektor.y;   m.A31 = wand_vektor.z
            m.A12 = vektor_oben.x;   m.A22 = vektor_oben.y;   m.A32 = vektor_oben.z
            m.A13 = wand_normale.x;  m.A23 = wand_normale.y;  m.A33 = wand_normale.z
            rot = App.Rotation(m)

            doors = ["Simple door", "Glass door"]
            clean_preset = "Fixed" if "fixed" in windowtype.lower() else "Simple door"
            window = Arch.makeWindowPreset(
                clean_preset,
                width=w_val, height=h_val,
                h1=50.0, h2=50.0, h3=50.0, w1=100.0, w2=50.0, o1=0.0, o2=50.0
            )

            if windowtype in doors:
                exakte_position = wand_start + (wand_vektor * dist) + (vektor_oben * (0))
            else:
                exakte_position = wand_start + (wand_vektor * dist) + (vektor_oben * s_val)
            window.Placement = App.Placement(exakte_position, rot)

            window.Hosts = [wall]
            window.Label = name

            doc.recompute()
            return f"Erfolgreich: Fenster '{window.Label}' in Wand '{wall.Label}' eingebettet."

        except Exception as e:
            return f"Fehler in Bridge beim Platzieren: {str(e)}"

    def erstelle_struktur(self, length="100mm", width="20mm", height="2000mm", name="Balken"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            base = doc.addObject("Part::Box", "StructBase")
            base.Length, base.Width, base.Height = self._parse_unit(length), self._parse_unit(width), self._parse_unit(height)
            if hasattr(base, "ViewObject"): base.ViewObject.Visibility = False
            struct = Arch.makeStructure(base); struct.Label = name
            doc.recompute()
            return f"Struktur: {struct.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def fuege_zu_wand_hinzu(self, wand_n, komp_n):
        try:
            import Arch
            w, k = self._get_obj(wand_n), self._get_obj(komp_n)
            if not w or not k: return "Objekt nicht gefunden."
            Arch.addComponents(k, w)
            App.ActiveDocument.recompute()
            return "Komponente in Wand eingesetzt."
        except Exception as e: return f"Fehler: {str(e)}"

    def fuege_zu_container_hinzu(self, obj_n, cont_n):
        try:
            o, c = self._get_obj(obj_n), self._get_obj(cont_n)
            if not o or not c: return "Objekt nicht gefunden."
            if hasattr(c, "addObject"): c.addObject(o)
            elif hasattr(c, "Group"):
                g = list(c.Group); g.append(o); c.Group = g
            App.ActiveDocument.recompute()
            return f"{o.Label} -> {c.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    # --- BIM Erweiterung Phase 1 ---
    def erstelle_dach(self, punkte, ueberstand="500mm", dicke="100mm", winkel=30.0, name="Dach"):
        try:
            import Arch, Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            punkte_vektoren = [self.to_vector(p) for p in punkte]
            draht = Draft.makeWire(punkte_vektoren, closed=True)
            if hasattr(draht, "ViewObject"):
                draht.ViewObject.Visibility = False
            doc.recompute()
            dach = Arch.makeRoof(draht)
            dach.Label = name
            if hasattr(dach, "Thickness"):
                dach.Thickness = [self._parse_unit(dicke)]
            if hasattr(dach, "Overhang"):
                dach.Overhang = [self._parse_unit(ueberstand)]
            if hasattr(dach, "Angles"):
                anzahl_flaechen = len(dach.Angles)
                dach.Angles = [winkel] * anzahl_flaechen if anzahl_flaechen > 0 else [winkel]
            doc.recompute()
            return f"Dach: {dach.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_treppe(self, laenge="1000mm", breite="1200mm", hoehe="2500mm", anzahl_stufen=14, wange_dicke="50mm", name="Treppe"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            treppe = Arch.makeStairs(
                length=self._parse_unit(laenge),
                width=self._parse_unit(breite),
                height=self._parse_unit(hoehe),
                steps=anzahl_stufen
            )
            treppe.Label = name
            if hasattr(treppe, "StringerThickness"):
                treppe.StringerThickness = self._parse_unit(wange_dicke)
            doc.recompute()
            return f"Treppe: {treppe.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_achse(self, x="0mm", y="0mm", z="0mm", richtung="Z", label="1"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            achse = Arch.makeAxis(1, 10000)
            achse.Label = f"Achse_{label}"
            achse.Placement.Base = App.Vector(self._parse_unit(x), self._parse_unit(y), self._parse_unit(z))
            if richtung.upper() == "X":
                achse.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), -90)
            elif richtung.upper() == "Y":
                achse.Placement.Rotation = App.Rotation(App.Vector(0, 0, 1), 0)
            else:
                achse.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
            if hasattr(achse, "Labels"):
                achse.Labels = [label]
            doc.recompute()
            return f"Achse: {achse.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_achsensystem(self, achsen_liste, name="Achsensystem"):
        try:
            import Arch
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            achsen = []
            for label in achsen_liste:
                a = self._get_obj(f"Achse_{label}")
                if a:
                    achsen.append(a)
            if not achsen:
                return "Fehler: Keine Achsen gefunden."
            system = Arch.makeAxisSystem(achsen)
            system.Label = name
            doc.recompute()
            return f"Achsensystem: {system.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_schnittebene(self, x="0mm", y="0mm", z="1500mm", richtung="Z", name="Schnitt_A"):
        try:
            import Arch
            doc = App.ActiveDocument or App.newDocument("BIM")
            objs = doc.Objects
            section = Arch.makeSectionPlane(objs)
            section.Label = name
            pos = App.Vector(self._parse_unit(x), self._parse_unit(y), self._parse_unit(z))
            section.Placement.Base = pos
            if richtung.upper() == "X":
                section.Placement.Rotation = App.Rotation(App.Vector(0, 1, 0), 90)
            elif richtung.upper() == "Y":
                section.Placement.Rotation = App.Rotation(App.Vector(1, 0, 0), 90)
            doc.recompute()
            return f"Schnittebene: {section.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def klone_objekt(self, quell_name, neuer_name="Klon"):
        try:
            import Draft
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            src = self._get_obj(quell_name)
            if not src:
                return f"Fehler: '{quell_name}' nicht gefunden."
            clone = Draft.clone(src)
            clone.Label = neuer_name
            doc.recompute()
            return f"Klon: {clone.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def spiegele_objekt(self, quell_name, achse="X", x=0.0, y=0.0, z=0.0, neuer_name="Gespiegelt"):
        try:
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            src = self._get_obj(quell_name)
            if not src:
                return f"Fehler: '{quell_name}' nicht gefunden."
            if achse.upper() == "X":
                dir_vec = App.Vector(1, 0, 0)
            elif achse.upper() == "Y":
                dir_vec = App.Vector(0, 1, 0)
            else:
                dir_vec = App.Vector(0, 0, 1)
            mirrored = doc.addObject("Part::Mirroring", "Gespiegelt")
            mirrored.Source = src
            mirrored.Normal = dir_vec
            mirrored.Base = App.Vector(x, y, z)
            mirrored.Label = neuer_name
            doc.recompute()
            return f"Gespiegelt: {mirrored.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    # --- BIM Erweiterung Phase 2 ---
    def erstelle_text(self, text, x="0mm", y="0mm", z="0mm", groesse="100mm", name="Text"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            pos = App.Vector(self._parse_unit(x), self._parse_unit(y), self._parse_unit(z))
            txt = Draft.makeText(text, point=pos)
            txt.Label = name
            if hasattr(txt, "FontSize"):
                txt.FontSize = self._parse_unit(groesse)
            doc.recompute()
            return f"Text: {txt.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_bemassung(self, p1, p2, p3, name="Mass"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            v1, v2, v3 = self.to_vector(p1), self.to_vector(p2), self.to_vector(p3)
            dim = Draft.makeDimension(v1, v2, v3)
            dim.Label = name
            doc.recompute()
            return f"Mass: {dim.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_verrundung(self, obj_name, radius="5mm", kanten_indizes=None, name="Verrundet"):
        if kanten_indizes is None:
            kanten_indizes = []
        try:
            import Part
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            src = self._get_obj(obj_name)
            if not src:
                return f"Fehler: '{obj_name}' nicht gefunden."
            r = self._parse_unit(radius)
            if kanten_indizes:
                kanten = [src.Shape.Edges[i] for i in kanten_indizes]
                neue_form = src.Shape.makeFillet(r, kanten)
            else:
                neue_form = src.Shape.makeFillet(r, src.Shape.Edges)
            result = doc.addObject("Part::Feature", "Verrundet")
            result.Shape = neue_form
            result.Label = name
            if hasattr(src, "ViewObject"):
                src.ViewObject.Visibility = False
            doc.recompute()
            return f"Verrundet: {result.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_fase(self, obj_name, laenge="5mm", kanten_indizes=None, name="Gefast"):
        try:
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            src = self._get_obj(obj_name)
            if not src:
                return f"Fehler: '{obj_name}' nicht gefunden."
            l = self._parse_unit(laenge)
            if kanten_indizes:
                kanten = [src.Shape.Edges[i] for i in kanten_indizes]
                neue_form = src.Shape.makeChamfer(l, kanten)
            else:
                neue_form = src.Shape.makeChamfer(l, src.Shape.Edges)
            result = doc.addObject("Part::Feature", "Gefast")
            result.Shape = neue_form
            result.Label = name
            if hasattr(src, "ViewObject"):
                src.ViewObject.Visibility = False
            doc.recompute()
            return f"Gefast: {result.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_paneel(self, laenge="1000mm", breite="500mm", dicke="50mm", name="Paneel"):
        try:
            import Arch, Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            rect = Draft.makeRectangle(self._parse_unit(laenge), self._parse_unit(breite))
            if hasattr(rect, "ViewObject"):
                rect.ViewObject.Visibility = False
            panel = Arch.makePanel(rect, thickness=self._parse_unit(dicke))
            panel.Label = name
            doc.recompute()
            return f"Paneel: {panel.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def importiere_dxf(self, dateipfad):
        try:
            import importDXF
            if not os.path.isabs(dateipfad):
                dateipfad = os.path.abspath(dateipfad)
            if not os.path.exists(dateipfad):
                return f"Fehler: Datei nicht gefunden: {dateipfad}"
            doc = App.ActiveDocument or App.newDocument("BIM")
            importDXF.importDXF(dateipfad, doc)
            doc.recompute()
            return f"DXF importiert: {dateipfad}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def exportiere_dxf(self, dateipfad="export.dxf"):
        try:
            import importDXF
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            if not os.path.isabs(dateipfad):
                dateipfad = os.path.abspath(dateipfad)
            importDXF.export(doc.Objects, dateipfad)
            return f"DXF exportiert: {dateipfad}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def exportiere_pdf(self, dateipfad="plan.pdf"):
        try:
            import FreeCADGui
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            gui_doc = FreeCADGui.ActiveDocument
            if not gui_doc:
                return "Fehler: Kein GUI-Dokument (keine Seiten vorhanden?)."
            if not os.path.isabs(dateipfad):
                dateipfad = os.path.abspath(dateipfad)
            gui_doc.exportPage(dateipfad)
            return f"PDF exportiert: {dateipfad}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def exportiere_svg(self, dateipfad="export.svg"):
        try:
            import importSVG
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            if not os.path.isabs(dateipfad):
                dateipfad = os.path.abspath(dateipfad)
            importSVG.export(doc.Objects, dateipfad)
            return f"SVG exportiert: {dateipfad}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    # --- BIM Erweiterung Phase 3 ---
    def erstelle_fenster_skizze(self, wand_bezeichnung, breite="900mm", hoehe="1200mm", brüstung="900mm", name="Fenster_Skizze"):
        try:
            import Arch, Draft
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            wall = self._get_obj(wand_bezeichnung)
            if not wall:
                return f"Fehler: Wand '{wand_bezeichnung}' nicht gefunden."
            w = self._parse_unit(breite)
            h = self._parse_unit(hoehe)
            s = self._parse_unit(brüstung)
            rect = Draft.makeRectangle(w, h)
            if hasattr(wall, "Base") and wall.Base:
                wand_start = wall.Base.Shape.Vertexes[0].Point
                wand_ende = wall.Base.Shape.Vertexes[-1].Point
                wand_vektor = (wand_ende - wand_start).normalize()
            else:
                wand_start = wall.Shape.BoundBox.Center
                wand_vektor = App.Vector(1, 0, 0)
            pos = wand_start + (wand_vektor * 1000) + App.Vector(0, 0, s)
            rect.Placement.Base = pos
            window = Arch.makeWindow(rect)
            window.Label = name
            window.Hosts = [wall]
            if hasattr(rect, "ViewObject"):
                rect.ViewObject.Visibility = False
            doc.recompute()
            return f"Fenster (Skizze): {window.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_vorhangfassade(self, wire_punkte, panel_breite="1000mm", panel_hoehe="2500mm", name="Vorhangfassade"):
        try:
            import Arch, Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            vektoren = [self.to_vector(p) for p in wire_punkte]
            wire = Draft.makeWire(vektoren, closed=False)
            if hasattr(wire, "ViewObject"):
                wire.ViewObject.Visibility = False
            fassade = Arch.makeCurtainWall(wire)
            fassade.Label = name
            # PanelWidth/PanelHeight als persistente Properties
            pb = self._parse_unit(panel_breite)
            ph = self._parse_unit(panel_hoehe)
            if not hasattr(fassade, "PanelWidth"):
                fassade.addProperty("App::PropertyLength", "PanelWidth", "Arch", "Panel width")
            fassade.PanelWidth = pb
            if not hasattr(fassade, "PanelHeight"):
                fassade.addProperty("App::PropertyLength", "PanelHeight", "Arch", "Panel height")
            fassade.PanelHeight = ph
            doc.recompute()
            return f"Vorhangfassade: {fassade.Label} ({fassade.Name})"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_rohr(self, wire_punkte, aussen_durchmesser="100mm", wandstaerke="5mm", name="Rohr"):
        try:
            import Arch, Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            vektoren = [self.to_vector(p) for p in wire_punkte]
            wire = Draft.makeWire(vektoren, closed=False)
            if hasattr(wire, "ViewObject"):
                wire.ViewObject.Visibility = False
            rohr = Arch.makePipe(wire, diameter=self._parse_unit(aussen_durchmesser))
            rohr.Label = name
            doc.recompute()
            return f"Rohr: {rohr.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_kanal(self, wire_punkte, breite="300mm", hoehe="200mm", name="Kanal"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            vektoren = [self.to_vector(p) for p in wire_punkte]
            if len(vektoren) < 2:
                return "Fehler: Mindestens 2 Punkte für den Pfad benötigt."
            b = self._parse_unit(breite)
            h = self._parse_unit(hoehe)
            pfad = Draft.makeWire(vektoren, closed=False)
            if hasattr(pfad, "ViewObject"):
                pfad.ViewObject.Visibility = False
            profil = Draft.makeRectangle(b, h)
            profil.Placement.Base = vektoren[0]
            if hasattr(profil, "ViewObject"):
                profil.ViewObject.Visibility = False
            doc.recompute()
            sweep = doc.addObject("Part::Sweep", "Kanal")
            sweep.Sections = [profil]
            sweep.Spine = pfad
            sweep.Solid = True
            sweep.Frenet = True
            sweep.Label = name
            doc.recompute()
            return f"Kanal: {sweep.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_auszug(self, obj_typ="Window", eigenschaften="Label,Width,Height", name="Auszug"):
        try:
            import Arch
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            schedule = Arch.makeSchedule()
            schedule.Label = name
            if hasattr(schedule, "Filter"):
                schedule.Filter = obj_typ
            if hasattr(schedule, "DetailedResults"):
                schedule.DetailedResults = True
            doc.recompute()
            # Werte direkt auslesen
            zeilen = [f"Auszug: {obj_typ}"]
            props_list = [p.strip() for p in eigenschaften.split(",")]
            treffer = 0
            for o in doc.Objects:
                if (obj_typ.lower() in o.TypeId.lower() or 
                    (hasattr(o, "IfcType") and obj_typ.lower() in str(o.IfcType).lower()) or
                    obj_typ.lower() in o.Label.lower()):
                    treffer += 1
                    werte = [o.Label]
                    for p in props_list:
                        if hasattr(o, p):
                            val = getattr(o, p)
                            werte.append(f"{p}={val}")
                    zeilen.append("  " + ", ".join(werte))
            if treffer == 0:
                zeilen.append("  (keine Objekte gefunden)")
            return "\n".join(zeilen)
        except Exception as e:
            return f"Fehler: {str(e)}"

    def erstelle_2d_ansicht(self, quell_name, richtung="Front", name="2D_Ansicht"):
        try:
            import FreeCADGui as Gui
            import TechDraw
            doc = App.ActiveDocument
            if not doc:
                return "Fehler: Kein aktives Dokument."
            src = self._get_obj(quell_name)
            if not src:
                return f"Fehler: '{quell_name}' nicht gefunden."
            # Seite erzeugen falls keine existiert
            page = None
            for o in doc.Objects:
                if "DrawPage" in o.TypeId:
                    page = o
                    break
            if not page:
                page = doc.addObject("TechDraw::DrawPage", "Seite")
                template = doc.addObject("TechDraw::DrawSVGTemplate", "Vorlage")
                page.Template = template
            # Ansicht erzeugen
            view = doc.addObject("TechDraw::DrawViewPart", name)
            view.Source = [src]
            view.Direction = App.Vector(0, 0, 1)
            if richtung.lower() == "front":
                view.Direction = App.Vector(0, -1, 0)
            elif richtung.lower() == "top":
                view.Direction = App.Vector(0, 0, -1)
            elif richtung.lower() == "right":
                view.Direction = App.Vector(1, 0, 0)
            page.addView(view)
            doc.recompute()
            return f"2D-Ansicht: {view.Label}"
        except Exception as e:
            return f"Fehler: {str(e)}"

    # --- Draft ---
    def erstelle_punkt(self, x="0mm", y="0mm", z="0mm", name="Punkt"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            point = Draft.makePoint(self._parse_unit(x), self._parse_unit(y), self._parse_unit(z))
            point.Label = name
            doc.recompute()
            return f"Punkt: {point.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_draft_line(self, p1, p2, name="Linie"):
        try:
            import Draft
            v1, v2 = self.to_vector(p1), self.to_vector(p2)
            line = Draft.make_line(v1, v2)
            line.Label = name; App.ActiveDocument.recompute()
            return f"Draft-Linie: {line.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_draft_polyline(self, points, closed=True):
        try:
            import Draft
            wire = Draft.make_wire([self.to_vector(p) for p in points], closed=closed)
            App.ActiveDocument.recompute()
            return f"Draft-Polyline: {wire.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_rechteck(self, length="100mm", width="50mm", placement_x="0mm", placement_y="0mm", placement_z="0mm"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            rect = Draft.makeRectangle(self._parse_unit(length), self._parse_unit(width))
            rect.Placement.Base = App.Vector(self._parse_unit(placement_x), self._parse_unit(placement_y), self._parse_unit(placement_z))
            doc.recompute()
            return f"Rechteck: {rect.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_kreis(self, radius="50mm", placement_x="0mm", placement_y="0mm", placement_z="0mm"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            circ = Draft.makeCircle(self._parse_unit(radius))
            circ.Placement.Base = App.Vector(self._parse_unit(placement_x), self._parse_unit(placement_y), self._parse_unit(placement_z))
            doc.recompute()
            return f"Kreis: {circ.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_kreisbogen(self, center_x="0mm", center_y="0mm", center_z="0mm", radius="50mm", start_angle="0deg", end_angle="90deg"):
        try:
            import Draft
            doc = App.ActiveDocument or App.newDocument("BIM")
            s_ang = float(str(start_angle).replace('deg',''))
            e_ang = float(str(end_angle).replace('deg',''))
            arc = Draft.makeCircle(self._parse_unit(radius), startangle=s_ang, endangle=e_ang)
            arc.Placement.Base = App.Vector(self._parse_unit(center_x), self._parse_unit(center_y), self._parse_unit(center_z))
            doc.recompute()
            return f"Bogen: {arc.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    # --- Metadaten & IFC ---
    def setze_ifc_daten(self, object_name, properties_json="{}"):
        try:
            obj = self._get_obj(object_name)
            if not obj: return "Objekt nicht gefunden."
            import json
            props = json.loads(properties_json)
            for k, v in props.items():
                if not hasattr(obj, k):
                    obj.addProperty("App::PropertyString", k, "Base", k)
                setattr(obj, k, str(v))
            App.ActiveDocument.recompute()
            return "IFC-Daten gesetzt."
        except Exception as e: return f"Fehler: {str(e)}"

    def setze_material(self, obj_name, material_name, color_rgb=(0.8, 0.8, 0.8)):
        try:
            obj = self._get_obj(obj_name)
            if not obj: return "Objekt nicht gefunden."
            
            mat = App.ActiveDocument.getObject(material_name)
            if not mat:
                mat = App.ActiveDocument.addObject("App::MaterialObject", material_name)
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
            obj.Material = mat
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                obj.ViewObject.ShapeColor = shape_color
            App.ActiveDocument.recompute()
            return "Material gesetzt."
        except Exception as e: return f"Fehler: {str(e)}"

    def ermittle_mengen(self, obj_name):
        try:
            obj = self._get_obj(obj_name)
            if not obj: return "Objekt nicht gefunden."
            q = {}
            for k in ["Area", "Volume", "Length", "Height", "Width"]:
                if hasattr(obj, k) and getattr(obj, k) is not None:
                    val = getattr(obj, k)
                    q[k] = f"{val}"
            return f"Mengen für {obj.Label}:\n" + "\n".join([f"- {k}: {v}" for k, v in q.items()])
        except Exception as e: return f"Fehler: {str(e)}"

    def exportiere_ifc(self, file_path="model.ifc"):
        try:
            import Arch
            if not App.ActiveDocument: return "Kein aktives Dokument."

            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)

            try:
                import importIFC
                importIFC.export(App.ActiveDocument.Objects, file_path)
                return f"Exportiert: {file_path}"
            except ImportError:
                try:
                    import ifcopenshell
                except ImportError:
                    return ("Fehler: ifcopenshell nicht installiert. "
                            "Installiere es über den FreeCAD-Addon-Manager oder via 'pip install ifcopenshell'.")
                if hasattr(Arch, "export"):
                    Arch.export(App.ActiveDocument.Objects, file_path)
                    return f"Exportiert (via Arch): {file_path}"
                return "Fehler: Export-Modul nicht gefunden."
        except Exception as e: return f"Fehler: {str(e)}"

    def analysiere_ifc(self, file_path):
        try:
            if not os.path.isabs(file_path):
                file_path = os.path.abspath(file_path)
            if not os.path.exists(file_path):
                return f"Fehler: Datei nicht gefunden: {file_path}"
                
            import ifcopenshell
            f = ifcopenshell.open(file_path)
            res = f"Projekt: {f.by_type('IfcProject')[0].Name if f.by_type('IfcProject') else '?'}\n"
            counts = {}
            for e in f.by_type("IfcRoot"): counts[e.is_a()] = counts.get(e.is_a(), 0) + 1
            return res + "\n".join([f"- {k}: {v}" for k, v in sorted(counts.items())])
        except Exception as e: return f"Fehler: {str(e)}"


    # --- Neue Tools (MCP Tool Lücken) ---
    def objekt_info_abrufen(self, name):
        try:
            obj = self._get_obj(name)
            if not obj: return "Nicht gefunden."
            lines = [f"Label: {obj.Label}", f"Name: {obj.Name}", f"Type: {obj.TypeId}"]
            if hasattr(obj, "Shape") and obj.Shape:
                bb = obj.Shape.BoundBox
                lines.append(f"BBox: X({bb.XMin:.1f}..{bb.XMax:.1f}) Y({bb.YMin:.1f}..{bb.YMax:.1f}) Z({bb.ZMin:.1f}..{bb.ZMax:.1f})")
                lines.append(f"Volume: {obj.Shape.Volume:.1f}")
            for attr in ["Align", "Width", "Height", "Length"]:
                if hasattr(obj, attr):
                    val = getattr(obj, attr)
                    lines.append(f"{attr}: {val}")
            if hasattr(obj, "State"):
                lines.append(f"State: {obj.State}")
            if hasattr(obj, "Base") and obj.Base and hasattr(obj.Base, "Shape"):
                vs = obj.Base.Shape.Vertexes
                if len(vs) >= 2:
                    lines.append(f"Start: ({vs[0].Point.x:.1f}, {vs[0].Point.y:.1f}, {vs[0].Point.z:.1f})")
                    lines.append(f"End: ({vs[-1].Point.x:.1f}, {vs[-1].Point.y:.1f}, {vs[-1].Point.z:.1f})")
            return "\n".join(lines)
        except Exception as e: return f"Fehler: {str(e)}"

    def umbenennen_objekt(self, obj_name, neues_label):
        try:
            obj = self._get_obj(obj_name)
            if not obj: return "Nicht gefunden."
            obj.Label = neues_label
            App.ActiveDocument.recompute()
            return f"Umbenannt: {obj.Name} -> '{neues_label}'"
        except Exception as e: return f"Fehler: {str(e)}"

    def sichtbarkeit_setzen(self, name, sichtbar):
        try:
            obj = self._get_obj(name)
            if not obj: return "Nicht gefunden."
            if hasattr(obj, "ViewObject") and obj.ViewObject:
                obj.ViewObject.Visibility = bool(sichtbar)
                return f"Sichtbarkeit {name}: {sichtbar}"
            return "Kein ViewObject."
        except Exception as e: return f"Fehler: {str(e)}"

    def linie_verschieben(self, name, start_pkt, end_pkt):
        try:
            obj = self._get_obj(name)
            if not obj: return "Nicht gefunden."
            if not hasattr(obj, "StartPoint") or not hasattr(obj, "EndPoint"):
                return "Keine Draft-Linie."
            obj.StartPoint = self.to_vector(start_pkt)
            obj.EndPoint = self.to_vector(end_pkt)
            App.ActiveDocument.recompute()
            return f"Linie {name} verschoben."
        except Exception as e: return f"Fehler: {str(e)}"

    def wand_ausrichtung_setzen(self, wand_name, ref_aussen=True):
        try:
            wall = self._get_obj(wand_name)
            if not wall: return "Nicht gefunden."
            if not hasattr(wall, "Base") or not wall.Base: return "Keine Basislinie."
            vs = wall.Base.Shape.Vertexes
            if len(vs) < 2: return "Ungültige Basis."
            v_start, v_ende = vs[0].Point, vs[-1].Point
            w_dir = (v_ende - v_start).normalize()
            w_breite = float(wall.Width) if hasattr(wall, "Width") else 200.0
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
        except Exception as e: return f"Fehler: {str(e)}"

    def bool_cut_finalisieren(self, schnitt_name, neues_label, container="", verstecken=True):
        try:
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
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_oeffnung(self, base_obj_name, form="rectangle", pos=None, groesse=None, name="Oeffnung"):
        try:
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
        except Exception as e: return f"Fehler: {str(e)}"

    def kopiere_nach_geschoss(self, wand_liste, ziel_geschoss, z_versatz=3.24, x_verlaengerung=0.0):
        try:
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
                    new_wall.Width = src.Width if hasattr(src, "Width") else 300.0
                    new_wall.Height = src.Height if hasattr(src, "Height") else 2500.0
                    new_wall.Align = src.Align if hasattr(src, "Align") else "Left"
                    new_wall.Label = f"{src.Label}_OG"
                    if ziel:
                        if hasattr(ziel, "addObject"): ziel.addObject(new_wall)
                        elif hasattr(ziel, "Group"):
                            g = list(ziel.Group); g.append(new_wall); ziel.Group = g
                    created.append(new_wall.Label)
            doc.recompute()
            return f"Kopiert: {', '.join(created)}" if created else "Keine Wände kopiert."
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_attika(self, platte_name, hoehe=0.3, dicke=0.365, versatz=0.0, prefix="Attika"):
        try:
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
            return f"Attika: {', '.join(created)}" if created else "Keine Attika erstellt."
        except Exception as e: return f"Fehler: {str(e)}"

    def erstelle_decke_mit_oeffnungen(self, laenge="10m", breite="8m", hoehe="300mm",
                                    px="0mm", py="0mm", pz="0mm", oeffnungen=None, name="Geschossdecke"):
        try:
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
                tool.Length, tool.Width, tool.Height = ow, oh, h + 10.0
                tool.Placement.Base = App.Vector(px_mm + ox, py_mm + oy, pz_mm - 5.0)
                cut = doc.addObject("Part::Cut", f"SlabCut_{i}")
                cut.Base, cut.Tool = current, tool
                if hasattr(current, "ViewObject"): current.ViewObject.Visibility = False
                if hasattr(tool, "ViewObject"): tool.ViewObject.Visibility = False
                current = cut
            current.Label = name
            doc.recompute()
            return f"Decke mit {len(oeffnungen)} Öffnungen: {current.Label}"
        except Exception as e: return f"Fehler: {str(e)}"

    def waende_in_container_ausrichten(self, container_name, ref_aussen="outside"):
        try:
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
        except Exception as e: return f"Fehler: {str(e)}"

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
            if invalid: lines.append(f"INVALID: {', '.join(invalid)}")
            if touched: lines.append(f"TOUCHED: {', '.join(touched)}")
            if no_container: lines.append(f"Ohne Container: {', '.join(no_container)}")
            overlaps = []
            for i, a in enumerate(objs):
                if not hasattr(a, "Shape") or not a.Shape: continue
                for j, b in enumerate(objs):
                    if j <= i: continue
                    if not hasattr(b, "Shape") or not b.Shape: continue
                    if a.Shape.BoundBox.intersect(b.Shape.BoundBox):
                        overlaps.append(f"{a.Label} ∩ {b.Label}")
            if overlaps:
                overlap_str = "\n  ".join(overlaps[:10])
                lines.append(f"Überlappungen:\n  {overlap_str}")
            return "\n".join(lines) if lines else "OK"
        except Exception as e: return f"Fehler: {str(e)}"

    def validiere_ifc_export(self):
        try:
            doc = App.ActiveDocument
            if not doc: return "Kein Dokument."
            warnings = []
            for o in doc.Objects:
                issues = []
                if not hasattr(o, "IfcType") or not o.IfcType:
                    issues.append("kein IFC-Typ")
                if not hasattr(o, "Material") or not o.Material:
                    issues.append("kein Material")
                in_container = any(hasattr(p, "Group") and o in p.Group for p in doc.Objects)
                if not in_container:
                    issues.append("nicht in Container")
                if issues:
                    warnings.append(f"  {o.Label} ({o.Name}): {', '.join(issues)}")
            if warnings: return "IFC-Warnungen:\n" + "\n".join(warnings)
            return "IFC-Export bereit."
        except Exception as e: return f"Fehler: {str(e)}"

    def run_python(self, script):
        try:
            import FreeCADGui as Gui
            import io, sys
            stdout_capture = io.StringIO()
            old_stdout = sys.stdout
            sys.stdout = stdout_capture
            try:
                exec(script, {"App": App, "Part": Part, "Gui": Gui, "os": os, "time": time, "FreeCAD": App})
                if App.ActiveDocument: App.ActiveDocument.recompute()
            finally:
                sys.stdout = old_stdout
            
            output = stdout_capture.getvalue()
            return output if output else "OK."
        except Exception as e: return f"Fehler: {str(e)}"

# Globale Referenzen für Hot-Reload
_server_instance = None
_bridge_instance = None

def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((HOST, port)) != 0

def start_bridge():
    global _timer_obj, _server_instance, _bridge_instance
    if not check_port(PORT):
        print(f"!!! PORT {PORT} BELEGT - Versuche Hot-Reload !!!")
        try:
            b = xmlrpc.client.ServerProxy(f"http://{HOST}:{PORT}")
            b.hot_reload()
            print("--- Hot-Reload erfolgreich ---")
            return
        except Exception as e:
            print(f"Hot-Reload fehlgeschlagen: {e}")
            return
    server = xmlrpc.server.SimpleXMLRPCServer((HOST, PORT), allow_none=True, logRequests=False)
    bridge = RobustFreeCADBridge()
    server.register_instance(bridge)
    _server_instance = server
    _bridge_instance = bridge
    threading.Thread(target=server.serve_forever, daemon=True).start()
    
    # Timer-Setup für Snap / Modern FreeCAD
    try:
        import FreeCADGui
        if hasattr(FreeCADGui, "addTimer"):
            FreeCADGui.addTimer(50, process_requests)
            print("--- Bridge AKTIV (via FreeCADGui.addTimer) ---")
            return
    except: pass
    try:
        from PySide6 import QtCore
        _timer_obj = QtCore.QTimer()
        _timer_obj.timeout.connect(process_requests)
        _timer_obj.start(50)
        print("--- Bridge AKTIV (via PySide6.QTimer) ---")
        return
    except: pass
    try:
        from PySide2 import QtCore
        _timer_obj = QtCore.QTimer()
        _timer_obj.timeout.connect(process_requests)
        _timer_obj.start(50)
        print("--- Bridge AKTIV (via PySide2.QTimer) ---")
        return
    except: pass
    print("FEHLER: Kein Timer gefunden.")

if __name__ == "__main__":
    start_bridge()
