# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Remote Engine Entry Point
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar

This module serves as the client engine when running on a remote laptop.
It connects the local PySide6 UI and local Android emulator to the Cloud Engine Server.
All proprietary attack algorithms, OpenCV templates, and tactical FSM planners execute
securely on the server, while the client displays live combat telemetry and controls.
"""

from __future__ import annotations

import asyncio
import json
import os
import sys
from pathlib import Path

# Add project root to sys.path
_current_dir = Path(__file__).resolve().parent
_project_root = _current_dir.parent
if str(_project_root) not in sys.path:
    sys.path.insert(0, str(_project_root))

from remote_bridge.client_bridge_runner import ClientRemoteEngine

_ACTIVE_ENGINE: ClientRemoteEngine | None = None


# Stubs for compatibility with PyArmor-protected UI files
def stop_license_heartbeat_for_cleanup():
    global _ACTIVE_ENGINE
    if _ACTIVE_ENGINE:
        _ACTIVE_ENGINE.stop()

def start_license_heartbeat():
    pass

def ensure_emulator_config_ready():
    pass

def load_saved_key():
    return "CLIENT-COMMUNITY-LICENSE-2026"

def get_license_error_message():
    return ""

class BotControl:
    running = True
    paused = False

class Vision:
    pass

class Stats:
    pass

GLOBAL_STATS = None
GLOBAL_VISION = None


def main(stats):
    """Main worker entry point invoked by ui.bot_worker.BotWorker.run()."""
    global _ACTIVE_ENGINE

    # 1. Load client configuration
    config_path = _project_root / "client_config.json"
    server_url = "https://holmes-recruiting-heat-bigger.trycloudflare.com"
    token = "clashbot-secret-key-2026"
    emulator_port = 5555

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
                server_url = cfg_data.get("server_url", server_url)
                token = cfg_data.get("token", token)
                emulator_port = int(cfg_data.get("emulator_port", emulator_port))
        except Exception as e:
            print(f"[!] Warning reading client_config.json: {e}")

    # 2. Load village/bot configuration from profiles
    profile_config = {}
    profile_path = _project_root / "src" / "profiles" / "config.json"
    if not profile_path.exists():
        profile_path = _project_root / "profiles" / "config.json"
    if profile_path.exists():
        try:
            with open(profile_path, "r", encoding="utf-8") as f:
                profile_config = json.load(f)
        except Exception:
            pass

    # 3. Instantiate client remote engine
    engine = ClientRemoteEngine(
        server_url=server_url,
        token=token,
        emulator_port=emulator_port,
        stats=stats,
    )
    _ACTIVE_ENGINE = engine

    # Auto-detect running emulator port
    active_port = engine.scan_emulator_port()
    if active_port is None:
        print("[!] ERROR: Cannot start bot - No active Android emulator detected!")
        print("[*] Please launch BlueStacks, LDPlayer, or MuMu (with ADB enabled), then click Start.")
        _ACTIVE_ENGINE = None
        return

    # 4. Run async event loop
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    engine.loop = loop

    try:
        loop.run_until_complete(engine.run(profile_config))
    except KeyboardInterrupt:
        pass
    finally:
        loop.close()
        _ACTIVE_ENGINE = None


def __getattr__(name):
    """Fallback catch-all to ensure binary UI wrappers never fail on missing attributes."""
    return lambda *args, **kwargs: None
