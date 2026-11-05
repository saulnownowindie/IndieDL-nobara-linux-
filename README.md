# Indie Now DL · Nobara / Fedora (Linux)

Port de **Indie Now DL** a Linux (probado en Nobara 44 / Fedora, KDE + Wayland).
La extensión de Chromium no cambia: sigue enviando `ytdl://…` y el sistema abre
la app con el handler `.desktop`.

## Instalar

```bash
git clone https://github.com/saulnownowindie/IndieDL-nobara-linux-.git
cd IndieDL-nobara-linux-
./instalar.sh
```

El script:
1. Instala dependencias del sistema (Python, Tkinter, ffmpeg, fuentes).
2. Crea el venv en `~/.local/share/IndieDL/venv`.
3. Instala `requirements.txt`.
4. Aplica los parches de Linux (`parche.py`) sobre los archivos de Windows.
5. Registra `x-scheme-handler/ytdl` con `indiedl.desktop`.

Para instalar en otra ruta:

```bash
PREFIX=/opt/IndieDL ./instalar.sh
```

## Extensión de Helium/Chrome

En `chrome://extensions` (o `helium://extensions`):

1. Modo de desarrollador.
2. «Cargar descomprimida» → `~/.local/share/IndieDL/browser-extension`.
3. Recargar la pestaña de YouTube/Instagram/TikTok/X/Pinterest.

La primera vez que un sitio abre `ytdl://`, Chromium pide permiso. Marcá
«Siempre permitir» para ese sitio (YouTube e Instagram ya lo tienen permitido
en perfiles habituales).

## Probar el handler

```bash
xdg-mime query default x-scheme-handler/ytdl   # indiedl.desktop
xdg-open 'ytdl://video/?u=https%3A%2F%2Fyoutu.be%2FjNQXAC9IVRw'
```

Tiene que abrirse la ventana «Indie Now DL» con la URL cargada.

## Qué parchea

- Rutas XDG (`~/.local/share`, `~/.cache`) en lugar de `%LOCALAPPDATA%`.
- `ffmpeg`: del sistema o el binario de `imageio-ffmpeg`.
- Perfiles de navegador para cookies (Helium, Chrome, Chromium, Brave, Edge, Firefox, Zen).
- `os.startfile` → `xdg-open`.
- DPI y barra de título oscura → no-op.
- `ytdl://` → `.desktop` + `xdg-mime` en lugar del registro de Windows.
- Diálogos de archivo nativos con `kdialog` (KDE) o `zenity` (GTK), con vuelta a Tkinter.
- Carpeta de descarga por defecto: `xdg-user-dir VIDEOS` (`~/Vídeos`), no `~/Videos`.

`parche.py` es idempotente: se puede volver a ejecutar tras un `git pull`.

## Requisitos

- Python 3.10+ con Tkinter (`python3-tkinter`).
- `ffmpeg` (o `imageio-ffmpeg`, incluido en requirements).
- Opcional: `kdialog` o `zenity` para diálogos nativos.
- Opcional: `deno` o `node` si YouTube pide un runtime JavaScript a yt-dlp.

## Desinstalar

```bash
./desinstalar.sh
```

Después quitá la extensión desde `chrome://extensions`.
