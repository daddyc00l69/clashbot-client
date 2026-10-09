# -*- coding: utf-8 -*-
"""ClashBot AI - Client Dashboard & Remote Control.

Apple-inspired minimalist, clean interface:
- Zero Bot Logic on client: all combat, vision, and farming intelligence run on Cloud Server.
- Real-time verified telemetry stream (Gold, Elixir, Dark Elixir, Attacks, Server Calls).
- Streamlined Start, Pause, Resume, and Stop bot controls.
- Live emulator connection monitoring and auto-detection.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

from PySide6.QtCore import QPoint, QRectF, Qt, QThread, QTimer, Signal, Slot
from PySide6.QtGui import QColor, QFont, QIcon, QPainter, QPainterPath, QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)

from remote_bridge.client_bridge_runner import ClientRemoteEngine
from remote_bridge.hwid import get_hwid


def resolve_icon_pixmap(size: int = 40) -> QPixmap | None:
    curr = Path(__file__).resolve().parent
    candidates = [
        curr.parent / "assets" / "icon.png",
        curr / "assets" / "icon.png",
        curr.parent / "src" / "assets" / "icon.png",
    ]
    for c in candidates:
        if c.is_file():
            pix = QPixmap(str(c))
            if not pix.isNull():
                scaled = pix.scaled(size, size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                rounded = QPixmap(size, size)
                rounded.fill(Qt.transparent)
                p = QPainter(rounded)
                p.setRenderHint(QPainter.Antialiasing)
                path = QPainterPath()
                path.addRoundedRect(QRectF(0, 0, size, size), 10, 10)
                p.setClipPath(path)
                p.drawPixmap(0, 0, scaled)
                p.end()
                return rounded
    return None


class StatCard(QFrame):
    """Clean Apple-style elevated metric card."""

    def __init__(self, title: str, icon_symbol: str, accent_color: str, parent=None):
        super().__init__(parent)
        self.setObjectName("StatCard")
        self.setStyleSheet(f"""
            QFrame#StatCard {{
                background-color: #1a1a1e;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 12px;
            }}
            QFrame#StatCard:hover {{
                border: 1px solid {accent_color};
                background-color: #202025;
            }}
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)

        icon_lbl = QLabel(icon_symbol)
        icon_lbl.setStyleSheet(f"font-size: 16px; color: {accent_color};")
        title_lbl = QLabel(title.upper())
        title_lbl.setStyleSheet("font-size: 11px; font-weight: 600; color: #8e8e93; letter-spacing: 0.5px;")

        header_layout.addWidget(icon_lbl)
        header_layout.addWidget(title_lbl)
        header_layout.addStretch()

        self.val_lbl = QLabel("0")
        self.val_lbl.setStyleSheet("font-size: 22px; font-weight: 700; color: #ffffff;")

        layout.addLayout(header_layout)
        layout.addWidget(self.val_lbl)

    def set_value(self, val: int | str):
        if isinstance(val, int):
            self.val_lbl.setText(f"{val:,}")
        else:
            self.val_lbl.setText(str(val))


