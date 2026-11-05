#!/usr/bin/env bash
# Instalador de IndieDL para Nobara/Fedora (y otras distros con dnf/apt).
#
# Uso:
#   git clone https://github.com/saulnownowindie/IndieDL-nobara-linux-.git
#   cd IndieDL-nobara-linux-
#   ./instalar.sh
#
# Variables opcionales:
#   PREFIX=/otra/ruta   Destino de la app (default: ~/.local/share/IndieDL)
#   PYTHON=python3      Intérprete base
set -euo pipefail

REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PREFIX="${PREFIX:-${XDG_DATA_HOME:-$HOME/.local/share}/IndieDL}"
PYTHON="${PYTHON:-python3}"

log() { printf '\n== %s\n' "$*"; }

command -v "$PYTHON" >/dev/null 2>&1 || {
  echo "No encontré $PYTHON. Instalá Python 3.10 o superior." >&2
  exit 1
}

log "Destino: $PREFIX"
mkdir -p "$PREFIX"

# 1. Dependencias del sistema (idempotentes)
if command -v dnf >/dev/null 2>&1; then
  log "Dependencias del sistema (dnf)"
  sudo dnf install -y python3 python3-pip python3-tkinter xdg-utils \
    fontconfig liberation-sans-fonts dejavu-sans-fonts \
    google-noto-sans-mono-fonts 2>&1 | tail -3 || true
  if ! command -v ffmpeg >/dev/null 2>&1; then
    sudo dnf install -y ffmpeg-free 2>&1 | tail -2 || true
  fi
elif command -v apt >/dev/null 2>&1; then
  log "Dependencias del sistema (apt)"
  sudo apt-get update -qq
  sudo apt-get install -y -qq python3 python3-pip python3-tk python3-venv \
    ffmpeg xdg-utils fonts-liberation fonts-dejavu fonts-noto-mono
else
  log "No detecté dnf ni apt. Asegurate de tener Python, Tkinter, ffmpeg y xdg-utils."
fi

# 2. Copiar la aplicación
log "Copiando la aplicación"
cp -a "$REPO/app/indiedl.py" "$REPO/app/analizar_media.py" "$PREFIX/"
cp -a "$REPO/plat_compat.py" "$REPO/parche.py" "$PREFIX/"
if [ -d "$PREFIX/browser-extension" ]; then
  rm -rf "$PREFIX/browser-extension"
fi
cp -a "$REPO/browser-extension" "$PREFIX/browser-extension"
cp -a "$REPO/requirements.txt" "$PREFIX/requirements.txt"

# 3. Venv + dependencias
log "Entorno virtual"
if [ ! -x "$PREFIX/venv/bin/python" ]; then
  "$PYTHON" -m venv "$PREFIX/venv"
fi
"$PREFIX/venv/bin/python" -m pip install --quiet --upgrade pip
"$PREFIX/venv/bin/python" -m pip install --quiet -r "$REPO/requirements.txt"

# 4. Parches Linux
log "Aplicando parches de Linux"
"$PREFIX/venv/bin/python" "$PREFIX/parche.py"

# 5. Registrar ytdl://
log "Registrando el protocolo ytdl://"
"$PREFIX/venv/bin/python" "$PREFIX/indiedl.py" --register-only

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${XDG_DATA_HOME:-$HOME/.local/share}/applications" >/dev/null 2>&1 || true
fi

cat <<EOF

Listo. IndieDL quedó en:
  $PREFIX

Abrila desde el menú («Indie Now DL») o con:
  $PREFIX/venv/bin/python $PREFIX/indiedl.py

Extensión de Helium/Chrome:
  $PREFIX/browser-extension

En chrome://extensions (o helium://extensions):
  1. Modo de desarrollador.
  2. «Cargar descomprimida» → $PREFIX/browser-extension.
  3. Recargar la pestaña de YouTube/Instagram/etc.

La primera vez que un sitio abre ytdl://, Chromium puede pedir permiso.
Marcá «Siempre permitir» para ese sitio.

Desinstalar:
  $REPO/desinstalar.sh   (o rm -rf $PREFIX y los .desktop)
EOF
