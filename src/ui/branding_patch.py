# -*- coding: utf-8 -*-
"""
ClashBot AI - UI Branding & Titlebar Patch
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

This module patches Qt widgets and UI windows to ensure 100% consistent
ClashBot AI branding across all window titles, custom title bars, labels, and dialogs.
"""

import sys
import os
import re
import builtins

_BASE_PATCHED = False
_HOOK_INSTALLED = False
_PATCHED_CLASSES = set()

def clean_branding_text(text):
    """Clean any remaining AutoClash legacy strings to ClashBot AI."""
    if not isinstance(text, str):
        return text
    
    # Specific compound names & path replacements
    text = re.sub(r'AutoClash\s*Pro', 'ClashBot AI Pro', text, flags=re.IGNORECASE)
    text = re.sub(r'AutoClash\s*Mini', 'ClashBot AI Mini', text, flags=re.IGNORECASE)
    text = re.sub(r'Auto\s*Clash\s*Pro', 'ClashBot AI Pro', text, flags=re.IGNORECASE)
    text = re.sub(r'Auto\s*Clash\s*Mini', 'ClashBot AI Mini', text, flags=re.IGNORECASE)
    text = re.sub(r'\\AutoClash\\', r'\\ClashBot-AI\\', text, flags=re.IGNORECASE)
    text = re.sub(r'/AutoClash/', r'/ClashBot-AI/', text, flags=re.IGNORECASE)
    text = re.sub(r'Auto\s*Clash', 'ClashBot AI', text, flags=re.IGNORECASE)
    text = re.sub(r'AutoClash', 'ClashBot AI', text, flags=re.IGNORECASE)
    text = re.sub(r'autoclash', 'ClashBot AI', text, flags=re.IGNORECASE)
    return text


