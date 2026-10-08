# -*- coding: utf-8 -*-
"""ClashBot AI - Client Login & License Activation Dialog.

Modern PySide6 Login Dialog with hardware identification (HWID) binding.
Allows users to enter their license key, view/copy their machine HWID,
and verify their activation directly with the cloud server.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QObject, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QCheckBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from remote_bridge.hwid import get_hwid
from remote_bridge.protocol import MSG_AUTH, MSG_AUTH_FAIL, MSG_AUTH_OK, pack_frame


def get_config_path() -> Path:
    # Check parent directory (project root) or local
    candidates = [
        Path(__file__).resolve().parent.parent / "client_config.json",
        Path(__file__).resolve().parent / "client_config.json",
        Path(os.getcwd()) / "client_config.json",
    ]
    for p in candidates:
        if p.exists():
            return p
    return candidates[0]


def load_client_config() -> dict:
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
    p = get_config_path()
    try:
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "w", encoding="utf-8") as f:
            json.dump(cfg, f, indent=2)
    except Exception as e:
        print(f"[!] Warning saving client_config.json: {e}")


class VerifyWorker(QThread):
    """Background worker to verify license & HWID over WebSocket without freezing UI."""
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
                return False, "Connection timed out. Server is taking too long to respond.", ""
            except Exception as e:
                err = str(e)
                if "10061" in err or "refused" in err.lower():
                    return False, "Connection refused: Server is not running or port 8765 is closed.", ""
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
    """Dedicated modern dark-mode Login Window with HWID hardware binding."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = load_client_config()
        self.hwid = get_hwid()
        self.worker: VerifyWorker | None = None

        self.setWindowTitle("ClashBot AI — Client Authentication & Activation")
        self.resize(520, 560)
        self.setMinimumSize(480, 520)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)

        self._init_ui()
        self._apply_styles()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(16)

        # 1. Header Card with App Title and Subtitle
        header_layout = QVBoxLayout()
        header_layout.setSpacing(4)
        header_layout.setAlignment(Qt.AlignCenter)

        title_lbl = QLabel("⚔️ CLASHBOT AI")
        title_lbl.setObjectName("appTitle")
        title_lbl.setAlignment(Qt.AlignCenter)

        sub_lbl = QLabel("Autonomous Cloud Intelligence • Hardware-Bound License")
        sub_lbl.setObjectName("subTitle")
        sub_lbl.setAlignment(Qt.AlignCenter)

        header_layout.addWidget(title_lbl)
        header_layout.addWidget(sub_lbl)
        layout.addLayout(header_layout)

        # 2. Machine Hardware ID (HWID) Display Box
        hwid_box = QFrame()
        hwid_box.setObjectName("hwidCard")
        hwid_layout = QVBoxLayout(hwid_box)
        hwid_layout.setContentsMargins(14, 12, 14, 12)
        hwid_layout.setSpacing(8)

        hwid_header = QHBoxLayout()
        hwid_title = QLabel("🔒 MACHINE HWID (Hardware Fingerprint):")
        hwid_title.setObjectName("sectionHeader")
        hwid_header.addWidget(hwid_title)
        hwid_header.addStretch()

        self.copy_btn = QPushButton("📋 Copy HWID")
        self.copy_btn.setObjectName("copyBtn")
        self.copy_btn.clicked.connect(self._copy_hwid)
        hwid_header.addWidget(self.copy_btn)
        hwid_layout.addLayout(hwid_header)

        self.hwid_edit = QLineEdit(self.hwid)
        self.hwid_edit.setReadOnly(True)
        self.hwid_edit.setObjectName("hwidDisplay")
        hwid_layout.addWidget(self.hwid_edit)

        hwid_hint = QLabel("Each license is locked to your PC's HWID to prevent sharing.")
        hwid_hint.setObjectName("hintText")
        hwid_layout.addWidget(hwid_hint)

        layout.addWidget(hwid_box)

        # 3. Credentials Input Card
        form_card = QFrame()
        form_card.setObjectName("formCard")
        form_layout = QVBoxLayout(form_card)
        form_layout.setContentsMargins(16, 14, 16, 14)
        form_layout.setSpacing(12)

        # License Key Field
        key_label = QLabel("🔑 License Key:")
        key_label.setObjectName("inputLabel")
        form_layout.addWidget(key_label)

        saved_key = self.cfg.get("license_key") or self.cfg.get("token") or "CLASH-VIP-2026"
        self.key_edit = QLineEdit(saved_key)
        self.key_edit.setPlaceholderText("Enter Key (e.g. CLASH-VIP-2026)")
        self.key_edit.setObjectName("textInput")
        form_layout.addWidget(self.key_edit)

        # Server URL Field
        url_label = QLabel("🌐 Cloud Server Endpoint:")
        url_label.setObjectName("inputLabel")
        form_layout.addWidget(url_label)

        saved_url = self.cfg.get("server_url") or "ws://110.227.184.49:8765"
        self.url_edit = QLineEdit(saved_url)
        self.url_edit.setPlaceholderText("ws://110.227.184.49:8765")
        self.url_edit.setObjectName("textInput")
        form_layout.addWidget(self.url_edit)

        # Remember Key Checkbox
        self.remember_cb = QCheckBox("Remember License Key on this PC")
        self.remember_cb.setChecked(self.cfg.get("remember_key", True))
        self.remember_cb.setObjectName("rememberCb")
        form_layout.addWidget(self.remember_cb)

        layout.addWidget(form_card)

        # 4. Status Notification Banner
        self.status_banner = QLabel("Enter your license key and connect to activate.")
        self.status_banner.setObjectName("statusBanner")
        self.status_banner.setWordWrap(True)
        self.status_banner.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_banner)

        layout.addStretch()

        # 5. Bottom Buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(12)

        self.exit_btn = QPushButton("Exit")
        self.exit_btn.setObjectName("secondaryBtn")
        self.exit_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.exit_btn)

        self.login_btn = QPushButton("⚡ Connect & Activate")
        self.login_btn.setObjectName("primaryBtn")
        self.login_btn.clicked.connect(self._start_verification)
        btn_layout.addWidget(self.login_btn, 1)

        layout.addLayout(btn_layout)

    def _apply_styles(self) -> None:
        self.setStyleSheet("""
            QDialog {
                background-color: #0b0f19;
                color: #e2e8f0;
                font-family: 'Segoe UI', system-ui, sans-serif;
            }
            QLabel#appTitle {
                font-size: 22px;
                font-weight: 800;
                color: #38bdf8;
                letter-spacing: 1px;
            }
            QLabel#subTitle {
                font-size: 11px;
                color: #64748b;
                font-weight: 500;
            }
            QFrame#hwidCard {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QFrame#formCard {
                background-color: #111827;
                border: 1px solid #1e293b;
                border-radius: 8px;
            }
            QLabel#sectionHeader {
                font-size: 11px;
                font-weight: 700;
                color: #94a3b8;
                letter-spacing: 0.5px;
            }
            QLabel#inputLabel {
                font-size: 12px;
                font-weight: 600;
                color: #cbd5e1;
            }
            QLabel#hintText {
                font-size: 10px;
                color: #64748b;
            }
            QLineEdit#hwidDisplay {
                background-color: #030712;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #38bdf8;
                font-family: 'Consolas', 'Cascadia Code', monospace;
                font-size: 13px;
                font-weight: bold;
                padding: 6px 10px;
            }
            QLineEdit#textInput {
                background-color: #030712;
                border: 1px solid #334155;
                border-radius: 6px;
                color: #f8fafc;
                font-size: 13px;
                padding: 7px 12px;
            }
            QLineEdit#textInput:focus {
                border: 1px solid #38bdf8;
            }
            QPushButton#copyBtn {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 5px;
                color: #38bdf8;
                font-size: 11px;
                font-weight: 600;
                padding: 3px 8px;
            }
            QPushButton#copyBtn:hover {
                background-color: #334155;
                color: #ffffff;
            }
            QCheckBox#rememberCb {
                color: #94a3b8;
                font-size: 11px;
                spacing: 8px;
            }
            QCheckBox#rememberCb::indicator {
                width: 16px;
                height: 16px;
                border-radius: 4px;
                border: 1px solid #475569;
                background-color: #0f172a;
            }
            QCheckBox#rememberCb::indicator:checked {
                background-color: #38bdf8;
                border: 1px solid #38bdf8;
            }
            QLabel#statusBanner {
                background-color: rgba(30, 41, 59, 0.5);
                border: 1px solid #1e293b;
                border-radius: 6px;
                color: #94a3b8;
                font-size: 11px;
                font-weight: 500;
                padding: 8px 12px;
            }
            QPushButton#primaryBtn {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0284c7, stop:1 #2563eb);
                border: none;
                border-radius: 7px;
                color: #ffffff;
                font-size: 13px;
                font-weight: bold;
                padding: 10px 16px;
            }
            QPushButton#primaryBtn:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #0369a1, stop:1 #1d4ed8);
            }
            QPushButton#primaryBtn:disabled {
                background-color: #334155;
                color: #64748b;
            }
            QPushButton#secondaryBtn {
                background-color: #1e293b;
                border: 1px solid #334155;
                border-radius: 7px;
                color: #94a3b8;
                font-size: 13px;
                font-weight: 600;
                padding: 10px 16px;
            }
            QPushButton#secondaryBtn:hover {
                background-color: #334155;
                color: #ffffff;
            }
        """)

    def _copy_hwid(self) -> None:
        clipboard = QApplication.clipboard()
        clipboard.setText(self.hwid)
        self.copy_btn.setText("✓ Copied!")
        QTimer.singleShot(1800, lambda: self.copy_btn.setText("📋 Copy HWID"))

    def _start_verification(self) -> None:
        key = self.key_edit.text().strip()
        url = self.url_edit.text().strip()

        if not key:
            self._set_status("Please enter a valid license key.", "#ef4444")
            return
        if not url:
            self._set_status("Please enter a server endpoint URL.", "#ef4444")
            return

        self.login_btn.setEnabled(False)
        self.login_btn.setText("⏳ Verifying HWID...")
        self._set_status("🔄 Connecting to cloud engine and validating HWID...", "#38bdf8")

        self.worker = VerifyWorker(server_url=url, key=key, hwid=self.hwid)
        self.worker.finished.connect(self._on_verification_finished)
        self.worker.start()

    @Slot(bool, str, str)
    def _on_verification_finished(self, is_valid: bool, message: str, user: str) -> None:
        self.login_btn.setEnabled(True)
        self.login_btn.setText("⚡ Connect & Activate")

        if is_valid:
            welcome = f"Welcome, {user}!" if user else "Activation Successful!"
            self._set_status(f"🟢 {message} ({welcome})", "#10b981")

            # Save valid credentials
            key = self.key_edit.text().strip()
            url = self.url_edit.text().strip()
            rem = self.remember_cb.isChecked()

            self.cfg["server_url"] = url
            self.cfg["license_key"] = key
            self.cfg["token"] = key
            self.cfg["remember_key"] = rem
            self.cfg["hwid"] = self.hwid
            save_client_config(self.cfg)

            # Briefly pause to let user see success, then accept
            QTimer.singleShot(600, self.accept)
        else:
            self._set_status(f"🔴 {message}", "#ef4444")

    def _set_status(self, text: str, color_hex: str) -> None:
        self.status_banner.setText(text)
        self.status_banner.setStyleSheet(f"""
            background-color: rgba({int(color_hex[1:3], 16)}, {int(color_hex[3:5], 16)}, {int(color_hex[5:7], 16)}, 0.15);
            border: 1px solid {color_hex};
            border-radius: 6px;
            color: {color_hex};
            font-size: 11px;
            font-weight: 600;
            padding: 8px 12px;
        """)


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
