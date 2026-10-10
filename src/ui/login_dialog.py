# -*- coding: utf-8 -*-
"""ClashBot AI - Client Activation & Sign-In Dialog.

Apple-inspired minimalist, clean interface for license authentication.
- Pure dark mode aesthetic (macOS/iOS inspired palette).
- Clean squircle branding with San Francisco-style typography.
- Streamlined single-field input with Enter-key submission.
- HWID hardware validation executed silently in the background (hidden from UI).
- Zero clutter: no neon effects, no emojis, no advanced network settings shown.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
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
    """Locate and return the app brand icon formatted with smooth rounded corners."""
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
                size = 60
                scaled = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                rounded = QPixmap(size, size)
                rounded.fill(Qt.transparent)
                painter = QPainter(rounded)
                painter.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, size, size), 14, 14)
                painter.setClipPath(path)
                painter.drawPixmap(0, 0, scaled)
                painter.end()
                return rounded
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
        "server_url": "https://clashbot.devtushar.uk",
        "token": "CLASH-PRO-FRIEND",
        "license_key": "CLASH-PRO-FRIEND",
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


_cached_client_public_ip: str | None = None

def get_client_real_ip() -> str:
    global _cached_client_public_ip
    if _cached_client_public_ip:
        return _cached_client_public_ip
    import urllib.request
    import socket
    for url in ("https://api.ipify.org", "https://icanhazip.com", "https://ifconfig.me/ip"):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "curl/7.68.0"})
            with urllib.request.urlopen(req, timeout=2.5) as resp:
                ip = resp.read().decode("utf-8").strip()
                if ip and len(ip.split(".")) == 4:
                    _cached_client_public_ip = ip
                    return ip
        except Exception:
            pass
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        if ip and ip not in ("127.0.0.1", "0.0.0.0"):
            _cached_client_public_ip = ip
            return ip
    except Exception:
        pass
    return "127.0.0.1"


class VerifyWorker(QThread):
    """Background worker to verify license & HWID with instant local path and multi-candidate network failover."""

    finished = Signal(bool, str, str)  # is_valid, message, user_name

    def __init__(self, server_url: str, key: str, hwid: str) -> None:
        super().__init__()
        self.server_url = server_url
        self.key = key
        self.hwid = hwid
        self.working_url: str = ""
        self.auth_data: dict = {}

    def run(self) -> None:
        # Asynchronous Multi-Candidate WebSocket Verification (Zero-timeout failover)
        import asyncio
        import inspect
        import socket
        import websockets

        def _format_ws_url(url: str) -> str:
            u = url.strip()
            if u.startswith("https://"):
                u = "wss://" + u[8:]
            elif u.startswith("http://"):
                u = "ws://" + u[7:]
            elif not (u.startswith("ws://") or u.startswith("wss://")):
                u = f"ws://{u}"
            if not u.endswith("/ws") and not u.endswith("/"):
                u = f"{u}/ws"
            return u

        # Candidate endpoints to try (prioritize local server first if running locally)
        candidates: list[str] = [
            _format_ws_url("ws://127.0.0.1:8765"),
        ]
        if self.server_url and self.server_url.strip():
            candidates.append(_format_ws_url(self.server_url))

        # Always probe permanent Cloudflare domain
        candidates.append(_format_ws_url("https://clashbot.devtushar.uk"))

        # LAN candidates
        try:
            local_ip = socket.gethostbyname(socket.gethostname())
            if local_ip and local_ip not in ("127.0.0.1", "0.0.0.0"):
                candidates.append(_format_ws_url(f"ws://{local_ip}:8765"))
        except Exception:
            pass

        # De-duplicate preserving order
        unique_candidates: list[str] = []
        seen = set()
        for c in candidates:
            if c not in seen:
                seen.add(c)
                unique_candidates.append(c)

        client_real_ip = get_client_real_ip()
        auth_payload = json.dumps({
            "key": self.key,
            "token": self.key,
            "hwid": self.hwid,
            "client_ip": client_real_ip,
            "version": "2.0.0",
        }).encode("utf-8")

        async def _probe_single(cand: str):
            try:
                connect_kwargs = {
                    "open_timeout": 2.5,
                    "ping_interval": None,
                }
                sig = inspect.signature(websockets.connect)
                bypass_headers = {"Bypass-Tunnel-Reminder": "true", "User-Agent": "Mozilla/5.0"}
                if "additional_headers" in sig.parameters:
                    connect_kwargs["additional_headers"] = bypass_headers
                elif "extra_headers" in sig.parameters:
                    connect_kwargs["extra_headers"] = bypass_headers

                async with websockets.connect(cand, **connect_kwargs) as ws:
                    await ws.send(pack_frame(MSG_AUTH, auth_payload))
                    resp = await asyncio.wait_for(ws.recv(), timeout=3.5)

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
                            return (True, msg or "License Verified", user, cand, data)
                        elif msg_type == MSG_AUTH_FAIL:
                            err_msg = data.get("error", payload) if isinstance(data, dict) else payload
                            return (False, err_msg or "Authentication failed.", "", cand, data)
            except asyncio.CancelledError:
                return (None, "Cancelled", "", cand, {})
            except asyncio.TimeoutError:
                return (None, "Server connection timed out.", "", cand, {})
            except Exception as e:
                err = str(e)
                if "10061" in err or "refused" in err.lower():
                    return (None, "Server is offline (connection refused).", "", cand, {})
                return (None, f"Connection error: {err}", "", cand, {})
            return (None, "Unexpected server response.", "", cand, {})

        async def _test_auth():
            if not unique_candidates:
                return False, "No valid server addresses configured.", ""

            tasks = [asyncio.create_task(_probe_single(c)) for c in unique_candidates]
            auth_rejection = None
            last_err = ""

            for fut in asyncio.as_completed(tasks):
                status, msg, user, cand, data = await fut
                if status is True:
                    for t in tasks:
                        if not t.done():
                            t.cancel()
                    self.working_url = cand
                    self.auth_data = data
                    return True, msg, user
                elif status is False:
                    auth_rejection = msg
                elif status is None:
                    last_err = msg

            if auth_rejection:
                return False, auth_rejection, ""

            return False, "Server is offline or unreachable. Please launch START_SERVER.bat on the host PC.", ""

        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            ok, msg, user = loop.run_until_complete(_test_auth())
            loop.close()
            self.finished.emit(ok, msg, user)
        except Exception as e:
            self.finished.emit(False, str(e), "")


class ClashBotLoginDialog(QDialog):
    """Apple-inspired minimalist Sign-In Dialog for ClashBot AI."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.cfg = load_client_config()
        self.hwid = get_hwid()
        self.worker: VerifyWorker | None = None
        self.drag_position = QPoint()

        self.setWindowTitle("ClashBot AI")
        self.setFixedSize(380, 460)
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
        outer_layout.setContentsMargins(10, 10, 10, 10)

        # Main macOS-styled Card Container
        self.card = QFrame(self)
        self.card.setObjectName("appleCard")
        self.card.setStyleSheet("""
            QFrame#appleCard {
                background-color: #1C1C1E;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 18px;
            }
        """)

        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(28, 20, 28, 24)
        card_layout.setSpacing(0)

        # 1. Minimal Header / Close Control
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)
        top_bar.addStretch()

        close_btn = QPushButton("✕")
        close_btn.setFixedSize(26, 26)
        close_btn.setCursor(Qt.PointingHandCursor)
        close_btn.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.06);
                border: none;
                border-radius: 13px;
                color: #8E8E93;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
                font-size: 11px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.15);
                color: #FFFFFF;
            }
        """)
        close_btn.clicked.connect(self.reject)
        top_bar.addWidget(close_btn)
        card_layout.addLayout(top_bar)

        card_layout.addSpacing(6)

        # 2. Hero Icon & Minimalist Typography
        hero_layout = QVBoxLayout()
        hero_layout.setSpacing(8)
        hero_layout.setAlignment(Qt.AlignCenter)

        icon_lbl = QLabel()
        pix = resolve_icon_pixmap()
        if pix:
            icon_lbl.setPixmap(pix)
        else:
            icon_lbl.setText("C")
            icon_lbl.setStyleSheet("""
                background-color: #2C2C2E;
                color: #FFFFFF;
                font-size: 24px;
                font-weight: bold;
                border-radius: 14px;
                min-width: 60px;
                min-height: 60px;
            """)
        icon_lbl.setAlignment(Qt.AlignCenter)
        hero_layout.addWidget(icon_lbl)

        card_layout.addSpacing(6)

        title_lbl = QLabel("ClashBot AI")
        title_lbl.setAlignment(Qt.AlignCenter)
        title_lbl.setStyleSheet("""
            font-family: -apple-system, 'SF Pro Display', 'Segoe UI', system-ui, sans-serif;
            font-size: 20px;
            font-weight: 600;
            color: #FFFFFF;
            letter-spacing: -0.3px;
        """)
        hero_layout.addWidget(title_lbl)

        sub_lbl = QLabel("Enter your license key to activate")
        sub_lbl.setAlignment(Qt.AlignCenter)
        sub_lbl.setStyleSheet("""
            font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
            font-size: 13px;
            color: #8E8E93;
            font-weight: 400;
        """)
        hero_layout.addWidget(sub_lbl)

        card_layout.addLayout(hero_layout)

        card_layout.addSpacing(24)

        # 3. Clean Input Field
        input_layout = QVBoxLayout()
        input_layout.setSpacing(10)

        saved_key = self.cfg.get("license_key") or self.cfg.get("token") or "CLASH-VIP-2026"
        self.key_edit = QLineEdit(saved_key)
        self.key_edit.setPlaceholderText("License Key")
        self.key_edit.setStyleSheet("""
            QLineEdit {
                background-color: #2C2C2E;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 10px;
                color: #FFFFFF;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
                font-size: 14px;
                padding: 12px 14px;
            }
            QLineEdit:focus {
                border: 1.5px solid #007AFF;
                background-color: #323235;
            }
        """)
        input_layout.addWidget(self.key_edit)

        # Options: Clean Apple style checkbox
        opts_layout = QHBoxLayout()
        opts_layout.setContentsMargins(2, 0, 0, 0)

        self.rem_cb = QCheckBox("Remember key")
        self.rem_cb.setChecked(self.cfg.get("remember_key", True))
        self.rem_cb.setStyleSheet("""
            QCheckBox {
                color: #8E8E93;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
                font-size: 12px;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 15px;
                height: 15px;
                border-radius: 4px;
                border: 1px solid #48484A;
                background-color: #2C2C2E;
            }
            QCheckBox::indicator:checked {
                background-color: #007AFF;
                border: 1px solid #007AFF;
            }
        """)
        opts_layout.addWidget(self.rem_cb)
        opts_layout.addStretch()
        input_layout.addLayout(opts_layout)

        card_layout.addLayout(input_layout)

        card_layout.addStretch()

        # 4. Status Notice
        self.status_lbl = QLabel("")
        self.status_lbl.setAlignment(Qt.AlignCenter)
        self.status_lbl.setWordWrap(True)
        self.status_lbl.setStyleSheet("""
            font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
            font-size: 12px;
            color: #8E8E93;
            min-height: 18px;
        """)
        card_layout.addWidget(self.status_lbl)

        card_layout.addSpacing(10)

        # 5. Clean Apple Blue Button
        self.continue_btn = QPushButton("Continue")
        self.continue_btn.setCursor(Qt.PointingHandCursor)
        self.continue_btn.setFixedHeight(42)
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background-color: #007AFF;
                border: none;
                border-radius: 10px;
                color: #FFFFFF;
                font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
                font-size: 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0069D9;
            }
            QPushButton:pressed {
                background-color: #0056B3;
            }
            QPushButton:disabled {
                background-color: #3A3A3C;
                color: #636366;
            }
        """)
        self.continue_btn.clicked.connect(self._start_verification)
        card_layout.addWidget(self.continue_btn)

        outer_layout.addWidget(self.card)

    def _set_status(self, text: str, color: str = "#8E8E93") -> None:
        self.status_lbl.setText(text)
        self.status_lbl.setStyleSheet(f"""
            font-family: -apple-system, 'SF Pro Text', 'Segoe UI', system-ui, sans-serif;
            font-size: 12px;
            color: {color};
            min-height: 18px;
        """)

    def _start_verification(self) -> None:
        key = self.key_edit.text().strip()
        url = self.cfg.get("server_url", "ws://127.0.0.1:8765")

        if not key:
            self._set_status("Please enter a license key.", "#FF453A")
            return

        self.continue_btn.setEnabled(False)
        self.continue_btn.setText("Verifying...")
        self._set_status("Connecting...", "#8E8E93")

        self.worker = VerifyWorker(server_url=url, key=key, hwid=self.hwid)
        self.worker.finished.connect(self._on_verification_finished)
        self.worker.start()

    @Slot(bool, str, str)
    def _on_verification_finished(self, is_valid: bool, message: str, user: str) -> None:
        self.continue_btn.setEnabled(True)
        self.continue_btn.setText("Continue")

        if is_valid:
            welcome = f"Welcome, {user}" if user else "Activated"
            self._set_status(welcome, "#30D158")

            key = self.key_edit.text().strip()
            rem = self.rem_cb.isChecked()
            auth_meta = getattr(self.worker, "auth_data", {}) if self.worker else {}

            exp_fmt = auth_meta.get("expires_formatted") or auth_meta.get("expires_at", "Active")
            exp_iso = auth_meta.get("expires_at") or exp_fmt
            plan_str = auth_meta.get("plan", "Pro Monthly")
            status_str = auth_meta.get("license_status") or auth_meta.get("status", "active")

            self.cfg["key"] = key
            self.cfg["license_key"] = key
            self.cfg["token"] = key
            self.cfg["user"] = user
            self.cfg["remember_key"] = rem
            self.cfg["hwid"] = self.hwid
            self.cfg["plan"] = plan_str
            self.cfg["expires"] = exp_fmt
            self.cfg["expires_at"] = exp_iso
            self.cfg["expires_formatted"] = exp_fmt
            self.cfg["status"] = status_str
            if self.worker and getattr(self.worker, "working_url", ""):
                self.cfg["server_url"] = self.worker.working_url
            save_client_config(self.cfg)

            # Persist clean metadata and license.key for UI components
            try:
                meta_dict = {
                    "valid": True,
                    "status": status_str,
                    "plan": plan_str,
                    "expires": exp_fmt,
                    "expires_at": exp_iso,
                    "expires_formatted": exp_fmt,
                    "remaining": exp_fmt,
                    "user": user,
                    "hwid": self.hwid,
                    "key": key,
                }
                candidate_dirs = [
                    Path("."),
                    Path("src"),
                    Path(os.getcwd()),
                    Path(os.getcwd()) / "src",
                    Path(__file__).resolve().parent.parent,
                    Path(__file__).resolve().parent.parent / "src",
                    Path(__file__).resolve().parent.parent / "friend_client_bundle" / "src",
                ]
                for base in candidate_dirs:
                    try:
                        base.mkdir(parents=True, exist_ok=True)
                        meta_file = base / "license_meta.json"
                        with open(meta_file, "w", encoding="utf-8") as f:
                            json.dump(meta_dict, f, indent=2)
                        kfile = base / "license.key"
                        kfile.write_text(key, encoding="utf-8")
                    except Exception:
                        pass
                try:
                    import license_manager
                    license_manager.save_license_meta(meta_dict)
                except Exception:
                    pass
            except Exception:
                pass

            QTimer.singleShot(400, self.accept)
        else:
            self._set_status(message, "#FF453A")


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