def _patch_main_window_class(cls):
    """Patch MainWindow methods."""
    if cls in _PATCHED_CLASSES:
        return
    _PATCHED_CLASSES.add(cls)

    _orig_update_window_title = cls._update_window_title
    def _patched_update_window_title(self, *args, **kwargs):
        try:
            _orig_update_window_title(self, *args, **kwargs)
        except Exception:
            pass
        cleaned = clean_branding_text(self.windowTitle())
        self.setWindowTitle(cleaned)
        if hasattr(self, "titlebar_title") and self.titlebar_title:
            try:
                self.titlebar_title.setText(cleaned)
            except Exception:
                pass
    cls._update_window_title = _patched_update_window_title

    _orig_init = cls.__init__
    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            self._update_window_title()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QLabel
            for lbl in self.findChildren(QLabel):
                t = lbl.text()
                if t and ('auto' in t.lower() or 'clash' in t.lower()):
                    c = clean_branding_text(t)
                    if c != t:
                        lbl.setText(c)
        except Exception:
            pass

        # Install Live Ping & Server Call telemetry badges into visible UI bars
        try:
            from PySide6.QtWidgets import QLabel, QFrame
            from PySide6.QtCore import QTimer

            # 1. Primary Badge: BottomBar (Center-right, adjacent to Status label)
            bottom_bar = getattr(self, "status", None).parent() if hasattr(self, "status") and self.status else None
            ping_badge = None
            if bottom_bar and bottom_bar.layout():
                ping_badge = QLabel("⚫ Cloud: Connecting... | clashbot.devtushar.uk")
                ping_badge.setObjectName("livePingBottomBadge")
                ping_badge.setStyleSheet(
                    "background: rgba(100, 116, 139, 0.15); "
                    "border: 1px solid rgba(100, 116, 139, 0.35); "
                    "border-radius: 6px; "
                    "color: #94a3b8; "
                    "font-family: 'Segoe UI', system-ui, sans-serif; "
                    "font-size: 11px; "
                    "font-weight: 600; "
                    "padding: 4px 12px; "
                    "margin-right: 8px;"
                )
                insert_idx = min(5, bottom_bar.layout().count() - 1)
                bottom_bar.layout().insertWidget(insert_idx, ping_badge)
                ping_badge.show()
                self._live_bottom_badge = ping_badge

            # 2. Companion Badge: TitleBar (Top-right, preceding window control buttons)
            title_bar = getattr(self, "title_bar", None)
            top_badge = None
            if title_bar and title_bar.layout():
                top_badge = QLabel("⚫ Connecting...")
                top_badge.setObjectName("livePingTopBadge")
                top_badge.setStyleSheet(
                    "background: rgba(100, 116, 139, 0.15); "
                    "border: 1px solid rgba(100, 116, 139, 0.35); "
                    "border-radius: 4px; "
                    "color: #94a3b8; "
                    "font-family: 'Segoe UI', system-ui, sans-serif; "
                    "font-size: 11px; "
                    "font-weight: 600; "
                    "padding: 2px 8px; "
                    "margin-right: 10px;"
                )
                insert_idx = min(2, title_bar.layout().count() - 1)
                title_bar.layout().insertWidget(insert_idx, top_badge)
                top_badge.show()
                self._live_top_badge = top_badge

            def _update_live_telemetry():
                try:
                    from remote_bridge.client_bridge_runner import ClientRemoteEngine
                    ms = getattr(ClientRemoteEngine, "LATEST_PING_MS", None)
                    server_host = getattr(ClientRemoteEngine, "ACTIVE_SERVER_HOST", "clashbot.devtushar.uk")
                    total_calls = getattr(ClientRemoteEngine, "TOTAL_SERVER_CALLS", 0)
                    latest_call = getattr(ClientRemoteEngine, "LATEST_SERVER_CALL", None)

                    call_str = ""
                    top_call_str = ""
                    if latest_call and isinstance(latest_call, dict):
                        cid = latest_call.get("call_id", total_calls)
                        act = latest_call.get("action", "CALL")
                        det = latest_call.get("details", "")
                        dur = latest_call.get("duration_ms", 0)
                        dur_text = f" [{dur}ms]" if dur > 0 else ""
                        if det:
                            det_short = det if len(det) <= 18 else det[:15] + "..."
                            call_str = f" | ⚡ Call #{cid}: {act} {det_short}{dur_text}"
                        else:
                            call_str = f" | ⚡ Call #{cid}: {act}{dur_text}"
                        top_call_str = f" | ⚡ #{cid} {act}"
                    elif total_calls > 0:
                        call_str = f" | ⚡ {total_calls} Calls"
                        top_call_str = f" | ⚡ #{total_calls}"

                    if ms is None or ms <= 0:
                        b_text = f"⚫ Cloud: Connecting... | {server_host}"
                        t_text = "⚫ Connecting..."
                        style_b = (
                            "background: rgba(100, 116, 139, 0.15); "
                            "border: 1px solid rgba(100, 116, 139, 0.35); "
                            "border-radius: 6px; "
                            "color: #94a3b8; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 4px 12px; "
                            "margin-right: 8px;"
                        )
                        style_t = (
                            "background: rgba(100, 116, 139, 0.15); "
                            "border: 1px solid rgba(100, 116, 139, 0.35); "
                            "border-radius: 4px; "
                            "color: #94a3b8; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 2px 8px; "
                            "margin-right: 10px;"
                        )
                    elif ms < 85:
                        b_text = f"🟢 Ping: {ms}ms | Cloud: {server_host}"
                        t_text = f"🟢 {ms}ms"
                        style_b = (
                            "background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 rgba(16, 185, 129, 0.18), stop:1 rgba(6, 182, 212, 0.18)); "
                            "border: 1px solid rgba(16, 185, 129, 0.5); "
                            "border-radius: 6px; "
                            "color: #10b981; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 4px 12px; "
                            "margin-right: 8px;"
                        )
                        style_t = (
                            "background: rgba(16, 185, 129, 0.18); "
                            "border: 1px solid rgba(16, 185, 129, 0.45); "
                            "border-radius: 4px; "
                            "color: #10b981; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 2px 8px; "
                            "margin-right: 10px;"
                        )
                    elif ms < 180:
                        b_text = f"🟡 Ping: {ms}ms | Cloud: {server_host}"
                        t_text = f"🟡 {ms}ms"
                        style_b = (
                            "background: rgba(245, 158, 11, 0.18); "
                            "border: 1px solid rgba(245, 158, 11, 0.5); "
                            "border-radius: 6px; "
                            "color: #f59e0b; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 4px 12px; "
                            "margin-right: 8px;"
                        )
                        style_t = (
                            "background: rgba(245, 158, 11, 0.18); "
                            "border: 1px solid rgba(245, 158, 11, 0.45); "
                            "border-radius: 4px; "
                            "color: #f59e0b; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 2px 8px; "
                            "margin-right: 10px;"
                        )
                    else:
                        b_text = f"🔴 Ping: {ms}ms (High Latency) | Cloud: {server_host}"
                        t_text = f"🔴 {ms}ms"
                        style_b = (
                            "background: rgba(239, 68, 68, 0.18); "
                            "border: 1px solid rgba(239, 68, 68, 0.5); "
                            "border-radius: 6px; "
                            "color: #ef4444; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 4px 12px; "
                            "margin-right: 8px;"
                        )
                        style_t = (
                            "background: rgba(239, 68, 68, 0.18); "
                            "border: 1px solid rgba(239, 68, 68, 0.45); "
                            "border-radius: 4px; "
                            "color: #ef4444; "
                            "font-family: 'Segoe UI', system-ui, sans-serif; "
                            "font-size: 11px; "
                            "font-weight: 600; "
                            "padding: 2px 8px; "
                            "margin-right: 10px;"
                        )

                    if ping_badge:
                        if ping_badge.text() != b_text:
                            ping_badge.setText(b_text)
                            ping_badge.setStyleSheet(style_b)
                        if ping_badge.isHidden():
                            ping_badge.show()

                    if top_badge:
                        if top_badge.text() != t_text:
                            top_badge.setText(t_text)
                            top_badge.setStyleSheet(style_t)
                        if top_badge.isHidden():
                            top_badge.show()
                except Exception:
                    pass

            timer = QTimer(self)
            timer.timeout.connect(_update_live_telemetry)
            timer.start(500)
            self._live_telemetry_timer = timer
            _update_live_telemetry()
        except Exception:
            pass
    cls.__init__ = _patched_init


    if hasattr(cls, "append_log"):
        _orig_append_log = cls.append_log
        def _patched_append_log(self, text, *args, **kwargs):
            if isinstance(text, str):
                text = clean_branding_text(text)
            return _orig_append_log(self, text, *args, **kwargs)
        cls.append_log = _patched_append_log


