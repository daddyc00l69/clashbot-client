"""ClashBot AI - Remote Bot Control Dashboard & Bridge.

The client-facing dashboard that runs on your friend's laptop:
- Exposes complete remote bot controls (Start, Pause, Stop).
- Strategy selector (Sneaky Goblins, Barch, E-Dragons, Dead Base).
- Minimum loot filters (Gold, Elixir, Dark Elixir).
- Automation toggles (Walls, Army, Resource Collection, Builder Base).
- Live session telemetry (Loot gained, Attacks won, Bot state).
- Live real-time activity log.
"""

from __future__ import annotations

import asyncio
import json
import re
import socket
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import websockets

# Protocol Message Types
MSG_AUTH = 0x01
MSG_AUTH_OK = 0x02
MSG_AUTH_FAIL = 0x03
MSG_OPEN_CHANNEL = 0x10
MSG_CHANNEL_OPENED = 0x11
MSG_CHANNEL_DATA = 0x12
MSG_CLOSE_CHANNEL = 0x13
MSG_BOT_CONTROL = 0x30
MSG_BOT_CONFIG = 0x31
MSG_BOT_TELEMETRY = 0x32

CHANNEL_STRUCT = struct.Struct("!I")

COMMON_EMULATOR_PORTS = [
    (5555, "BlueStacks / LDPlayer / Generic"),
    (16384, "MuMu Player 12"),
    (7555, "MuMu Player 6"),
    (62001, "NoxPlayer / LDPlayer alt"),
    (21503, "MEmu Play"),
]


def detect_emulator() -> tuple[int, str]:
    for port, name in COMMON_EMULATOR_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    return port, name
            except Exception:
                pass
    return 5555, "Standard ADB (Default)"


def normalize_ws_url(raw_url: str) -> str:
    text = raw_url.strip().strip('"').strip("'")
    match = re.search(r"(https?://[^\s'\"]+|wss?://[^\s'\"]+|[a-zA-Z0-9\-]+\.trycloudflare\.com[^\s'\"]*)", text)
    if match:
        text = match.group(0)

    if text.startswith("https://"):
        return "wss://" + text[8:]
    if text.startswith("http://"):
        return "ws://" + text[7:]
    if text.startswith("wss://") or text.startswith("ws://"):
        return text
    if "trycloudflare.com" in text or not (":" in text and text.split(":")[-1].isdigit()):
        return "wss://" + text
    return "ws://" + text


