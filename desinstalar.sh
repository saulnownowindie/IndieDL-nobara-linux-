#!/usr/bin/env bash
set -euo pipefail
PREFIX="${PREFIX:-${XDG_DATA_HOME:-$HOME/.local/share}/IndieDL}"
APPS="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
echo "Desinstalando IndieDL de $PREFIX"
rm -rf "$PREFIX"
rm -f "$APPS/indiedl.desktop" "$APPS/indiedl-url.desktop"
update-desktop-database "$APPS" 2>/dev/null || true
echo "Listo. Quitá también la extensión desde chrome://extensions."