def _patch_mini_window_class(cls):
    """Patch MiniWindow methods."""
    if cls in _PATCHED_CLASSES:
        return
    _PATCHED_CLASSES.add(cls)

    _orig_update_window_title = cls._update_window_title
    def _patched_update_window_title(self, *args, **kwargs):
        try:
            _orig_update_window_title(self, *args, **kwargs)
        except Exception:
            pass
        cleaned = clean_branding_text(self.windowTitle())
        self.setWindowTitle(cleaned)
        if hasattr(self, "title_label") and self.title_label:
            try:
                self.title_label.setText(cleaned)
            except Exception:
                pass
    cls._update_window_title = _patched_update_window_title

    _orig_init = cls.__init__
    def _patched_init(self, *args, **kwargs):
        _orig_init(self, *args, **kwargs)
        try:
            self._update_window_title()
        except Exception:
            pass
        try:
            from PySide6.QtWidgets import QLabel
            for lbl in self.findChildren(QLabel):
                t = lbl.text()
                if t and ('auto' in t.lower() or 'clash' in t.lower()):
                    c = clean_branding_text(t)
                    if c != t:
                        lbl.setText(c)
        except Exception:
            pass

        # Install Live Ping & Server Call telemetry badge into MiniWindow
        try:
            from PySide6.QtWidgets import QLabel, QFrame
            from PySide6.QtCore import QTimer

            shell = self.findChild(QFrame, "MiniShell")
            mini_tb = shell.findChild(QFrame, "TitleBar") if shell else None
            if mini_tb and mini_tb.layout():
                m_badge = QLabel("⚫ Connecting...")
                m_badge.setObjectName("miniLivePingBadge")
                m_badge.setStyleSheet(
                    "background: rgba(100, 116, 139, 0.15); "
                    "border: 1px solid rgba(100, 116, 139, 0.35); "
                    "border-radius: 4px; "
                    "color: #94a3b8; "
                    "font-family: 'Segoe UI', system-ui, sans-serif; "
                    "font-size: 10px; "
                    "font-weight: 600; "
                    "padding: 2px 6px; "
                    "margin-right: 6px;"
                )
                insert_idx = max(0, mini_tb.layout().count() - 2)
                mini_tb.layout().insertWidget(insert_idx, m_badge)
                m_badge.show()
                self._mini_live_badge = m_badge

                def _update_mini_telemetry():
                    try:
                        from remote_bridge.client_bridge_runner import ClientRemoteEngine
                        ms = getattr(ClientRemoteEngine, "LATEST_PING_MS", None)
                        total_calls = getattr(ClientRemoteEngine, "TOTAL_SERVER_CALLS", 0)
                        latest_call = getattr(ClientRemoteEngine, "LATEST_SERVER_CALL", None)

                        call_str = ""
                        if latest_call and isinstance(latest_call, dict):
                            cid = latest_call.get("call_id", total_calls)
                            act = latest_call.get("action", "CALL")
                            call_str = f" | ⚡ #{cid}"
                        elif total_calls > 0:
                            call_str = f" | ⚡ #{total_calls}"

                        if ms is None or ms <= 0:
                            m_badge.setText("⚫ Offline")
                            m_badge.setStyleSheet("background: rgba(100, 116, 139, 0.15); border: 1px solid rgba(100, 116, 139, 0.35); border-radius: 4px; color: #94a3b8; font-size: 10px; font-weight: 600; padding: 2px 6px; margin-right: 6px;")
                        elif ms < 85:
                            m_badge.setText(f"🟢 {ms}ms")
                            m_badge.setStyleSheet("background: rgba(16, 185, 129, 0.18); border: 1px solid rgba(16, 185, 129, 0.45); border-radius: 4px; color: #10b981; font-size: 10px; font-weight: 600; padding: 2px 6px; margin-right: 6px;")
                        elif ms < 180:
                            m_badge.setText(f"🟡 {ms}ms")
                            m_badge.setStyleSheet("background: rgba(245, 158, 11, 0.18); border: 1px solid rgba(245, 158, 11, 0.45); border-radius: 4px; color: #f59e0b; font-size: 10px; font-weight: 600; padding: 2px 6px; margin-right: 6px;")
                        else:
                            m_badge.setText(f"🔴 {ms}ms")
                            m_badge.setStyleSheet("background: rgba(239, 68, 68, 0.18); border: 1px solid rgba(239, 68, 68, 0.45); border-radius: 4px; color: #ef4444; font-size: 10px; font-weight: 600; padding: 2px 6px; margin-right: 6px;")
                        if m_badge.isHidden():
                            m_badge.show()
                    except Exception:
                        pass

                m_timer = QTimer(self)
                m_timer.timeout.connect(_update_mini_telemetry)
                m_timer.start(500)
                self._mini_telemetry_timer = m_timer
                _update_mini_telemetry()
        except Exception:
            pass
    cls.__init__ = _patched_init

    if hasattr(cls, "append_log"):
        _orig_mini_append_log = cls.append_log
        def _patched_mini_append_log(self, text, *args, **kwargs):
            if isinstance(text, str):
                text = clean_branding_text(text)
            return _orig_mini_append_log(self, text, *args, **kwargs)
        cls.append_log = _patched_mini_append_log


