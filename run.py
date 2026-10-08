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

def _ensure_dependencies():
    """Ensure all required Python packages (including OpenCV, PySide6, etc.) are installed."""
    missing = []
    checks = [
        ("PySide6", "PySide6>=6.5.0"),
        ("websockets", "websockets>=13.0"),
        ("cv2", "opencv-python>=4.8.0"),
        ("numpy", "numpy>=1.24.0"),
        ("PIL", "pillow>=9.5.0"),
        ("ppadb", "pure-python-adb>=0.3.0"),
        ("requests", "requests>=2.31.0"),
        ("psutil", "psutil>=5.9.0"),
        ("cryptography", "cryptography>=41.0.0"),
    ]
    for mod_name, pkg_name in checks:
        try:
            __import__(mod_name)
        except ImportError:
            missing.append(pkg_name)

    if missing:
        print(f"[*] Missing required components: {', '.join(missing)}")
        print("[*] Automatically installing missing components via pip...")
        req_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "requirements.txt")
        if os.path.isfile(req_file):
            cmd = [sys.executable, "-m", "pip", "install", "-r", req_file]
        else:
            cmd = [sys.executable, "-m", "pip", "install"] + missing
        res = subprocess.call(cmd)
        if res != 0:
            print("[-] Warning: Some components failed to install via pip.")

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
