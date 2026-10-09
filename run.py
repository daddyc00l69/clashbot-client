# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Application Launcher
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar

Zero Local Bot Logic:
The client runs the full ClashBot AI Main Interface (tabs, village configs, army planners,
trophy goals, loot filters). When botting is active, all tactical attack algorithms, vision
intelligence, and farming execution are processed on the Cloud Server.
"""
import os
import subprocess
import sys

bundle_root = os.path.dirname(os.path.abspath(__file__))
if bundle_root not in sys.path:
    sys.path.insert(0, bundle_root)

src_dir = os.path.join(bundle_root, "src")
if src_dir not in sys.path:
    sys.path.insert(0, src_dir)

os.chdir(src_dir)

if __name__ == "__main__":
    # 1. Run Login & License Activation Dialog with HWID Verification in a dedicated subprocess
    res = subprocess.call([sys.executable, "-m", "remote_bridge.login_dialog"], cwd=bundle_root)
    if res != 0:
        print("[-] Login cancelled by user. Exiting.")
        sys.exit(0)

    print("[+] Starting ClashBot AI Main Interface...")
    try:
        from ui.branding_patch import apply_branding_patches
        apply_branding_patches()
    except Exception as e:
        print(f"[!] Notice: Branding patch initialization: {e}")

    from ui import gui
    gui.WINDOW_SETTINGS_APP = "ClashBotAI"
    gui.WINDOW_SETTINGS_ORG = "ClashBotAI"
    sys.exit(gui.run())
