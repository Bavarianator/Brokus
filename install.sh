#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  install.sh – brokus install / update helper
#
#  Symlinkt bin/brokus → ~/.local/bin/brokus, prüft Python-
#  Dependencies und installiert sie bei Bedarf.
#
#  Usage:
#    ./install.sh             # installieren
#    ./install.sh --uninstall # entfernen
#    ./install.sh --help      # Hilfe
# ─────────────────────────────────────────────────────────────

set -e

# ── Pfade ──
SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"
BROKUS_BIN="$SCRIPT_DIR/bin/brokus"
TARGET_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
TARGET_LINK="$TARGET_DIR/brokus"
LOCAL_BIN_LINE='export PATH="$HOME/.local/bin:$PATH"'

# ── Farben ──
GREEN='\033[0;32m'
CYAN='\033[0;36m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
DIM='\033[2m'
NC='\033[0m' # No Color

info()  { echo -e "  ${CYAN}→${NC} $1"; }
ok()    { echo -e "  ${GREEN}✓${NC} $1"; }
warn()  { echo -e "  ${YELLOW}⚠${NC} $1"; }
err()   { echo -e "  ${RED}✗${NC} $1"; }
dim()   { echo -e "  ${DIM}$1${NC}"; }

# ── Hilfe ──
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "brokus – Installations-Helfer"
    echo
    echo "  $(basename "$0")               Installieren / aktualisieren"
    echo "  $(basename "$0") --uninstall    Entfernen"
    echo "  $(basename "$0") --help         Diese Hilfe"
    echo
    echo "Was passiert:"
    echo "  • $BROKUS_BIN → $TARGET_LINK (Symlink)"
    echo "  • Eintrag in ~/.bashrc / ~/.zshrc für PATH (falls nötig)"
    echo "  • Python-Dependencies werden installiert (pip install -e .)"
    exit 0
fi

# ── Uninstall ──
if [[ "${1:-}" == "--uninstall" ]]; then
    echo "  brokus deinstallieren"
    echo
    if [[ -L "$TARGET_LINK" ]]; then
        rm "$TARGET_LINK"
        ok "Symlink entfernt: $TARGET_LINK"
    else
        warn "Kein Symlink gefunden: $TARGET_LINK"
    fi
    echo
    dim "Python-Paket bleibt installiert (falls per pip installiert)."
    dim "Zum Entfernen: pip uninstall brokus"
    exit 0
fi

# ═════════════════════════════════════════════════════════════
#  Haupt-Logik
# ═════════════════════════════════════════════════════════════

echo
echo -e "  ${GREEN}██████${NC}  ${CYAN}brokus${NC} – Installation"
echo -e "  ${GREEN}██   ██${NC}  KI-gestützter Buch-Generator"
echo -e "  ${GREEN}██████${NC}  Einfach. Terminal. Roman."
echo
dim "  $(basename "$0") --help für Details"
echo

# ── Schritt 1: Python prüfen ──
info "Prüfe Python..."
PYTHON=""
for cmd in python3 python; do
    if command -v "$cmd" &>/dev/null; then
        PY_VER=$("$cmd" --version 2>&1 | grep -oP '\d+\.\d+')
        if [[ "$(echo "$PY_VER" | cut -d. -f1)" -ge 3 && "$(echo "$PY_VER" | cut -d. -f2)" -ge 10 ]]; then
            PYTHON="$cmd"
            ok "Python $PY_VER gefunden: $PYTHON"
            break
        fi
    fi
done

if [[ -z "$PYTHON" ]]; then
    err "Python 3.10+ nicht gefunden. Bitte installieren: https://python.org"
    exit 1
fi

# ── Schritt 2: Dependencies installieren ──
info "Prüfe Python-Dependencies..."
cd "$SCRIPT_DIR"

# Prüfe ob rich (Haupt-Dependency) bereits installiert ist
if $PYTHON -c "import rich" 2>/dev/null; then
    ok "Dependencies bereits installiert"
