# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Remote Engine Bridge
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar

Zero Bot Logic on Client:
All combat decision making, army deployment, and village farming logic execute
remotely on the Cloud Server. This client stub connects local emulator capture
and GUI telemetry to the server session.
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

# Ensure remote_bridge is accessible
_src_dir = Path(__file__).resolve().parent
_bundle_root = _src_dir.parent
if str(_bundle_root) not in sys.path:
    sys.path.insert(0, str(_bundle_root))

from remote_bridge.client_main_stub import (
    main,
    BotControl,
    Vision,
    Stats,
    GLOBAL_STATS,
    GLOBAL_VISION,
    ensure_emulator_config_ready,
    stop_license_heartbeat_for_cleanup,
    start_license_heartbeat,
)

__all__ = [
    "main",
    "BotControl",
    "Vision",
    "Stats",
    "GLOBAL_STATS",
    "GLOBAL_VISION",
    "ensure_emulator_config_ready",
    "stop_license_heartbeat_for_cleanup",
    "start_license_heartbeat",
]