def _patch_emulator_lifecycle():
    """Ensure bot engine never crashes with FileNotFoundError on systems without BlueStacks/executables."""
    try:
        import startup
        def _safe_ensure(*args, **kwargs):
            try:
                if hasattr(startup, "_orig_ensure_emulator"):
                    return startup._orig_ensure_emulator(*args, **kwargs)
            except Exception as e:
                print(f"[*] Notice: Emulator auto-launch bypassed ({e}). Connecting via ADB...")
            return None

        if not hasattr(startup, "_orig_ensure_emulator"):
            startup._orig_ensure_emulator = startup.ensure_emulator_config_ready

        startup.ensure_emulator_config_ready = _safe_ensure
        startup.ensure_bluestacks_instance_running = lambda *args, **kwargs: True
        startup.ensure_ldplayer_instance_running = lambda *args, **kwargs: True
        startup.ensure_mumu_instance_running = lambda *args, **kwargs: True
        startup.enforce_bluestacks_config = lambda *args, **kwargs: None
        startup.enforce_emulator_config = lambda *args, **kwargs: None
        startup.enforce_ldplayer_config = lambda *args, **kwargs: None
        startup.enforce_mumu_config = lambda *args, **kwargs: None
        startup.launch_emulator = lambda *args, **kwargs: True
        startup.restart_emulator_instance = lambda *args, **kwargs: True
        startup.stop_bluestacks_instance = lambda *args, **kwargs: True
        startup.stop_emulator = lambda *args, **kwargs: True
    except Exception:
        pass

    try:
        import recovery
        recovery.restart_emulator_instance = lambda *args, **kwargs: True
        recovery.stop_emulator = lambda *args, **kwargs: True
    except Exception:
        pass

    try:
        for mod_name in ("main", "src.main"):
            if mod_name in sys.modules:
                m = sys.modules[mod_name]
                if hasattr(m, "ensure_emulator_config_ready"):
                    m.ensure_emulator_config_ready = lambda *args, **kwargs: None
    except Exception:
        pass


