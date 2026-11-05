#!/usr/bin/env python3
"""Aplica los parches Linux a los archivos de IndieDL / Subs-Now.
Uso:  python3 parche.py
Idempotente: si ya está parcheado, no cambia nada."""
import re
import sys
from pathlib import Path


def ensure_import(text: str) -> str:
    """Asegura `import plat_compat as pc` después de los imports base."""
    if "import plat_compat as pc" in text:
        return text
    # Insertar después del último import de la zona superior
    lines = text.splitlines(keepends=True)
    last_import = -1
    for i, line in enumerate(lines[:80]):
        if re.match(r"^(import|from)\s+\S", line):
            last_import = i
    if last_import < 0:
        return text
    lines.insert(last_import + 1, "import plat_compat as pc\n")
    return "".join(lines)


def apply(name: str, text: str, subs: list, required_any: bool = False) -> tuple[str, int]:
    """Aplica lista de tuplas (patrón, reemplazo, [regex])."""
    applied = 0
    for item in subs:
        old, new = item[0], item[1]
        is_regex = len(item) > 2 and item[2]
        if is_regex:
            pat = re.compile(old, re.DOTALL)
            new_text, n = pat.subn(new, text)
        else:
            if old in text:
                new_text = text.replace(old, new, 1)
                n = 1
            else:
                new_text, n = text, 0
        if n:
            text = new_text
            applied += 1
        elif required_any:
            print(f"  ⚠ {name}: patrón no encontrado → {old[:60]!r}")
    return text, applied


# ═════════════════════════════════════════════════════════════
# PARCHES POR ARCHIVO
# ═════════════════════════════════════════════════════════════

