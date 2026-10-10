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
    try:
        from license_manager import load_saved_key as _lm_load_saved_key
        k = _lm_load_saved_key()
        if k:
            return k
    except Exception:
        pass
    cfg_p = _project_root / "client_config.json"
    if cfg_p.exists():
        try:
            cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
            k = cfg.get("license_key") or cfg.get("key") or cfg.get("token")
            if k:
                return str(k).strip()
        except Exception:
            pass
    return ""

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
    global _ACTIVE_ENGINE, GLOBAL_STATS

    if stats is None:
        try:
            from stats import Stats
            stats = Stats()
        except Exception:
            pass

    GLOBAL_STATS = stats
    import sys
    if "main" in sys.modules and sys.modules["main"]:
        sys.modules["main"].GLOBAL_STATS = stats

    # 1. Load client configuration
    config_path = _project_root / "client_config.json"
    server_url = "https://clashbot.devtushar.uk"
    token = "CLASH-PRO-FRIEND"
    emulator_port = 5555

    if config_path.exists():
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                cfg_data = json.load(f)
                server_url = cfg_data.get("server_url", server_url)
                token = cfg_data.get("license_key") or cfg_data.get("token", token)
                emulator_port = int(cfg_data.get("emulator_port", emulator_port))
        except Exception as e:
            print(f"[!] Warning reading client_config.json: {e}")

    # 2. Gather accurate bot configuration from user settings
    profile_config = {}
    active_profile = "default"
    try:
        from profiles.profile_manager import ProfileManager
        pm = ProfileManager(None)
        enabled = pm.get_enabled_profiles()
        if enabled:
            active_profile = enabled[0]
    except Exception:
        pass

    # Step A: Load default templates first as baseline
    for candidate in [
        _project_root / "profiles" / "default" / "config.json",
        _project_root / "src" / "profiles" / "default" / "config.json",
    ]:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        profile_config.update(loaded)
            except Exception:
                pass

    # Step B: Load profile-specific config if active profile is custom
    try:
        from profiles.config_manager import ConfigManager
        cm = ConfigManager()
        if active_profile and active_profile != "default":
            active_data = cm.load(active_profile)
            if active_data:
                profile_config.update(active_data)
        for candidate in [
            _project_root / "profiles" / active_profile / "config.json",
            _project_root / "src" / "profiles" / active_profile / "config.json",
        ]:
            if candidate.exists() and active_profile != "default":
                try:
                    with open(candidate, "r", encoding="utf-8") as f:
                        loaded = json.load(f)
                        if isinstance(loaded, dict):
                            profile_config.update(loaded)
                except Exception:
                    pass
    except Exception:
        pass

    # Step C: Load user global settings (src/profiles/config.json) LAST.
    # In ClashBot AI UI, all tab controls save to global config when current_profile is None.
    # Therefore, global user settings represent the user's active UI choices and MUST OVERRIDE templates!
    try:
        from profiles.config_manager import ConfigManager
        cm = ConfigManager()
        global_data = cm.load(None)
        if global_data:
            profile_config.update(global_data)
    except Exception:
        pass

    for candidate in [
        _project_root / "profiles" / "config.json",
        _project_root / "src" / "profiles" / "config.json",
    ]:
        if candidate.exists():
            try:
                with open(candidate, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        profile_config.update(loaded)
            except Exception:
                pass

    # Step D: Read directly from active MainWindow widgets if the GUI is running
    try:
        from PySide6.QtWidgets import QApplication
        app = QApplication.instance()
        if app:
            for widget in app.topLevelWidgets():
                if widget.__class__.__name__ == "MainWindow":
                    # 1. Flush tab save methods to ensure latest UI inputs are saved
                    for updater in ["update_builder", "update_general", "update_attack_army", "update_donations", "update_upgrade_research"]:
                        if hasattr(widget, updater):
                            try:
                                getattr(widget, updater)()
                            except Exception:
                                pass
                    # 2. Synchronize active configuration from MainWindow's config_mgr
                    if hasattr(widget, "config_mgr") and widget.config_mgr:
                        try:
                            prof = getattr(widget, "current_profile", None)
                            mgr_data = widget.config_mgr.load(prof)
                            if isinstance(mgr_data, dict):
                                profile_config.update(mgr_data)
                        except Exception:
                            pass
                    # 3. Explicitly read direct checkbox states from UI
                    widget_mappings = {
                        "builder_enabled": "BUILDER_ENABLED",
                        "clan_capital_enable": "CLAN_CAPITAL",
                        "clan_capital_dump_gold_treasury_if_full": "CLAN_CAPITAL_DUMP_GOLD_TREASURY_IF_FULL",
                        "clan_games_enable": "CLAN_GAMES",
                        "cg_claim_rewards_for_gems": "CG_CLAIM_REWARDS_FOR_GEMS",
                        "war_attacks_enabled": "WAR_ATTACKS_ENABLED",
                        "war_one_attack_per_session": "WAR_ONE_ATTACK_PER_SESSION",
                        "war_request_cc": "WAR_REQUEST_CC",
                        "war_wait_cc": "WAR_WAIT_FOR_CC",
                        "request_leave_enabled": "REQUEST_AND_LEAVE_ENABLED",
                        "request_leave_join": "REQUEST_AND_LEAVE_JOIN",
                        "request_leave_leave": "REQUEST_AND_LEAVE_LEAVE",
                        "request_leave_set_army_slot1": "REQUEST_AND_LEAVE_SET_ARMY_SLOT1",
                        "request_leave_wait_cooldown": "REQUEST_AND_LEAVE_WAIT_FOR_COOLDOWN",
                        "home_upgrade_enabled": "HOME_UPGRADE_ENABLED",
                        "home_upgrade_perform_suggested": "HOME_UPGRADE_PERFORM_SUGGESTED",
                        "home_upgrade_suggested_rotate": "HOME_UPGRADE_SUGGESTED_ROTATE",
                        "home_upgrade_suggested_ignore_townhall": "HOME_UPGRADE_SUGGESTED_IGNORE_TOWNHALL",
                        "home_save_1_builder": "HOME_SAVE_1_BUILDER",
                        "home_research_enabled": "HOME_RESEARCH_ENABLED",
                        "home_research_perform_suggested": "HOME_RESEARCH_PERFORM_SUGGESTED",
                        "home_research_suggested_rotate": "HOME_RESEARCH_SUGGESTED_ROTATE",
                        "home_research_pets": "HOME_RESEARCH_PETS",
                        "home_research_use_1_gem_helper": "HOME_RESEARCH_USE_1_GEM_HELPER",
                        "bb_upgrade_enabled": "BB_UPGRADE_ENABLED",
                        "bb_upgrade_perform_suggested": "BB_UPGRADE_PERFORM_SUGGESTED",
                        "bb_upgrade_suggested_rotate": "BB_UPGRADE_SUGGESTED_ROTATE",
                        "bb_save_1_builder": "BB_SAVE_1_BUILDER",
                        "bb_research_enabled": "BB_RESEARCH_ENABLED",
                        "bb_research_perform_suggested": "BB_RESEARCH_PERFORM_SUGGESTED",
                        "bb_research_suggested_rotate": "BB_RESEARCH_SUGGESTED_ROTATE",
                        "upgrade_walls": "UPGRADE_WALLS",
                        "builderbase_upgrade_walls": "BUILDERBASE_UPGRADE_WALLS",
                        "builder_collect_gem_mine": "BUILDER_COLLECT_GEM_MINE",
                        "builder_collect_resources_first_run": "BUILDER_COLLECT_RESOURCES",
                        "builder_end_after_drop": "BUILDER_END_AFTER_TROOP_DROP",
                    }
                    for w_attr, cfg_key in widget_mappings.items():
                        if hasattr(widget, w_attr):
                            w_obj = getattr(widget, w_attr)
                            if hasattr(w_obj, "isChecked"):
                                profile_config[cfg_key] = bool(w_obj.isChecked())

                    # 4. Extract combo lists for upgrade and research slots
                    for combos_attr, cfg_key in [
                        ("home_upgrade_slot_combos", "HOME_UPGRADE_SLOTS"),
                        ("home_research_slot_combos", "HOME_RESEARCH_SLOTS"),
                        ("bb_upgrade_slot_combos", "BB_UPGRADE_SLOTS"),
                        ("bb_research_slot_combos", "BB_RESEARCH_SLOTS"),
                    ]:
                        if hasattr(widget, combos_attr):
                            combos = getattr(widget, combos_attr)
                            if isinstance(combos, list):
                                profile_config[cfg_key] = [
                                    str(c.currentData() or c.currentText() or "").strip()
                                    for c in combos if hasattr(c, "currentData")
                                ]
                    break
    except Exception as e:
        print(f"[!] Warning reading active MainWindow widgets: {e}")

    # Read user-selected emulator settings from profiles/config.json
    preferred_emulator = str(profile_config.get("EMULATOR_SELECTION", "")).strip().lower()
    preferred_instance = str(profile_config.get("EMULATOR_INSTANCE", "")).strip()
    cfg_port = profile_config.get("EMULATOR_PORT")
    if cfg_port:
        try:
            emulator_port = int(cfg_port)
        except (ValueError, TypeError):
            pass

    # If MuMu instance is specified and port was default 5555, compute exact instance ADB port
    if ("mumu" in preferred_emulator or "mumu" in preferred_instance.lower()) and (not cfg_port or emulator_port == 5555):
        inst_idx = 0
        if ":" in preferred_instance:
            try:
                inst_idx = int(preferred_instance.split(":")[1])
            except ValueError:
                inst_idx = 0
        emulator_port = 16384 + inst_idx * 32

    # 3. Instantiate client remote engine with user's selected instance and port
    engine = ClientRemoteEngine(
        server_url=server_url,
        token=token,
        emulator_port=emulator_port,
        preferred_emulator=preferred_emulator,
        preferred_instance=preferred_instance,
        stats=stats,
    )
    _ACTIVE_ENGINE = engine

    # Auto-detect running emulator port (prioritizing user-selected instance and port)
    engine.scan_emulator_port()

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
