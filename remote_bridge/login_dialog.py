# -*- coding: utf-8 -*-
"""ClashBot AI - Client Authentication & Launcher Window.

Modern AAA gaming-style PySide6 Launch Dialog with hardware identification (HWID).
Features:
- Dark glassmorphism obsidian theme with glowing cyan & electric accents.
- Frameless window with custom draggable titlebar.
- Compact hardware fingerprint (HWID) badge with instant clipboard copy.
- Streamlined License Key activation with Enter-key submission.
- Collapsible advanced network / server settings.
- Seamless auto-launch option and live status telemetry.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from remote_bridge.hwid import get_hwid
from remote_bridge.protocol import MSG_AUTH, MSG_AUTH_FAIL, MSG_AUTH_OK, pack_frame


def resolve_icon_pixmap() -> QPixmap | None:
    """Locate the ClashBot AI brand icon across common project structures."""
    curr = Path(__file__).resolve().parent
    candidates = [
        curr.parent / "src" / "assets" / "icon.png",
        curr.parent / "assets" / "icon.png",
        curr / "assets" / "icon.png",
        Path.cwd() / "src" / "assets" / "icon.png",
        Path.cwd() / "assets" / "icon.png",
    ]
    for c in candidates:
        if c.exists():
            pix = QPixmap(str(c))
            if not pix.isNull():
                return pix.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
    return None


def get_config_path() -> Path:
    """Find the client configuration JSON file."""
    curr = Path(__file__).resolve().parent
    candidates = [
        curr.parent / "client_config.json",
        curr / "client_config.json",
        Path(os.getcwd()) / "client_config.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_client_config() -> dict:
    """Load configuration from client_config.json with resilient defaults."""
    p = get_config_path()
    if p.exists():
        try:
            with open(p, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "server_url": "ws://110.227.184.49:8765",
        "token": "CLASH-VIP-2026",
        "license_key": "CLASH-VIP-2026",
        "remember_key": True,
        "auto_login": False,
        "emulator_port": 5555,
        "bot_speed": "balanced",
    }


def save_client_config(cfg: dict) -> None:
    """Persist client configuration."""
    p = get_config_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[!] Warning saving client_config.json: {e}")


class VerifyWorker(QThread):
    """Background worker to verify license & HWID over WebSocket without UI freeze."""

    finished = Signal(bool, str, str)  # is_valid, message, user_name

    def __init__(self, server_url: str, key: str, hwid: str) -> None:
        super().__init__()
        self.server_url = server_url
        self.key = key
        self.hwid = hwid

    def run(self) -> None:
        import asyncio
        import websockets

        async def _test_auth():
            ws_url = self.server_url.strip()
            if ws_url.startswith("https://"):
                ws_url = "wss://" + ws_url[8:]
            elif ws_url.startswith("http://"):
                ws_url = "ws://" + ws_url[7:]
            elif not (ws_url.startswith("ws://") or ws_url.startswith("wss://")):
                ws_url = f"ws://{ws_url}"
            if not ws_url.endswith("/ws") and not ws_url.endswith("/"):
                ws_url = f"{ws_url}/ws"

            auth_payload = json.dumps({
                "key": self.key,
                "token": self.key,
                "hwid": self.hwid,
                "version": "2.0.0",
            }).encode("utf-8")

            try:
                async with websockets.connect(
                    ws_url,
                    open_timeout=4.0,
                    ping_interval=None,
                ) as ws:
                    await ws.send(pack_frame(MSG_AUTH, auth_payload))
                    resp = await asyncio.wait_for(ws.recv(), timeout=5.0)

                    if isinstance(resp, bytes) and len(resp) >= 5:
                        msg_type = resp[4]
                        payload = resp[5:].decode("utf-8", errors="ignore")

                        data = {}
                        try:
                            data = json.loads(payload)
                        except Exception:
                            pass

                        if msg_type == MSG_AUTH_OK:
                            user = data.get("user", "User") if isinstance(data, dict) else "User"
                            msg = data.get("message", "License Verified") if isinstance(data, dict) else payload
                            return True, msg or "License Verified", user
                        else:
                            err_msg = data.get("error", payload) if isinstance(data, dict) else payload
                            return False, err_msg or "Authentication failed.", ""
                    return False, "Unexpected response from server.", ""
            except asyncio.TimeoutError:
                return False, "Connection timed out. Server did not respond.", ""
            except Exception as e:
                err = str(e)
                if "10061" in err or "refused" in err.lower():
                    return False, "Connection refused: Server is offline or port is closed.", ""
                return False, f"Connection error: {err}", ""

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ok, msg, user = loop.run_until_complete(_test_auth())
            loop.close()
            self.finished.emit(ok, msg, user)
        except Exception as e:
            self.finished.emit(False, str(e), "")


class ClashBotLoginDialog(QDialog):
    """Modern AAA Gaming Launcher Dialog for ClashBot AI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = load_client_config()
        self.hwid = get_hwid()
        self.worker: VerifyWorker | None = None
        self.drag_position = QPoint()

        self.setWindowTitle("ClashBot AI — Client Launcher")
        self.setFixedSize(460, 560)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.Dialog)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._init_ui()

        # Handle auto-login if configured
        if self.cfg.get("auto_login", False) and self.key_edit.text().strip():
            QTimer.singleShot(250, self._start_verification)

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_position = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()

    def mouseMoveEvent(self, event):
        if event.buttons() == Qt.LeftButton:
            self.move(event.globalPosition().toPoint() - self.drag_position)
            event.accept()

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            self.reject()
        elif event.key() in (Qt.Key_Return, Qt.Key_Enter):
            self._start_verification()
        else:
            super().keyPressEvent(event)

    def _init_ui(self) -> None:
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(8, 8, 8, 8)

        # Main Obsidian Card Container
        self.card = QFrame(self)
        self.card.setObjectName("mainCard")
        self.card.setStyleSheet("""
            QFrame#mainCard {
                background-color: #0A0D14;
                border: 1px solid #1E293B;
                border-radius: 14px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(22, 16, 22, 20)
        card_layout.setSpacing(12)

        # 1. Custom Draggable Title Bar
        titlebar = QHBoxLayout()
        titlebar.setContentsMargins(0, 0, 0, 0)

        badge_dot = QLabel("●")
        badge_dot.setStyleSheet("color: #38BDF8; font-size: 10px; margin-right: 2px;")
        titlebar.addWidget(badge_dot)

        top_title = QLabel("CLASHBOT AI")
        top_title.setStyleSheet("font-family: 'Segoe UI', system-ui; font-size: 11px; font-weight: 800; color: #94A3B8; letter-spacing: 1px;")
        titlebar.addWidget(top_title)

        ver_badge = QLabel("PRO v2.0")
        ver_badge.setStyleSheet("background-color: #161F30; color: #38BDF8; font-size: 9px; font-weight: 700; padding: 2px 6px; border-radius: 4px; border: 1px solid #1E293B;")
        titlebar.addWidget(ver_badge)

        titlebar.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(24, 24)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748B;
                font-size: 13px;
                font-weight: bold;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #EF4444;
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.reject)
        titlebar.addWidget(close_btn)
        card_layout.addLayout(titlebar)

        # 2. Hero Brand Header
        hero = QVBoxLayout()
        hero.setSpacing(4)
        hero.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        pix = resolve_icon_pixmap()
        if pix:
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("⚔️")
            icon_lbl.setStyleSheet("font-size: 32px;")
        icon_lbl.setAlignment(Qt.AlignCenter)
        hero.addWidget(icon_lbl)

        brand_lbl = QLabel("CLASHBOT AI")
        brand_lbl.setAlignment(Qt.AlignCenter)
        brand_lbl.setStyleSheet("""
            font-family: 'Segoe UI', system-ui;
            font-size: 18px;
            font-weight: 800;
            color: #F8FAFC;
            letter-spacing: 1.5px;
            margin-top: 2px;
        """)
        hero.addWidget(brand_lbl)

        sub_lbl = QLabel("Autonomous Tactical Intelligence & Cloud Engine")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("font-size: 11px; color: #64748B; font-weight: 500;")
        hero.addWidget(sub_lbl)

        card_layout.addLayout(hero)

        # 3. Compact Hardware ID (HWID) Chip
        hwid_chip = QFrame()
        hwid_chip.setObjectName("hwidChip")
        hwid_chip.setStyleSheet("""
            QFrame#hwidChip {
                background-color: #101522;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        hwid_layout = QHBoxLayout(hwid_chip)
        hwid_layout.setContentsMargins(12, 6, 12, 6)
        hwid_layout.setSpacing(8)

        hwid_tag = QLabel("🔒 HWID:")
        hwid_tag.setStyleSheet("font-size: 10px; font-weight: 700; color: #64748B; letter-spacing: 0.5px; border: none; background: transparent;")
        hwid_layout.addWidget(hwid_tag)

        self.hwid_val = QLabel(self.hwid)
        self.hwid_val.setStyleSheet("font-family: 'Consolas', monospace; font-size: 11px; font-weight: bold; color: #38BDF8; border: none; background: transparent;")
        hwid_layout.addWidget(self.hwid_val)

        hwid_layout.addStretch()

        self.copy_btn = QPushButton("📋 Copy")
        self.copy_btn.setCursor(Qt.PointingHandCursor)
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A2234;
                border: 1px solid #28354D;
                border-radius: 4px;
                color: #94A3B8;
                font-size: 10px;
                font-weight: 600;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #243048;
                color: #FFFFFF;
            }
        """)
        self.copy_btn.clicked.connect(self._copy_hwid)
        hwid_layout.addWidget(self.copy_btn)

        card_layout.addWidget(hwid_chip)

        # 4. Form Card (Key Input + Options)
        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_card.setStyleSheet("""
            QFrame#formCard {
                background-color: #101522;
                border: 1px solid #1E293B;
                border-radius: 10px;
            }
        """)
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(14, 12, 14, 12)
        form_layout.setSpacing(10)

        key_header = QHBoxLayout()
        key_lbl = QLabel("🔑 LICENSE KEY")
        key_lbl.setStyleSheet("font-size: 10px; font-weight: 700; color: #94A3B8; letter-spacing: 0.8px; border: none; background: transparent;")
        key_header.addWidget(key_lbl)
        key_header.addStretch()
        form_layout.addLayout(key_header)

        saved_key = self.cfg.get("license_key") or self.cfg.get("token") or "CLASH-VIP-2026"
        self.key_edit = QLineEdit(saved_key)
        self.key_edit.setPlaceholderText("Enter license key (e.g. CLASH-VIP-2026)")
        self.key_edit.setStyleSheet("""
            QLineEdit {
                background-color: #07090E;
                border: 1px solid #28354D;
                border-radius: 6px;
                color: #F8FAFC;
                font-family: 'Consolas', monospace;
                font-size: 13px;
                font-weight: bold;
                padding: 8px 12px;
                letter-spacing: 0.5px;
            }
            QLineEdit:focus {
                border: 1.5px solid #38BDF8;
                background-color: #0B111D;
            }
        """)
        form_layout.addWidget(self.key_edit)

        # Checkboxes row
        opts_layout = QHBoxLayout()
        opts_layout.setSpacing(14)

        self.rem_cb = QCheckBox("Remember key")
        self.rem_cb.setChecked(self.cfg.get("remember_key", True))
        self.rem_cb.setStyleSheet("""
            QCheckBox {
                color: #94A3B8;
                font-size: 11px;
                spacing: 6px;
            }
            QCheckBox::indicator {
                width: 14px;
                height: 14px;
                border-radius: 3px;
                border: 1px solid #334155;
                background: #07090E;
            }
            QCheckBox::indicator:checked {
                background: #38BDF8;
                border: 1px solid #38BDF8;
            }
        """)
        opts_layout.addWidget(self.rem_cb)

        self.auto_cb = QCheckBox("Auto-launch on startup")
        self.auto_cb.setChecked(self.cfg.get("auto_login", False))
        self.auto_cb.setStyleSheet(self.rem_cb.styleSheet())
        opts_layout.addWidget(self.auto_cb)

        opts_layout.addStretch()
        form_layout.addLayout(opts_layout)

        card_layout.addWidget(form_card)

        # 5. Collapsible Advanced Connection Settings
        self.adv_btn = QPushButton("⚙️ Advanced Network Settings ▾")
        self.adv_btn.setCursor(Qt.PointingHandCursor)
        self.adv_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                border: none;
                color: #64748B;
                font-size: 10px;
                font-weight: 600;
                text-align: left;
                padding: 2px 4px;
            }
            QPushButton:hover {
                color: #94A3B8;
            }
        """)
        self.adv_btn.clicked.connect(self._toggle_advanced)
        card_layout.addWidget(self.adv_btn)

        self.adv_frame = QFrame()
        self.adv_frame.setObjectName("advFrame")
        self.adv_frame.setVisible(False)
        self.adv_frame.setStyleSheet("""
            QFrame#advFrame {
                background-color: #0E131F;
                border: 1px solid #1E293B;
                border-radius: 8px;
            }
        """)
        adv_layout = QVBoxLayout(self.adv_frame)
        adv_layout.setContentsMargins(12, 10, 12, 10)
        adv_layout.setSpacing(6)

        url_lbl = QLabel("Cloud Server Endpoint:")
        url_lbl.setStyleSheet("font-size: 10px; color: #94A3B8; font-weight: 600; border: none; background: transparent;")
        adv_layout.addWidget(url_lbl)

        saved_url = self.cfg.get("server_url") or "ws://110.227.184.49:8765"
        self.url_edit = QLineEdit(saved_url)
        self.url_edit.setPlaceholderText("ws://110.227.184.49:8765")
        self.url_edit.setStyleSheet("""
            QLineEdit {
                background-color: #07090E;
                border: 1px solid #28354D;
                border-radius: 5px;
                color: #CBD5E1;
                font-size: 11px;
                padding: 5px 8px;
            }
            QLineEdit:focus {
                border: 1px solid #38BDF8;
            }
        """)
        adv_layout.addWidget(self.url_edit)
        card_layout.addWidget(self.adv_frame)

        card_layout.addStretch()

        # 6. Status Feedback Banner
        self.status_banner = QLabel("Ready • Enter your license key to activate.")
        self.status_banner.setAlignment(Qt.AlignCenter)
        self.status_banner.setWordWrap(True)
        self.status_banner.setFixedHeight(34)
        self.status_banner.setStyleSheet("""
            background-color: #0E131F;
            border: 1px solid #1A2333;
            border-radius: 6px;
            color: #64748B;
            font-size: 11px;
            font-weight: 500;
            padding: 6px 10px;
        """)
        card_layout.addWidget(self.status_banner)

        # 7. Hero Action Button
        self.launch_btn = QPushButton("⚡ LAUNCH CLASHBOT")
        self.launch_btn.setCursor(Qt.PointingHandCursor)
        self.launch_btn.setFixedHeight(42)
        self.launch_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284C7, stop:0.5 #2563EB, stop:1 #4F46E5);
                border: none;
                border-radius: 8px;
                color: #FFFFFF;
                font-family: 'Segoe UI', system-ui;
                font-size: 13px;
                font-weight: 800;
                letter-spacing: 0.8px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369A1, stop:0.5 #1D4ED8, stop:1 #4338CA);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #075985, stop:0.5 #1E40AF, stop:1 #3730A3);
            }
            QPushButton:disabled {
                background: #1E293B;
                color: #64748B;
            }
        """)
        self.launch_btn.clicked.connect(self._start_verification)
        card_layout.addWidget(self.launch_btn)

        outer_layout.addWidget(self.card)

    def _copy_hwid(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hwid)
        self.copy_btn.setText("✓ Copied")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #064E3B;
                border: 1px solid #059669;
                border-radius: 4px;
                color: #34D399;
                font-size: 10px;
                font-weight: 700;
                padding: 3px 8px;
            }
        """)
        QTimer.singleShot(1600, self._reset_copy_btn)

    def _reset_copy_btn(self) -> None:
        self.copy_btn.setText("📋 Copy")
        self.copy_btn.setStyleSheet("""
            QPushButton {
                background-color: #1A2234;
                border: 1px solid #28354D;
                border-radius: 4px;
                color: #94A3B8;
                font-size: 10px;
                font-weight: 600;
                padding: 3px 8px;
            }
            QPushButton:hover {
                background-color: #243048;
                color: #FFFFFF;
            }
        """)

    def _toggle_advanced(self) -> None:
        visible = not self.adv_frame.isVisible()
        self.adv_frame.setVisible(visible)
        if visible:
            self.adv_btn.setText("⚙️ Advanced Network Settings ▴")
            self.setFixedSize(460, 620)
        else:
            self.adv_btn.setText("⚙️ Advanced Network Settings ▾")
            self.setFixedSize(460, 560)

    def _set_status(self, text: str, color_hex: str) -> None:
        self.status_banner.setText(text)
        r = int(color_hex[1:3], 16)
        g = int(color_hex[3:5], 16)
        b = int(color_hex[5:7], 16)
        self.status_banner.setStyleSheet(f"""
            background-color: rgba({r}, {g}, {b}, 0.12);
            border: 1px solid {color_hex};
            border-radius: 6px;
            color: {color_hex};
            font-size: 11px;
            font-weight: 600;
            padding: 6px 10px;
        """)

    def _start_verification(self) -> None:
        key = self.key_edit.text().strip()
        url = self.url_edit.text().strip()

        if not key:
            self._set_status("Please enter a valid license key.", "#EF4444")
            return
        if not url:
            self._set_status("Please enter a valid server URL.", "#EF4444")
            return

        self.launch_btn.setEnabled(False)
        self.launch_btn.setText("⏳ VERIFYING LICENSE...")
        self._set_status("Connecting to Cloud Engine & validating HWID...", "#38BDF8")

        self.worker = VerifyWorker(server_url=url, key=key, hwid=self.hwid)
        self.worker.finished.connect(self._on_verification_finished)
        self.worker.start()

    @Slot(bool, str, str)
    def _on_verification_finished(self, is_valid: bool, message: str, user: str) -> None:
        self.launch_btn.setEnabled(True)
        self.launch_btn.setText("⚡ LAUNCH CLASHBOT")

        if is_valid:
            welcome = f"Welcome, {user}!" if user else "Activation Successful!"
            self._set_status(f"🟢 {message} ({welcome})", "#10B981")

            # Save credentials & options
            key = self.key_edit.text().strip()
            url = self.url_edit.text().strip()
            rem = self.rem_cb.isChecked()
            auto = self.auto_cb.isChecked()

            self.cfg["server_url"] = url
            self.cfg["license_key"] = key
            self.cfg["token"] = key
            self.cfg["remember_key"] = rem
            self.cfg["auto_login"] = auto
            self.cfg["hwid"] = self.hwid
            save_client_config(self.cfg)

            # Brief pause so user sees green verification confirmation
            QTimer.singleShot(500, self.accept)
        else:
            self._set_status(f"🔴 {message}", "#EF4444")


def check_or_show_login_dialog(parent: QWidget | None = None) -> bool:
    """Launch the Login Dialog if required, returning True if verified/logged in."""
    dialog = ClashBotLoginDialog(parent)
    result = dialog.exec()
    return result == QDialog.Accepted


if __name__ == "__main__":
    app = QApplication.instance() or QApplication(sys.argv)
    verified = check_or_show_login_dialog()
    print(f"Login result: {verified}")
    sys.exit(0 if verified else 1)