def patch_indiedl(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    subs = [
        # Rutas base
        ("""APP_DIR = Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "IndieDL"
CFG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "indiedl.log"
TEMP_DIR = APP_DIR / "tmp"
NO_WINDOW = 0x08000000 if os.name == "nt" else 0""",
         """import plat_compat as pc
APP_DIR = pc.app_dir("IndieDL")
CFG_FILE = APP_DIR / "config.json"
LOG_FILE = APP_DIR / "indiedl.log"
TEMP_DIR = APP_DIR / "tmp"
NO_WINDOW = pc.NO_WINDOW"""),

        # ensure_temp_dir: quitar os.chdir global
        ("""    try: os.chdir(str(APP_DIR))
    except OSError: pass
    return temp_path""",
         """    return temp_path"""),

        # _low_integrity
        (r"def _low_integrity\(\):(?:(?!\ndef ).)*?return False\n",
         "def _low_integrity():\n    return pc.low_integrity()\n",
         True),

        # running_browser_processes / close_browser_processes
        (r"def running_browser_processes\(key\):.*?\n\n(?=def |class )",
         "def running_browser_processes(key):\n"
         "    hint = BROWSER_PROC_HINT.get(key, key)\n"
         "    names = pc.list_processes()\n"
         "    return sorted(n for n in names\n"
         "                  if hint in n.lower() and n.lower().endswith(('.exe',)) ) or \\\n"
         "           sorted(n for n in names if hint in n.lower())\n\n",
         True),

        (r"def close_browser_processes\(names\):.*?\n\n(?=def |class )",
         "def close_browser_processes(names):\n"
         "    for n in names:\n        pc.kill_process(n)\n\n",
         True),

        # os.startfile en open_dir (método de la clase App, 8 espacios)
        ("""        def open_dir(self, p):
            try:
                os.startfile(p)
            except Exception:
                pass""",
         """        def open_dir(self, p):
            pc.open_path(p)"""),

        # Dark titlebar
        (r"        def _apply_dark_titlebar\(self\):.*?(?=\n        def |\n        class )",
         "        def _apply_dark_titlebar(self):\n            pc.apply_dark_titlebar(self)\n\n",
         True),

        # ffmpeg_path
        (r"def ffmpeg_path\(\):.*?(?=\ndef )",
         "def ffmpeg_path():\n    return pc.find_ffmpeg()\n\n",
         True),

        # Fuentes en halftone_header / cached_header
        (r'    for p in \("C:/Windows/Fonts/seguibl\.ttf".*?\n              "DejaVuSans-Bold\.ttf"\):',
         '''    _fp = pc.font_file("seguibl.ttf", "ariblk.ttf", "arialbd.ttf")\n    for p in ([_fp] if _fp else []):''',
         True),

        # Cache dir
        ('cache_dir = APP_DIR / "cache"',
         'cache_dir = pc.cache_dir(APP_DIR)'),

        # browser_profile_candidates
        (r"def browser_profile_candidates\(\):.*?(?=\ndef )",
         "def browser_profile_candidates():\n"
         "    return pc.browser_profiles()\n\n",
         True),

        # Carpeta de descarga por defecto (XDG en Linux, E:\ en Windows)
        ('"last_dir": "E:\\\\" if os.path.isdir("E:\\\\") else str(Path.home() / "Videos"),',
         '"last_dir": str(pc.download_dir()),'),

        # Diálogos nativos de KDE/GTK al arrancar la interfaz
        ("def build_app():\n    import customtkinter as ctk",
         "def build_app():\n    pc.patch_tkinter_dialogs()\n"
         "    import customtkinter as ctk"),

        # register()
        (r"def register\(\):.*?(?=\ndef )",
         "def register():\n"
         "    if not pc.register_protocol(Path(__file__).resolve()):\n"
         "        log('Registro de protocolo no disponible en este SO.')\n\n",
         True),
    ]

    text, n = apply(p.name, text, subs, required_any=True)
    if text != orig:
        text = ensure_import(text)
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: {n} parches aplicados")
        return True
    print(f"  - {p.name}: sin cambios")
    return True


def patch_analizar_media(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    subs = [
        (r"def find_tools\(\):.*?(?=\ndef )",
         "def find_tools():\n"
         "    import plat_compat as pc\n"
         "    ff = pc.find_ffmpeg()\n"
         "    fp = pc.find_ffprobe(ff)\n"
         "    return ff, fp\n\n",
         True),
    ]
    text, n = apply(p.name, text, subs, required_any=True)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: {n} parches")
        return True
    print(f"  - {p.name}: sin cambios")
    return True


def patch_gpu_runtime(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    new_body = '''def preparar_cuda() -> list[str]:
    """Registra DLL de CUDA del instalador o de los paquetes NVIDIA de Python."""
    app = _app_dir()
    bases = [app / "cuda-runtime", app.parent / "cuda-runtime"]
    bases.extend(Path(p) / "nvidia" for p in sys.path if p and Path(p).is_dir())

    rutas = []
    for base in bases:
        if not base.is_dir():
            continue
        if base.name.lower() == "nvidia":
            for sub in base.iterdir():
                if not sub.is_dir() or "cu11" in sub.name.lower():
                    continue
                for libdir in ("bin", "lib"):
                    if (sub / libdir).is_dir():
                        rutas.append(sub / libdir)
        else:
            rutas.append(base)
            rutas.extend(x for x in base.rglob("*") if x.is_dir())
    rutas = list(dict.fromkeys(p for p in rutas if p.is_dir()))
    if not rutas:
        return []
    cargadores = []
    for ruta in rutas:
        try:
            if hasattr(os, "add_dll_directory"):
                cargadores.append(os.add_dll_directory(str(ruta)))
        except (AttributeError, OSError):
            pass
    os.environ["PATH"] = os.pathsep.join(
        [str(p) for p in rutas] + [os.environ.get("PATH", "")])
    if os.name != "nt":
        os.environ["LD_LIBRARY_PATH"] = os.pathsep.join(
            [str(p) for p in rutas] + [os.environ.get("LD_LIBRARY_PATH", "")])
    global _DLL_HANDLES
    _DLL_HANDLES = cargadores
    return [str(p) for p in rutas]
'''

    pat = re.compile(r"def preparar_cuda\(\) -> list\[str\]:.*?(?=\ndef nvidia_info)",
                     re.DOTALL)
    if pat.search(text):
        text = pat.sub(new_body + "\n\n", text)
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: preparar_cuda reescrito")
        return True
    print(f"  ⚠ {p.name}: patrón de preparar_cuda no encontrado")
    return False


def patch_subtitulos(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    subs = [
        # DPI aware
        ("""try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass""",
         """import plat_compat as pc
pc.set_dpi_aware()"""),

        # _preparar_resolve
        (r"def _preparar_resolve\(\):.*?(?=\n_preparar_resolve\(\))",
         '''def _preparar_resolve():
    api, lib = pc.resolve_scripting_paths()
    os.environ["RESOLVE_SCRIPT_API"] = api
    os.environ["RESOLVE_SCRIPT_LIB"] = lib
    mod = os.path.join(api, "Modules")
    if mod not in sys.path:
        sys.path.insert(0, mod)
    if pc.IS_WIN:
        try:
            os.add_dll_directory(os.path.dirname(lib))
        except Exception:
            pass

''',
         True),
    ]
    text, n = apply(p.name, text, subs, required_any=True)
    if text != orig:
        text = ensure_import(text)
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: {n} parches")
        return True
    print(f"  - {p.name}: sin cambios")
    return True


def patch_subtitulos_ui(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    subs = [
        # _abrir_carpeta
        (r"def _abrir_carpeta\(self\):.*?(?=\n    def )",
         '''    def _abrir_carpeta(self):
        ruta = self.v_srt.get() or self.v_guion.get()
        carpeta = os.path.dirname(ruta) if ruta else os.path.expanduser("~")
        pc.open_path(carpeta)

''',
         True),

        # _apply_dark_titlebar
        (r"def _apply_dark_titlebar\(self\):.*?(?=\n    def )",
         '''    def _apply_dark_titlebar(self):
        pc.apply_dark_titlebar(self.root)

''',
         True),
    ]
    text, n = apply(p.name, text, subs, required_any=True)
    if text != orig:
        text = ensure_import(text)
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: {n} parches")
        return True
    print(f"  - {p.name}: sin cambios")
    return True


def patch_indie_ui(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    subs = [
        # _font_file → delegar a plat_compat
        (r"def _font_file\(\*names\):.*?(?=\n\ndef |\n\nclass |\Z)",
         '''def _font_file(*names):
    import plat_compat as pc
    return pc.font_file(*names)


''',
         True),

        # Fallbacks de fuentes en init_fonts
        ('''    F_BLACK = pick("Segoe UI Black", "Arial Black", "Segoe UI", "Arial")
    F_SEMI = pick("Segoe UI Semibold", "Segoe UI", "Arial")
    F_BODY = pick("Segoe UI", "Arial")
    F_MONO = pick("Consolas", "Cascadia Mono", "Courier New")''',
         '''    F_BLACK = pick("Segoe UI Black", "Arial Black", "Liberation Sans",
                   "DejaVu Sans", "Arial")
    F_SEMI  = pick("Segoe UI Semibold", "Liberation Sans", "DejaVu Sans", "Arial")
    F_BODY  = pick("Segoe UI", "Liberation Sans", "DejaVu Sans", "Arial")
    F_MONO  = pick("Consolas", "Cascadia Mono", "Liberation Mono",
                   "DejaVu Sans Mono", "Courier New")'''),
    ]
    text, n = apply(p.name, text, subs, required_any=True)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: {n} parches")
        return True
    print(f"  - {p.name}: sin cambios")
    return True


def patch_cortes_verificar(p: Path) -> bool:
    text = p.read_text(encoding="utf-8")
    orig = text

    subs = [
        ('''os.environ.setdefault("RESOLVE_SCRIPT_API",
    r"C:\\ProgramData\\Blackmagic Design\\DaVinci Resolve\\Support\\Developer\\Scripting")
os.environ.setdefault("RESOLVE_SCRIPT_LIB",
    r"C:\\Program Files\\Blackmagic Design\\DaVinci Resolve\\fusionscript.dll")''',
         '''import plat_compat as pc
_api, _lib = pc.resolve_scripting_paths()
os.environ.setdefault("RESOLVE_SCRIPT_API", _api)
os.environ.setdefault("RESOLVE_SCRIPT_LIB", _lib)'''),
    ]
    text, n = apply(p.name, text, subs)
    if text != orig:
        p.write_text(text, encoding="utf-8")
        print(f"  ✓ {p.name}: {n} parches")
        return True
    print(f"  - {p.name}: sin cambios")
    return True


# ═════════════════════════════════════════════════════════════
# MAIN
# ═════════════════════════════════════════════════════════════

def main():
    here = Path(__file__).resolve().parent
    print(f"Parcheando {here}…\n")

    targets = {
        "indiedl.py":           patch_indiedl,
        "analizar_media.py":    patch_analizar_media,
        "gpu_runtime.py":       patch_gpu_runtime,
        "subtitulos.py":        patch_subtitulos,
        "subtitulos_ui.py":     patch_subtitulos_ui,
        "indie_ui.py":          patch_indie_ui,
        "cortes.py":            patch_cortes_verificar,
        "verificar.py":         patch_cortes_verificar,
    }

    for name, fn in targets.items():
        # Buscar en raíz o en app/
        for candidate in (here / name, here / "app" / name):
            if candidate.exists():
                try:
                    fn(candidate)
                except Exception as exc:
                    print(f"  ✗ {name}: ERROR {type(exc).__name__}: {exc}")
                break
        else:
            print(f"  · {name}: no está en este repo (saltando)")

    print("\nListo. Revisá el output arriba.")
    print("Si algún parche no matcheó, mandame ese archivo y ajustamos el patrón.")


if __name__ == "__main__":
    main()