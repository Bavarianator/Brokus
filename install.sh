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

# ── rclone automatisch installieren ──
_install_rclone() {
    if command -v rclone &>/dev/null; then
        return 0
    fi
    echo "  📦 Installiere rclone (Cloud-Upload für 40+ Anbieter)..." >&2
    if [[ "$(uname)" == "Darwin" ]]; then
        if command -v brew &>/dev/null; then
            brew install rclone 2>&1 && echo "  ✓ rclone installiert (brew)" >&2 && return 0
        fi
    elif command -v apt &>/dev/null; then
        sudo apt install -y rclone 2>&1 && echo "  ✓ rclone installiert (apt)" >&2 && return 0
    elif command -v pacman &>/dev/null; then
        sudo pacman -S --noconfirm rclone 2>&1 && echo "  ✓ rclone installiert (pacman)" >&2 && return 0
    elif command -v dnf &>/dev/null; then
        sudo dnf install -y rclone 2>&1 && echo "  ✓ rclone installiert (dnf)" >&2 && return 0
    fi
    echo "  ⚠ rclone konnte nicht automatisch installiert werden." >&2
    echo "  Installiere manuell: https://rclone.org/install/" >&2
    return 1
}

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

# ── rclone installieren ──
if [[ "${1:-}" != "--uninstall" && "${1:-}" != "--help" && "${1:-}" != "-h" ]]; then
    _install_rclone
fi

# ── Delegiere an bin/brokus ──
exec "$SCRIPT_DIR/bin/brokus" "$@"
