# -*- coding: utf-8 -*-
"""
ClashBot AI - Application Launcher
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar
"""
import os
import sys
import subprocess

def _ensure_python_310():
    """Ensure runtime is executing on Python 3.10 (required by PyArmor cp310 binary ABI)."""
    if sys.version_info[:2] == (3, 10):
        return

    print("=" * 60)
    print(f"[!] Active Python: {sys.version.split()[0]} ({sys.executable})")
    print("[*] ClashBot AI requires Python 3.10 (64-bit) for binary UI compatibility.")
    print("=" * 60)

    # 1. Search for existing Python 3.10 installations
    candidates = [
        os.path.expandvars(r"%LocalAppData%\Programs\Python\Python310\python.exe"),
        r"C:\Program Files\Python310\python.exe",
    ]

    target_py = None
    for cand in candidates:
        if os.path.isfile(cand):
            try:
                res = subprocess.run([cand, "-c", "import sys; print(sys.version_info[:2])"], capture_output=True, text=True)
                if "(3, 10)" in res.stdout:
                    target_py = cand
                    break
            except Exception:
                pass

    # 2. If Python 3.10 is not installed, trigger automated installer
    if not target_py:
        print("[*] Python 3.10 not found. Launching automated installer...")
        ps_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "setup_environment.ps1")
        if os.path.isfile(ps_script):
            subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", ps_script])
            for cand in candidates:
                if os.path.isfile(cand):
                    target_py = cand
                    break

    # 3. Re-launch under Python 3.10
    if target_py and os.path.isfile(target_py):
        print(f"[+] Re-launching ClashBot AI under Python 3.10 ({target_py})...\n")
        try:
            os.execv(target_py, [target_py] + sys.argv)
        except Exception:
            # Fallback for Windows if execv has handle inheritance issues
            res = subprocess.call([target_py] + sys.argv)
            sys.exit(res)
    else:
        print("[-] ERROR: Python 3.10 could not be located or installed automatically.")
        print("[*] Please run install.bat to configure Python 3.10.")
        sys.exit(1)

_ensure_python_310()


def install_spoof_module_finder():
    """Universal import hook that intercepts missing legacy modules and provides safe stubs."""
    import types
    from importlib.abc import MetaPathFinder, Loader
    from importlib.machinery import ModuleSpec

    class _SpoofObject:
        def __init__(self, name=""):
            self._name = name
        def __call__(self, *args, **kwargs):
            return _SpoofObject(self._name)
        def __getattr__(self, name):
            if name.startswith("__") and name.endswith("__"):
                raise AttributeError(name)
            return _SpoofObject(f"{self._name}.{name}")
        def __mro_entries__(self, bases):
            return (object,)
        def __bool__(self):
            return True
        def __int__(self):
            return 0
        def __float__(self):
            return 0.0
        def __len__(self):
            return 0
        def __iter__(self):
            return iter([])
        def __getitem__(self, key):
            return _SpoofObject(f"{self._name}[{key}]")
        def __repr__(self):
            return f"<Spoof {self._name}>"

    class _SpoofLoader(Loader):
        def create_module(self, spec):
            mod = types.ModuleType(spec.name)
            mod.__path__ = []
            mod.__file__ = f"<spoofed_{spec.name}>"
            mod.__loader__ = self
            return mod
        def exec_module(self, mod):
            def _getattr(name):
                if name.startswith("__") and name.endswith("__"):
                    raise AttributeError(name)
                obj = _SpoofObject(f"{mod.__name__}.{name}")
                setattr(mod, name, obj)
                return obj
            mod.__getattr__ = _getattr

    class SpoofFinder(MetaPathFinder):
        # Protected core modules that must be loaded normally
        PROTECTED = {
            "sys", "os", "PySide6", "websockets", "asyncio", "json", "socket",
            "struct", "threading", "time", "functools", "pathlib", "logging",
            "subprocess", "shutil", "math", "re", "random", "collections",
            "typing", "ctypes", "io", "enum", "inspect", "builtins",
            "cv2", "numpy", "PIL", "requests", "psutil", "cryptography",
            "urllib3", "chardet", "charset_normalizer", "certifi", "idna", "six",
            "ui", "utils", "remote_bridge", "main", "branding_patch"
        }
        def find_spec(self, name, path=None, target=None):
            root = name.split(".")[0]
            if root in self.PROTECTED:
                return None
            return ModuleSpec(name, _SpoofLoader(), is_package=True)

    if not any(isinstance(f, SpoofFinder) for f in sys.meta_path):
        sys.meta_path.append(SpoofFinder())

# Install the spoof finder so missing legacy dependencies never crash the UI
install_spoof_module_finder()


def _ensure_dependencies():
    """Ensure core Python packages (PySide6, OpenCV, NumPy, etc.) are installed."""
    checks = [
        ("PySide6", "PySide6"),
        ("websockets", "websockets>=13.0"),
        ("cv2", "opencv-python"),
        ("numpy", "numpy"),
        ("PIL", "pillow"),
        ("requests", "requests"),
        ("psutil", "psutil"),
    ]
    missing = []
    for mod_name, pkg_name in checks:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print(f"[*] Installing required components: {', '.join(missing)}...")
        for pkg in missing:
            subprocess.call([sys.executable, "-m", "pip", "install", pkg])

_ensure_dependencies()

project_root = os.path.dirname(os.path.abspath(__file__))
src_dir = os.path.join(project_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

os.chdir(src_dir)

if __name__ == "__main__":
    print(f"[+] Starting ClashBot AI Engine on Python {sys.version.split()[0]}...")
    try:
        from ui.branding_patch import apply_branding_patches
        apply_branding_patches()
    except Exception as e:
        print(f"[!] Notice: Branding patch initialization: {e}")
    from ui import gui
    gui.WINDOW_SETTINGS_APP = "ClashBotAI"
    gui.WINDOW_SETTINGS_ORG = "ClashBotAI"
    sys.exit(gui.run())