else
    info "Installiere Dependencies (pip install -e .)..."
    
    # Versuch normal — Ausgabe mitschneiden, um PEP 668 zu erkennen
    PIP_OUTPUT=$($PYTHON -m pip install -e . 2>&1) && {
        ok "Dependencies installiert"
    } || {
        if echo "$PIP_OUTPUT" | grep -qi "externally-managed"; then
            # PEP 668 (Arch Linux) → Fallback mit --break-system-packages
            warn "PEP 668 erkannt (Arch/Manjaro) — versuche mit --break-system-packages..."
            PIP_OUTPUT2=$($PYTHON -m pip install --break-system-packages -e . 2>&1) && {
                ok "Dependencies installiert (--break-system-packages)"
            } || {
                warn "pip-install fehlgeschlagen:"
                echo "$PIP_OUTPUT2" | head -5 | while read -r line; do warn "$line"; done
                warn "Manuelle Installation: cd $SCRIPT_DIR && pip install -e ."
            }
        else
            # Anderer Fehler → anzeigen
            warn "pip-install fehlgeschlagen:"
            echo "$PIP_OUTPUT" | head -5 | while read -r line; do warn "$line"; done
            warn "Manuelle Installation: cd $SCRIPT_DIR && pip install -e ."
        fi
    }
fi

echo

# ── Schritt 3: Symlink erstellen ──
info "Installiere 'brokus'-Befehl..."
mkdir -p "$TARGET_DIR"

if [[ -L "$TARGET_LINK" ]]; then
    # Symlink existiert bereits → aktualisieren
    ln -sf "$BROKUS_BIN" "$TARGET_LINK"
    ok "Symlink aktualisiert: $TARGET_LINK → $BROKUS_BIN"
elif [[ -f "$TARGET_LINK" ]]; then
    # Datei existiert (kein Symlink) → warnen
    warn "Datei existiert bereits: $TARGET_LINK"
    warn "Bitte manuell löschen und erneut ausführen."
else
    ln -s "$BROKUS_BIN" "$TARGET_LINK"
    ok "Symlink erstellt: $TARGET_LINK → $BROKUS_BIN"
fi

# ── Schritt 4: PATH prüfen & Shell-Config aktualisieren ──
if ! echo "$PATH" | tr ':' '\n' | grep -qx "$TARGET_DIR"; then
    warn "$TARGET_DIR ist nicht im PATH!"
    echo
    
    # Aktuelle Shell erkennen
    SHELL_NAME="$(basename "${SHELL:-/bin/bash}")"
    case "$SHELL_NAME" in
        zsh)  RC="$HOME/.zshrc" ;;
        bash) RC="$HOME/.bashrc" ;;
        *)    # Fallback: erste existierende Config-Datei
              for f in "$HOME/.profile" "$HOME/.bash_profile" "$HOME/.bashrc" "$HOME/.zshrc"; do
                  [[ -f "$f" ]] && { RC="$f"; break; }
              done
              [[ -z "$RC" ]] && RC="$HOME/.profile" ;;
    esac
    
    if ! grep -q "\.local/bin" "$RC" 2>/dev/null; then
        echo "" >> "$RC"
        echo "# brokus: lokale Binaries zum PATH hinzufügen" >> "$RC"
        echo "$LOCAL_BIN_LINE" >> "$RC"
        ok "PATH-Eintrag in $RC hinzugefügt"
    else
        warn "PATH-Eintrag bereits in $RC vorhanden"
    fi
    
    echo
    dim "Lade die Konfiguration neu: source $RC"
    dim "Oder direkt: export PATH=\"\$HOME/.local/bin:\$PATH\""
fi

echo

# ── Fertig ──
if command -v brokus &>/dev/null; then
    VER=$($PYTHON -c "from brokus import __version__; print(__version__)" 2>/dev/null || echo "?")
    ok "${GREEN}brokus v$VER${NC} ist jetzt installiert!"
    dim "  Starte mit:  brokus"
    dim "  Hilfe:       brokus --help"
else
    warn "brokus ist noch nicht direkt im PATH."
    dim "  Starte mit:  $PYTHON -m brokus"
    dim "  Oder:        source ~/.bashrc && brokus"
fi

echo