class ClientDashboardWindow(QMainWindow):
    """Sleek Apple-inspired Minimalist Client GUI."""

    def __init__(self, engine: ClientRemoteEngine, config_path: str | None = None):
        super().__init__()
        self.engine = engine
        self.config_path = config_path or str(Path(__file__).resolve().parent.parent / "client_config.json")
        self.hwid = get_hwid()
        self.bot_running = False
        self.bot_paused = False

        self._load_saved_config()
        self._init_ui()
        self._setup_poll_timer()

    def _load_saved_config(self):
        self.saved_speed = "balanced"
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    d = json.load(f)
                    self.saved_speed = d.get("bot_speed", "balanced")
            except Exception:
                pass

    def _save_config(self):
        data = {}
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception:
                pass
        data["bot_speed"] = self.speed_combo.currentText().lower()
        try:
            with open(self.config_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _init_ui(self):
        self.setWindowTitle("ClashBot AI — Cloud Combat Dashboard")
        self.resize(840, 680)
        self.setMinimumSize(780, 580)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #121214;
            }
            QWidget {
                color: #e5e5ea;
                font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            }
        """)

        central = QWidget(self)
        self.setCentralWidget(central)
        root_layout = QVBoxLayout(central)
        root_layout.setContentsMargins(24, 20, 24, 20)
        root_layout.setSpacing(18)

        # 1. Header Bar: Brand + Connection Status + RTT Ping
        header_bar = QHBoxLayout()
        header_bar.setSpacing(12)

        icon_pix = resolve_icon_pixmap(38)
        if icon_pix:
            icon_lbl = QLabel()
            icon_lbl.setPixmap(icon_pix)
            header_bar.addWidget(icon_lbl)

        title_box = QVBoxLayout()
        title_box.setSpacing(2)
        app_title = QLabel("ClashBot AI")
        app_title.setStyleSheet("font-size: 18px; font-weight: 700; color: #ffffff;")
        app_sub = QLabel("Cloud Autonomous Combat Intelligence")
        app_sub.setStyleSheet("font-size: 12px; color: #8e8e93;")
        title_box.addWidget(app_title)
        title_box.addWidget(app_sub)
        header_bar.addLayout(title_box)

        header_bar.addStretch()

        # Connection status pill
        self.status_pill = QLabel("🟢 Connected")
        self.status_pill.setStyleSheet("""
            background-color: rgba(48, 209, 88, 0.15);
            color: #30d158;
            border: 1px solid rgba(48, 209, 88, 0.3);
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        """)
        header_bar.addWidget(self.status_pill)

        # RTT Ping pill
        self.ping_pill = QLabel("📶 -- ms")
        self.ping_pill.setStyleSheet("""
            background-color: rgba(255, 255, 255, 0.06);
            color: #aeaeb2;
            border: 1px solid rgba(255, 255, 255, 0.1);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 500;
        """)
        header_bar.addWidget(self.ping_pill)

        # HWID Verified Shield pill
        self.hwid_pill = QLabel("🛡️ Verified HWID")
        self.hwid_pill.setStyleSheet("""
            background-color: rgba(10, 132, 255, 0.12);
            color: #0a84ff;
            border: 1px solid rgba(10, 132, 255, 0.25);
            border-radius: 12px;
            padding: 4px 10px;
            font-size: 12px;
            font-weight: 500;
        """)
        header_bar.addWidget(self.hwid_pill)

        root_layout.addLayout(header_bar)

        # 2. Control Bar (Start / Pause / Stop + Speed Mode + Emulator status)
        control_frame = QFrame()
        control_frame.setStyleSheet("""
            QFrame {
                background-color: #1a1a1e;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 14px;
                padding: 12px;
            }
        """)
        ctl_layout = QHBoxLayout(control_frame)
        ctl_layout.setContentsMargins(14, 10, 14, 10)
        ctl_layout.setSpacing(12)

        self.btn_start = QPushButton("▶  Start Bot")
        self.btn_start.setCursor(Qt.PointingHandCursor)
        self.btn_start.setStyleSheet("""
            QPushButton {
                background-color: #0071e3;
                color: #ffffff;
                border: none;
                border-radius: 8px;
                padding: 8px 20px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: #0077ed;
            }
            QPushButton:pressed {
                background-color: #0062c4;
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.08);
                color: #636366;
            }
        """)
        self.btn_start.clicked.connect(self._on_start_clicked)

        self.btn_pause = QPushButton("⏸  Pause")
        self.btn_pause.setCursor(Qt.PointingHandCursor)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 255, 255, 0.08);
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 500;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.12);
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.05);
            }
            QPushButton:disabled {
                color: #636366;
                border-color: rgba(255, 255, 255, 0.05);
            }
        """)
        self.btn_pause.clicked.connect(self._on_pause_clicked)

        self.btn_stop = QPushButton("⏹  Stop Bot")
        self.btn_stop.setCursor(Qt.PointingHandCursor)
        self.btn_stop.setEnabled(False)
        self.btn_stop.setStyleSheet("""
            QPushButton {
                background-color: rgba(255, 69, 58, 0.15);
                color: #ff453a;
                border: 1px solid rgba(255, 69, 58, 0.3);
                border-radius: 8px;
                padding: 8px 18px;
                font-size: 13px;
                font-weight: 600;
            }
            QPushButton:hover {
                background-color: rgba(255, 69, 58, 0.25);
            }
            QPushButton:pressed {
                background-color: rgba(255, 69, 58, 0.1);
            }
            QPushButton:disabled {
                background-color: rgba(255, 255, 255, 0.05);
                color: #636366;
                border-color: transparent;
            }
        """)
        self.btn_stop.clicked.connect(self._on_stop_clicked)

        ctl_layout.addWidget(self.btn_start)
        ctl_layout.addWidget(self.btn_pause)
        ctl_layout.addWidget(self.btn_stop)

        ctl_layout.addSpacing(16)

        speed_lbl = QLabel("Pacing:")
        speed_lbl.setStyleSheet("color: #8e8e93; font-size: 12px; font-weight: 500;")
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["Balanced", "Fast", "Relaxed"])
        self.speed_combo.setCurrentText(self.saved_speed.capitalize())
        self.speed_combo.setStyleSheet("""
            QComboBox {
                background-color: #242429;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.1);
                border-radius: 6px;
                padding: 5px 12px;
                font-size: 12px;
                font-weight: 500;
            }
            QComboBox::drop-down {
                border: none;
            }
        """)
        self.speed_combo.currentTextChanged.connect(self._on_speed_changed)

        ctl_layout.addWidget(speed_lbl)
        ctl_layout.addWidget(self.speed_combo)

        ctl_layout.addStretch()

        self.emu_lbl = QLabel(f"📱 127.0.0.1:{self.engine.emulator_port}")
        self.emu_lbl.setStyleSheet("color: #8e8e93; font-size: 12px; font-weight: 500;")
        ctl_layout.addWidget(self.emu_lbl)

        root_layout.addWidget(control_frame)

        # 3. Live Combat Telemetry Cards
        stats_layout = QHBoxLayout()
        stats_layout.setSpacing(12)

        self.card_gold = StatCard("Gold Looted", "💰", "#ffd60a", self)
        self.card_elixir = StatCard("Elixir Looted", "🧪", "#bf5af2", self)
        self.card_dark = StatCard("Dark Elixir", "🛢️", "#5e5ce6", self)
        self.card_wins = StatCard("Attacks Won", "⚔️", "#30d158", self)

        stats_layout.addWidget(self.card_gold)
        stats_layout.addWidget(self.card_elixir)
        stats_layout.addWidget(self.card_dark)
        stats_layout.addWidget(self.card_wins)

        root_layout.addLayout(stats_layout)

        # 4. Live Server Call & Action Stream
        feed_header = QHBoxLayout()
        feed_title = QLabel("LIVE SERVER EXECUTION STREAM")
        feed_title.setStyleSheet("font-size: 12px; font-weight: 700; color: #8e8e93; letter-spacing: 0.5px;")

        self.calls_count_lbl = QLabel("0 Calls Verified")
        self.calls_count_lbl.setStyleSheet("font-size: 11px; color: #636366;")

        feed_header.addWidget(feed_title)
        feed_header.addStretch()
        feed_header.addWidget(self.calls_count_lbl)
        root_layout.addLayout(feed_header)

        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(800)
        self.log_view.setStyleSheet("""
            QPlainTextEdit {
                background-color: #161618;
                color: #d1d1d6;
                border: 1px solid rgba(255, 255, 255, 0.08);
                border-radius: 12px;
                padding: 10px;
                font-family: Consolas, "SF Mono", Monaco, "Courier New", monospace;
                font-size: 12px;
                line-height: 1.5;
            }
        """)
        root_layout.addWidget(self.log_view, stretch=1)

        # Bottom Footer
        footer_layout = QHBoxLayout()
        footer_lbl = QLabel("ClashBot AI v2.0 • Server-Side Zero-Client Architecture")
        footer_lbl.setStyleSheet("font-size: 11px; color: #48484a;")
        footer_layout.addWidget(footer_lbl)
        footer_layout.addStretch()

        clear_btn = QPushButton("Clear Stream")
        clear_btn.setCursor(Qt.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                background: transparent;
                color: #8e8e93;
                border: none;
                font-size: 11px;
            }
            QPushButton:hover {
                color: #ffffff;
            }
        """)
        clear_btn.clicked.connect(self.log_view.clear)
        footer_layout.addWidget(clear_btn)

        root_layout.addLayout(footer_layout)

    def _setup_poll_timer(self):
        self.poll_timer = QTimer(self)
        self.poll_timer.timeout.connect(self._on_poll_tick)
        self.poll_timer.start(250)

    @Slot()
    def _on_poll_tick(self):
        # Update ping pill
        ping_ms = ClientRemoteEngine.LATEST_PING_MS
        if ping_ms is not None and 0 <= ping_ms < 5000:
            self.ping_pill.setText(f"📶 {ping_ms} ms")
            if ping_ms < 80:
                self.ping_pill.setStyleSheet("""
                    background-color: rgba(48, 209, 88, 0.12);
                    color: #30d158;
                    border: 1px solid rgba(48, 209, 88, 0.25);
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 500;
                """)
            else:
                self.ping_pill.setStyleSheet("""
                    background-color: rgba(255, 214, 10, 0.12);
                    color: #ffd60a;
                    border: 1px solid rgba(255, 214, 10, 0.25);
                    border-radius: 12px;
                    padding: 4px 10px;
                    font-size: 12px;
                    font-weight: 500;
                """)

        # Update stats
        if self.engine and self.engine.stats:
            self.card_gold.set_value(getattr(self.engine.stats, "gold_looted", 0))
            self.card_elixir.set_value(getattr(self.engine.stats, "elixir_looted", 0))
            self.card_dark.set_value(getattr(self.engine.stats, "dark_elixir_looted", 0))
            self.card_wins.set_value(getattr(self.engine.stats, "attacks_won", 0))

        # Update call count
        call_total = ClientRemoteEngine.TOTAL_SERVER_CALLS
        self.calls_count_lbl.setText(f"{call_total} Calls Verified")

        # Update latest server call
        call = ClientRemoteEngine.LATEST_SERVER_CALL
        if call and getattr(self, "_last_rendered_call_id", None) != call.get("id"):
            self._last_rendered_call_id = call.get("id")
            act = call.get("action", "")
            det = call.get("details", "")
            tm = call.get("time", "")
            dur = call.get("duration_ms", 0)
            dur_str = f" [{dur}ms]" if dur else ""
            line = f"[{tm}] ⚡ {act} {det}{dur_str}"
            self.log_view.appendPlainText(line)

    @Slot()
    def _on_start_clicked(self):
        self.bot_running = True
        self.bot_paused = False
        self.btn_start.setEnabled(False)
        self.btn_pause.setEnabled(True)
        self.btn_pause.setText("⏸  Pause")
        self.btn_stop.setEnabled(True)
        self.status_pill.setText("⚡ Bot Running Active")
        self.status_pill.setStyleSheet("""
            background-color: rgba(0, 113, 227, 0.15);
            color: #0a84ff;
            border: 1px solid rgba(0, 113, 227, 0.35);
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        """)

        cfg = {"bot_speed": self.speed_combo.currentText().lower()}
        self.engine.send_bot_control("start", cfg)
        self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] ▶ Sent START command to Cloud Engine [HWID: {self.hwid[:8]}...]")

    @Slot()
    def _on_pause_clicked(self):
        if not self.bot_paused:
            self.bot_paused = True
            self.btn_pause.setText("▶  Resume")
            self.status_pill.setText("⏸️ Bot Paused")
            self.status_pill.setStyleSheet("""
                background-color: rgba(255, 214, 10, 0.15);
                color: #ffd60a;
                border: 1px solid rgba(255, 214, 10, 0.35);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            """)
            self.engine.send_bot_control("pause")
            self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] ⏸ Sent PAUSE command to Cloud Engine")
        else:
            self.bot_paused = False
            self.btn_pause.setText("⏸  Pause")
            self.status_pill.setText("⚡ Bot Running Active")
            self.status_pill.setStyleSheet("""
                background-color: rgba(0, 113, 227, 0.15);
                color: #0a84ff;
                border: 1px solid rgba(0, 113, 227, 0.35);
                border-radius: 12px;
                padding: 4px 12px;
                font-size: 12px;
                font-weight: 600;
            """)
            self.engine.send_bot_control("resume")
            self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] ▶ Sent RESUME command to Cloud Engine")

    @Slot()
    def _on_stop_clicked(self):
        self.bot_running = False
        self.bot_paused = False
        self.btn_start.setEnabled(True)
        self.btn_pause.setEnabled(False)
        self.btn_pause.setText("⏸  Pause")
        self.btn_stop.setEnabled(False)
        self.status_pill.setText("🟢 Connected • Ready")
        self.status_pill.setStyleSheet("""
            background-color: rgba(48, 209, 88, 0.15);
            color: #30d158;
            border: 1px solid rgba(48, 209, 88, 0.3);
            border-radius: 12px;
            padding: 4px 12px;
            font-size: 12px;
            font-weight: 600;
        """)
        self.engine.send_bot_control("stop")
        self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] ⏹ Sent STOP command to Cloud Engine")

    @Slot(str)
    def _on_speed_changed(self, text: str):
        self._save_config()
        if self.bot_running:
            cfg = {"bot_speed": text.lower()}
            self.engine.send_bot_control("start", cfg)
            self.log_view.appendPlainText(f"[{time.strftime('%H:%M:%S')}] ⚡ Pacing updated to: {text}")