def _patch_bot_worker(mod):
    """Patch TeeStream and BotWorker to ensure crash-free execution."""
    if hasattr(mod, "TeeStream"):
        cls = mod.TeeStream
        if cls not in _PATCHED_CLASSES:
            _PATCHED_CLASSES.add(cls)
            _orig_write = cls.write
            def _patched_write(self, data):
                if isinstance(data, str):
                    data = clean_branding_text(data)
                return _orig_write(self, data)
            cls.write = _patched_write

    if hasattr(mod, "BotWorker"):
        cls = mod.BotWorker
        if cls not in _PATCHED_CLASSES:
            _PATCHED_CLASSES.add(cls)
            _orig_run = cls.run
            def _patched_run(self, *args, **kwargs):
                _patch_emulator_lifecycle()
                return _orig_run(self, *args, **kwargs)
            cls.run = _patched_run


def _install_import_hook():
    """Install import hook to auto-patch window classes whenever modules are loaded."""
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return
    _HOOK_INSTALLED = True

    _orig_import = builtins.__import__
    def _branding_import(name, globals=None, locals=None, fromlist=(), level=0):
        mod = _orig_import(name, globals, locals, fromlist, level)
        try:
            for mod_name in ("ui.main_window", "main_window"):
                if mod_name in sys.modules:
                    m = sys.modules[mod_name]
                    if hasattr(m, "MainWindow"):
                        _patch_main_window_class(m.MainWindow)
            for mod_name in ("ui.mini_window", "mini_window"):
                if mod_name in sys.modules:
                    m = sys.modules[mod_name]
                    if hasattr(m, "MiniWindow"):
                        _patch_mini_window_class(m.MiniWindow)
            for mod_name in ("ui.bot_worker", "bot_worker"):
                if mod_name in sys.modules:
                    _patch_bot_worker(sys.modules[mod_name])
            if "main" in sys.modules:
                m = sys.modules["main"]
                if hasattr(m, "ensure_emulator_config_ready"):
                    m.ensure_emulator_config_ready = lambda *args, **kwargs: None
        except Exception:
            pass
        return mod
    builtins.__import__ = _branding_import


