#!/usr/bin/env bash
#
# Startet die Testsuite und meldet PASS/FAIL.
#
# Aufruf:  bash run_tests.sh
#
# Die Suite braucht App aus der FreeCAD-Python-Konsole. Ein Lauf mit dem
# normalen Python (oder pytest) funktioniert nicht - dafür gibt es dieses Skript.

set -uo pipefail

cd "$(dirname "$0")" || exit 1

TESTFILE="test_mcp_tools.py"
TIMEOUT="${FREECAD_TEST_TIMEOUT:-300}"

if [ ! -f "$TESTFILE" ]; then
    echo "FEHLER: $TESTFILE nicht gefunden."
    echo "Skript muss aus dem Projektordner laufen."
    exit 2
fi

# FreeCAD-Binary suchen. Reihenfolge = Prioritaet.
find_freecad() {
    # 1. Ausdruecklich gesetzt? Dann muss es auch stimmen - ein Tippfehler
    #    darf nicht unmerklich auf ein anderes FreeCAD zurueckfallen.
    if [ -n "${FREECAD_CMD:-}" ]; then
        if command -v "$FREECAD_CMD" >/dev/null 2>&1; then
            command -v "$FREECAD_CMD"
        elif [ -x "$FREECAD_CMD" ]; then
            echo "$FREECAD_CMD"
        else
            return 2
        fi
        return 0
    fi
    # 2. Ueblicherweise im PATH
    for c in freecadcmd freecad FreeCAD; do
        if command -v "$c" >/dev/null 2>&1; then
            command -v "$c"
            return 0
        fi
    done
    # 3. Typische Installationsorte (Windows, AppImage, Homebrew)
    for p in \
        /usr/bin/freecadcmd \
        /usr/bin/freecad \
        /snap/bin/freecad \
        /Applications/FreeCAD.app/Contents/MacOS/FreeCADCmd \
        "/c/Program Files/FreeCAD 1.0/bin/FreeCADCmd.exe"; do
        if [ -x "$p" ]; then
            echo "$p"
            return 0
        fi
    done
    return 1
}

FREECAD_BIN="$(find_freecad)"
FIND_STATUS=$?

if [ $FIND_STATUS -eq 2 ]; then
    echo "FEHLER: FREECAD_CMD='${FREECAD_CMD}' ist nicht ausfuehrbar."
    echo "Pfad pruefen, oder die Variable entfernen fuer die automatische Suche."
    exit 3
fi
if [ $FIND_STATUS -ne 0 ]; then
    cat <<'EOF'
FEHLER: Kein FreeCAD gefunden.

FreeCAD-Binary im PATH ablegen, oder Pfad explizit setzen:
    FREECAD_CMD=/pfad/zu/freecad bash run_tests.sh

Gesucht wurde: freecadcmd, freecad, FreeCAD
EOF
    exit 3
fi

echo "FreeCAD:  $FREECAD_BIN"
echo "Testsuite: $TESTFILE"
echo "Timeout:   ${TIMEOUT}s"
echo "---"

# FreeCAD startet in einem eigenen Arbeitsverzeichnis (Snap: /var/lib/snapd/void),
# nicht in dem, aus dem dieses Skript laeuft. Deshalb den absoluten Pfad zur
# Bridge uebergeben - sonst findet der Test die Datei nicht.
export FREECAD_BRIDGE_PATH="$(pwd)/freecad_bridge.py"

# -c startet FreeCAD headless (Konsole, kein GUI).
# Das Skript wird ueber stdin gefuettert, weil FreeCAD keine eingerueckten
# Bloecke direkt ausfuehren kann.
OUTPUT="$(timeout "$TIMEOUT" "$FREECAD_BIN" -c < "$TESTFILE" 2>&1)"
STATUS=$?

RESULT_LINE="$(printf '%s\n' "$OUTPUT" | grep -E "^=== RESULT:" | tail -1)"

if [ -z "$RESULT_LINE" ]; then
    echo "FEHLER: Kein Ergebniszeilen - die Suite ist abgebrochen (Exit $STATUS)."
    echo "Die letzten 20 Zeilen der Ausgabe:"
    printf '%s\n' "$OUTPUT" | tail -20
    exit 1
fi

echo "$OUTPUT" | grep -E "^  (PASS|FAIL):" | sed 's/^  //'

echo "---"
echo "$RESULT_LINE"

# Exit-Code aus der Zusammenfassung ableiten.
if printf '%s' "$RESULT_LINE" | grep -qE ", 0 failed"; then
    exit 0
else
    exit 1
fi