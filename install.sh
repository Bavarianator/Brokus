#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  install.sh – brokus installieren (Einstiegspunkt)
#
#  Delegiert an bin/brokus, das automatisch Dependencies,
#  Symlink und PATH einrichtet.
#
#  Usage:
#    ./install.sh             # installieren und starten
#    ./install.sh --help      # Hilfe
#    ./install.sh --uninstall # entfernen
# ─────────────────────────────────────────────────────────────

SCRIPT_DIR="$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)"

# ── Hilfe ──
if [[ "${1:-}" == "--help" || "${1:-}" == "-h" ]]; then
    echo "brokus – Installation (via bin/brokus)"
    echo
    echo "  $(basename "$0")               Installieren und starten"
    echo "  $(basename "$0") --uninstall    Entfernen"
    echo "  $(basename "$0") --help         Diese Hilfe"
    echo
    echo "Was passiert:"
    echo "  1. Python-Dependencies werden installiert (pip)"
    echo "  2. Symlink: bin/brokus → ~/.local/bin/brokus"
    echo "  3. ~/.local/bin wird zum PATH hinzugefügt"
    echo "  4. brokus startet"
    echo
    echo "Nach dem ersten Aufruf ist 'brokus' global verfügbar."
    exit 0
fi

# ── Uninstall ──
if [[ "${1:-}" == "--uninstall" ]]; then
    TARGET_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"
    TARGET_LINK="$TARGET_DIR/brokus"
    echo "  brokus deinstallieren"
    echo
    if [[ -L "$TARGET_LINK" ]]; then
        rm "$TARGET_LINK"
        echo "  ✓ Symlink entfernt: $TARGET_LINK"
    else
        echo "  ⚠ Kein Symlink gefunden: $TARGET_LINK"
    fi
    echo
    echo "  Python-Paket bleibt installiert (falls per pip installiert)."
    echo "  Zum Entfernen: pip uninstall brokus"
    exit 0
fi

# ── Delegiere an bin/brokus ──
exec "$SCRIPT_DIR/bin/brokus" "$@"