class RemoteBotDashboard:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ClashBot AI - Remote Control Dashboard")
        self.root.geometry("640x780")
        self.root.minsize(580, 700)
        self.root.configure(bg="#0F1117")

        self.is_connected = False
        self.bot_running = False
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None
        self.channels: dict[int, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self.active_ws = None
        self.token = "clashbot-secret-key-2026"
        self.emu_port = 5555

        # Stats counters
        self.gold_looted = 0
        self.elixir_looted = 0
        self.de_looted = 0
        self.attacks_won = 0

        self._build_ui()
        self._rescan_emulator()

    def _build_ui(self) -> None:
        # Top Header
        header = tk.Frame(self.root, bg="#161B26", height=70)
        header.pack(fill="x", side="top")

        h_left = tk.Frame(header, bg="#161B26")
        h_left.pack(side="left", padx=20, pady=12)

        tk.Label(h_left, text="⚡ CLASHBOT AI", font=("Segoe UI", 16, "bold"), fg="#00E676", bg="#161B26").pack(anchor="w")
        tk.Label(h_left, text="Remote Game Intelligence & Tactical Control Dashboard", font=("Segoe UI", 9), fg="#8A93A6", bg="#161B26").pack(anchor="w")

        self.status_badge = tk.Label(header, text="● OFFLINE", font=("Segoe UI", 9, "bold"), fg="#FF5252", bg="#161B26")
        self.status_badge.pack(side="right", padx=20)

        # Scrollable Canvas or Main Card
        main_container = tk.Frame(self.root, bg="#0F1117")
        main_container.pack(fill="both", expand=True, padx=16, pady=12)

        # 1. Connection Card
        conn_card = tk.LabelFrame(main_container, text=" 🔗 SERVER CONNECTION ", font=("Segoe UI", 9, "bold"), fg="#9E9E9E", bg="#161B26", bd=1, relief="solid")
        conn_card.pack(fill="x", pady=(0, 10), padx=2, ipady=6)

        c_row = tk.Frame(conn_card, bg="#161B26")
        c_row.pack(fill="x", padx=12, pady=6)

        self.url_var = tk.StringVar(value="https://holmes-recruiting-heat-bigger.trycloudflare.com")
        self.url_entry = tk.Entry(c_row, textvariable=self.url_var, font=("Segoe UI", 10), bg="#0F1117", fg="#FFFFFF", insertbackground="#00E676", bd=6, relief="flat")
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        tk.Button(c_row, text="📋 Paste", font=("Segoe UI", 9, "bold"), bg="#252C3A", fg="#FFFFFF", bd=0, padx=10, pady=4, cursor="hand2", command=self._paste_clipboard).pack(side="left", padx=(0, 8))

        self.connect_btn = tk.Button(c_row, text="CONNECT", font=("Segoe UI", 9, "bold"), bg="#00C853", fg="#FFFFFF", bd=0, padx=14, pady=4, cursor="hand2", command=self._toggle_connection)
        self.connect_btn.pack(side="right")

        emu_info_row = tk.Frame(conn_card, bg="#161B26")
        emu_info_row.pack(fill="x", padx=12, pady=(0, 4))
        self.emu_lbl = tk.Label(emu_info_row, text="Emulator: Detecting...", font=("Segoe UI", 8), fg="#00E676", bg="#161B26")
        self.emu_lbl.pack(side="left")
        tk.Button(emu_info_row, text="🔄 Rescan Port", font=("Segoe UI", 8), fg="#8A93A6", bg="#161B26", bd=0, cursor="hand2", command=self._rescan_emulator).pack(side="right")

        # 2. Main Remote Bot Controls (Action Buttons)
        ctrl_card = tk.LabelFrame(main_container, text=" 🎮 BOT ACTIONS & CONTROLS ", font=("Segoe UI", 9, "bold"), fg="#9E9E9E", bg="#161B26", bd=1, relief="solid")
        ctrl_card.pack(fill="x", pady=(0, 10), padx=2, ipady=8)

        btn_row = tk.Frame(ctrl_card, bg="#161B26")
        btn_row.pack(fill="x", padx=12, pady=6)

        self.start_btn = tk.Button(btn_row, text="▶ START BOT", font=("Segoe UI", 11, "bold"), bg="#00C853", fg="#FFFFFF", bd=0, pady=8, cursor="hand2", command=self._start_bot)
        self.start_btn.pack(side="left", fill="x", expand=True, padx=(0, 6))

        self.pause_btn = tk.Button(btn_row, text="⏸ PAUSE", font=("Segoe UI", 11, "bold"), bg="#FFA000", fg="#FFFFFF", bd=0, pady=8, cursor="hand2", command=self._pause_bot)
        self.pause_btn.pack(side="left", fill="x", expand=True, padx=6)

        self.stop_btn = tk.Button(btn_row, text="⏹ STOP", font=("Segoe UI", 11, "bold"), bg="#D50000", fg="#FFFFFF", bd=0, pady=8, cursor="hand2", command=self._stop_bot)
        self.stop_btn.pack(side="right", fill="x", expand=True, padx=(6, 0))

        self.bot_state_lbl = tk.Label(ctrl_card, text="Status: Bot is Idle (Ready to Start)", font=("Segoe UI", 9, "bold"), fg="#8A93A6", bg="#161B26")
        self.bot_state_lbl.pack(pady=(4, 0))

        # 3. Tactical Configuration Card
        cfg_card = tk.LabelFrame(main_container, text=" ⚔️ COMBAT & TACTICAL STRATEGY ", font=("Segoe UI", 9, "bold"), fg="#9E9E9E", bg="#161B26", bd=1, relief="solid")
        cfg_card.pack(fill="x", pady=(0, 10), padx=2, ipady=8)

        # Strategy selection
        strat_row = tk.Frame(cfg_card, bg="#161B26")
        strat_row.pack(fill="x", padx=12, pady=4)
        tk.Label(strat_row, text="Attack Strategy:", font=("Segoe UI", 9, "bold"), fg="#D0D5DD", bg="#161B26").pack(side="left")

        self.strat_var = tk.StringVar(value="Sneaky Goblins & Jump (Storage Rush)")
        strat_combo = ttk.Combobox(
            strat_row,
            textvariable=self.strat_var,
            values=[
                "Sneaky Goblins & Jump (Storage Rush)",
                "Barch & Goblins (Collector Sweeper)",
                "Electro Dragon & Heroes Assault",
                "Smart Dead-Base Collector Harvest",
            ],
            state="readonly",
            width=38,
            font=("Segoe UI", 9),
        )
        strat_combo.pack(side="right")

        # Loot filters
        loot_row = tk.Frame(cfg_card, bg="#161B26")
        loot_row.pack(fill="x", padx=12, pady=8)

        # Min Gold
        tk.Label(loot_row, text="Min Gold:", font=("Segoe UI", 8), fg="#FFD54F", bg="#161B26").pack(side="left")
        self.min_gold_var = tk.StringVar(value="400000")
        tk.Entry(loot_row, textvariable=self.min_gold_var, font=("Segoe UI", 8), width=10, bg="#0F1117", fg="#FFF", bd=4, relief="flat").pack(side="left", padx=(4, 12))

        # Min Elixir
        tk.Label(loot_row, text="Min Elixir:", font=("Segoe UI", 8), fg="#E040FB", bg="#161B26").pack(side="left")
        self.min_elixir_var = tk.StringVar(value="400000")
        tk.Entry(loot_row, textvariable=self.min_elixir_var, font=("Segoe UI", 8), width=10, bg="#0F1117", fg="#FFF", bd=4, relief="flat").pack(side="left", padx=(4, 12))

        # Min Dark Elixir
        tk.Label(loot_row, text="Min DE:", font=("Segoe UI", 8), fg="#80D8FF", bg="#161B26").pack(side="left")
        self.min_de_var = tk.StringVar(value="3000")
        tk.Entry(loot_row, textvariable=self.min_de_var, font=("Segoe UI", 8), width=8, bg="#0F1117", fg="#FFF", bd=4, relief="flat").pack(side="left", padx=(4, 0))

        # Feature Checkboxes
        chk_row = tk.Frame(cfg_card, bg="#161B26")
        chk_row.pack(fill="x", padx=12, pady=(2, 6))

        self.auto_walls = tk.BooleanVar(value=True)
        self.auto_train = tk.BooleanVar(value=True)
        self.auto_collect = tk.BooleanVar(value=True)
        self.auto_builder = tk.BooleanVar(value=False)

        tk.Checkbutton(chk_row, text="Auto Upgrade Walls", variable=self.auto_walls, bg="#161B26", fg="#FFF", selectcolor="#0F1117", font=("Segoe UI", 8)).pack(side="left", padx=(0, 10))
        tk.Checkbutton(chk_row, text="Auto Train Army", variable=self.auto_train, bg="#161B26", fg="#FFF", selectcolor="#0F1117", font=("Segoe UI", 8)).pack(side="left", padx=(0, 10))
        tk.Checkbutton(chk_row, text="Harvest Collectors", variable=self.auto_collect, bg="#161B26", fg="#FFF", selectcolor="#0F1117", font=("Segoe UI", 8)).pack(side="left", padx=(0, 10))
        tk.Checkbutton(chk_row, text="Builder Base Boost", variable=self.auto_builder, bg="#161B26", fg="#FFF", selectcolor="#0F1117", font=("Segoe UI", 8)).pack(side="left")

        # 4. Live Telemetry Badges
        stats_frame = tk.Frame(main_container, bg="#0F1117")
        stats_frame.pack(fill="x", pady=(0, 10))

        self.gold_badge = self._create_stat_badge(stats_frame, "GOLD LOOTED", "0", "#FFD54F")
        self.elixir_badge = self._create_stat_badge(stats_frame, "ELIXIR LOOTED", "0", "#E040FB")
        self.de_badge = self._create_stat_badge(stats_frame, "DARK ELIXIR", "0", "#80D8FF")
        self.wins_badge = self._create_stat_badge(stats_frame, "ATTACKS WON", "0", "#00E676")

        # 5. Live Activity Log
        log_card = tk.LabelFrame(main_container, text=" 📜 LIVE BOT ACTIVITY TELEMETRY ", font=("Segoe UI", 9, "bold"), fg="#9E9E9E", bg="#161B26", bd=1, relief="solid")
        log_card.pack(fill="both", expand=True, padx=2)

        self.log_text = tk.Text(log_card, font=("Consolas", 8), bg="#0A0C10", fg="#CFD8DC", bd=6, relief="flat", wrap="word")
        self.log_text.pack(fill="both", expand=True, padx=8, pady=8)

        self._log("Remote Control Dashboard initialized. Click CONNECT to link with bot server.")

    def _create_stat_badge(self, parent: tk.Frame, title: str, val: str, color: str) -> tk.Label:
        box = tk.Frame(parent, bg="#161B26", bd=1, relief="solid")
        box.pack(side="left", fill="both", expand=True, padx=3)
        tk.Label(box, text=title, font=("Segoe UI", 7, "bold"), fg="#8A93A6", bg="#161B26").pack(pady=(4, 0))
        lbl = tk.Label(box, text=val, font=("Segoe UI", 12, "bold"), fg=color, bg="#161B26")
        lbl.pack(pady=(0, 4))
        return lbl

    def _paste_clipboard(self) -> None:
        try:
            content = self.root.clipboard_get()
            self.url_var.set(content.strip())
            self._log("Pasted server URL.")
        except Exception:
            pass

    def _rescan_emulator(self) -> None:
        self.emu_port, name = detect_emulator()
        self.emu_lbl.config(text=f"Emulator: {name} (127.0.0.1:{self.emu_port})")
        self._log(f"Detected {name} on port {self.emu_port}")

    def _log(self, text: str) -> None:
        ts = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{ts}] {text}\n")
        self.log_text.see("end")

    def _update_status(self, text: str, color: str) -> None:
        self.status_badge.config(text=text, fg=color)

    def _toggle_connection(self) -> None:
        if not self.is_connected:
            raw_url = self.url_var.get().strip()
            if not raw_url:
                messagebox.showwarning("Missing Link", "Please enter the Server URL.")
                return
            normalized_url = normalize_ws_url(raw_url)
            self._log(f"Connecting to {normalized_url}...")
            self._update_status("● CONNECTING...", "#FFD600")
            self.connect_btn.config(text="DISCONNECT", bg="#D50000")
            self.url_entry.config(state="disabled")
            self.is_connected = True

            self.thread = threading.Thread(target=self._run_async_worker, args=(normalized_url,), daemon=True)
            self.thread.start()
        else:
            self._disconnect()

    def _disconnect(self) -> None:
        self.is_connected = False
        self.bot_running = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self._update_status("● OFFLINE", "#FF5252")
        self.connect_btn.config(text="CONNECT", bg="#00C853")
        self.url_entry.config(state="normal")
        self.bot_state_lbl.config(text="Status: Bot is Idle (Disconnected)", fg="#8A93A6")
        self._log("Disconnected from bot server.")

    # Bot Control Dispatchers
    def _start_bot(self) -> None:
        if not self.is_connected or not self.active_ws:
            messagebox.showwarning("Not Connected", "Please connect to the server first!")
            return

        config = {
            "strategy": self.strat_var.get(),
            "min_gold": int(self.min_gold_var.get() or "400000"),
            "min_elixir": int(self.min_elixir_var.get() or "400000"),
            "min_de": int(self.min_de_var.get() or "3000"),
            "auto_walls": self.auto_walls.get(),
            "auto_train": self.auto_train.get(),
            "auto_collect": self.auto_collect.get(),
            "auto_builder": self.auto_builder.get(),
        }

        cmd_payload = json.dumps({"action": "start", "config": config}).encode("utf-8")
        frame = struct.pack("!IB", 1 + len(cmd_payload), MSG_BOT_CONTROL) + cmd_payload

        asyncio.run_coroutine_threadsafe(self.active_ws.send(frame), self.loop)
        self.bot_running = True
        self.bot_state_lbl.config(text=f"Status: RUNNING - Strategy: {self.strat_var.get()}", fg="#00E676")
        self._log(f"Command sent: START BOT ({self.strat_var.get()})")

    def _pause_bot(self) -> None:
        if not self.is_connected or not self.active_ws:
            return
        cmd_payload = json.dumps({"action": "pause"}).encode("utf-8")
        frame = struct.pack("!IB", 1 + len(cmd_payload), MSG_BOT_CONTROL) + cmd_payload
        asyncio.run_coroutine_threadsafe(self.active_ws.send(frame), self.loop)
        self.bot_state_lbl.config(text="Status: PAUSED", fg="#FFA000")
        self._log("Command sent: PAUSE BOT")

    def _stop_bot(self) -> None:
        if not self.is_connected or not self.active_ws:
            return
        cmd_payload = json.dumps({"action": "stop"}).encode("utf-8")
        frame = struct.pack("!IB", 1 + len(cmd_payload), MSG_BOT_CONTROL) + cmd_payload
        asyncio.run_coroutine_threadsafe(self.active_ws.send(frame), self.loop)
        self.bot_running = False
        self.bot_state_lbl.config(text="Status: STOPPED", fg="#D50000")
        self._log("Command sent: STOP BOT")

    # Async WebSocket Loop
    def _run_async_worker(self, url: str) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_worker_loop(url))
        except Exception as e:
            self.root.after(0, self._log, f"Session finished: {e}")
        finally:
            self.root.after(0, self._disconnect)

    async def _async_worker_loop(self, url: str) -> None:
        while self.is_connected:
            try:
                async with websockets.connect(url, max_size=32 * 1024 * 1024, ping_interval=20, ping_timeout=20) as ws:
                    self.active_ws = ws

                    # Authenticate
                    auth_bytes = self.token.encode("utf-8")
                    auth_frame = struct.pack("!IB", 1 + len(auth_bytes), MSG_AUTH) + auth_bytes
                    await ws.send(auth_frame)

                    reply = await asyncio.wait_for(ws.recv(), timeout=10)
                    if not isinstance(reply, bytes) or len(reply) < 5 or reply[4] != MSG_AUTH_OK:
                        self.root.after(0, self._log, "Authentication rejected by server.")
                        return

                    self.root.after(0, self._log, "Connected & authenticated with ClashBot Server!")
                    self.root.after(0, self._update_status, "● ONLINE & ACTIVE", "#00E676")

                    # Listen for commands & telemetry from server
                    async for raw in ws:
                        if not self.is_connected:
                            break
                        if isinstance(raw, bytes) and len(raw) >= 5:
                            msg_type = raw[4]
                            payload = raw[5:]

                            if msg_type == MSG_OPEN_CHANNEL:
                                (ch_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                                asyncio.create_task(self._open_channel(ch_id, ws))

                            elif msg_type == MSG_CHANNEL_DATA:
                                (ch_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                                data = payload[4:]
                                ch = self.channels.get(ch_id)
                                if ch:
                                    _, emu_w = ch
                                    emu_w.write(data)
                                    await emu_w.drain()

                            elif msg_type == MSG_CLOSE_CHANNEL:
                                (ch_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                                ch = self.channels.pop(ch_id, None)
                                if ch:
                                    _, emu_w = ch
                                    try:
                                        emu_w.close()
                                    except Exception:
                                        pass

                            elif msg_type == MSG_BOT_TELEMETRY:
                                try:
                                    telemetry = json.loads(payload.decode("utf-8"))
                                    self.root.after(0, self._handle_telemetry, telemetry)
                                except Exception:
                                    pass

            except Exception as e:
                if not self.is_connected:
                    break
                self.root.after(0, self._log, f"Connection warning: {e}. Reconnecting...")
                self.root.after(0, self._update_status, "● RECONNECTING...", "#FFD600")
                await asyncio.sleep(5)

    def _handle_telemetry(self, t: dict) -> None:
        if "state" in t:
            self.bot_state_lbl.config(text=f"Status: {t['state']}", fg="#00E676")
        if "gold" in t:
            self.gold_badge.config(text=f"{t['gold']:,}")
        if "elixir" in t:
            self.elixir_badge.config(text=f"{t['elixir']:,}")
        if "de" in t:
            self.de_badge.config(text=f"{t['de']:,}")
        if "wins" in t:
            self.wins_badge.config(text=str(t["wins"]))
        if "log" in t:
            self._log(t["log"])

    async def _open_channel(self, channel_id: int, ws: websockets.WebSocketClientProtocol) -> None:
        try:
            emu_r, emu_w = await asyncio.open_connection("127.0.0.1", self.emu_port)
            self.channels[channel_id] = (emu_r, emu_w)

            reply = struct.pack("!IB", 5, MSG_CHANNEL_OPENED) + CHANNEL_STRUCT.pack(channel_id)
            await ws.send(reply)

            while self.is_connected:
                data = await emu_r.read(65536)
                if not data:
                    break
                payload = CHANNEL_STRUCT.pack(channel_id) + data
                frame = struct.pack("!IB", 1 + len(payload), MSG_CHANNEL_DATA) + payload
                await ws.send(frame)
        except Exception:
            pass
        finally:
            self.channels.pop(channel_id, None)
            try:
                close_frame = struct.pack("!IB", 5, MSG_CLOSE_CHANNEL) + CHANNEL_STRUCT.pack(channel_id)
                await ws.send(close_frame)
            except Exception:
                pass


def main() -> None:
    root = tk.Tk()
    app = RemoteBotDashboard(root)
    root.mainloop()


if __name__ == "__main__":
    main()