def apply_branding_patches():
    """Apply branding monkey-patches to Qt widgets and window classes."""
    global _BASE_PATCHED
    
    _patch_emulator_lifecycle()
    _install_import_hook()

    if not _BASE_PATCHED:
        _BASE_PATCHED = True
        try:
            from PySide6.QtWidgets import (
                QWidget, QLabel, QAbstractButton, QGroupBox
            )
            from PySide6.QtCore import QCoreApplication

            # 1. Patch QWidget.setWindowTitle
            _orig_setWindowTitle = QWidget.setWindowTitle
            def _patched_setWindowTitle(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_setWindowTitle(self, *args, **kwargs)
            QWidget.setWindowTitle = _patched_setWindowTitle

            # 2. Patch QLabel.setText and QLabel.__init__
            _orig_lbl_setText = QLabel.setText
            def _patched_lbl_setText(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_lbl_setText(self, *args, **kwargs)
            QLabel.setText = _patched_lbl_setText

            _orig_lbl_init = QLabel.__init__
            def _patched_lbl_init(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                if 'text' in kwargs and isinstance(kwargs['text'], str):
                    kwargs['text'] = clean_branding_text(kwargs['text'])
                return _orig_lbl_init(self, *args, **kwargs)
            QLabel.__init__ = _patched_lbl_init

            # 3. Patch QAbstractButton.setText and __init__
            _orig_btn_setText = QAbstractButton.setText
            def _patched_btn_setText(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_btn_setText(self, *args, **kwargs)
            QAbstractButton.setText = _patched_btn_setText

            _orig_btn_init = QAbstractButton.__init__
            def _patched_btn_init(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                if 'text' in kwargs and isinstance(kwargs['text'], str):
                    kwargs['text'] = clean_branding_text(kwargs['text'])
                return _orig_btn_init(self, *args, **kwargs)
            QAbstractButton.__init__ = _patched_btn_init

            # 4. Patch QGroupBox.setTitle and __init__
            _orig_gb_setTitle = QGroupBox.setTitle
            def _patched_gb_setTitle(self, *args, **kwargs):
                if args and isinstance(args[0], str):
                    args = (clean_branding_text(args[0]),) + args[1:]
                return _orig_gb_setTitle(self, *args, **kwargs)
            QGroupBox.setTitle = _patched_gb_setTitle

            # 5. Patch QCoreApplication.setApplicationName & QApplication.setApplicationName
            _orig_setAppName = QCoreApplication.setApplicationName
            def _patched_setAppName(*args, **kwargs):
                str_arg = args[-1] if args else "ClashBot AI"
                cleaned = clean_branding_text(str_arg) if isinstance(str_arg, str) else str_arg
                return _orig_setAppName(cleaned)
            QCoreApplication.setApplicationName = staticmethod(_patched_setAppName)
            QApplication.setApplicationName = staticmethod(_patched_setAppName)

        except Exception as e:
            pass

    # Eagerly patch MainWindow and MiniWindow
    try:
        from ui import main_window
        _patch_main_window_class(main_window.MainWindow)
    except Exception:
        pass

    try:
        from ui import mini_window
        _patch_mini_window_class(mini_window.MiniWindow)
    except Exception:
        pass

    try:
        from ui import bot_worker
        _patch_bot_worker(bot_worker)
    except Exception:
        pass

    # Patch gui.set_windows_app_user_model_id if available
    try:
        from ui import gui
        def _patched_app_id():
            if sys.platform == "win32":
                try:
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("ClashBotAI.App.2.1.5")
                except Exception:
                    pass
        gui.set_windows_app_user_model_id = _patched_app_id
    except Exception:
        pass

    _patch_emulator_lifecycle()


