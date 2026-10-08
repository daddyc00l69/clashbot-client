"""ClashBot AI - Remote Client GUI.

A sleek, modern dark-themed desktop application for the client worker.
Allows friends/users to paste the server URL, auto-detect their emulator,
and connect with one click.
"""

from __future__ import annotations

import asyncio
import re
import socket
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import messagebox, ttk

import websockets

# Message Types
MSG_AUTH = 0x01
MSG_AUTH_OK = 0x02
MSG_AUTH_FAIL = 0x03
MSG_OPEN_CHANNEL = 0x10
MSG_CHANNEL_OPENED = 0x11
MSG_CHANNEL_DATA = 0x12
MSG_CLOSE_CHANNEL = 0x13

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


class ClientWorkerGUI:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("ClashBot AI - Client Bridge")
        self.root.geometry("540x580")
        self.root.minsize(480, 520)
        self.root.configure(bg="#12151B")

        # Connection state
        self.is_connected = False
        self.loop: asyncio.AbstractEventLoop | None = None
        self.thread: threading.Thread | None = None
        self.channels: dict[int, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self.active_ws = None
        self.token = "clashbot-secret-key-2026"

        self._build_ui()
        self._rescan_emulator()

    def _build_ui(self) -> None:
        # Top Header Banner
        header = tk.Frame(self.root, bg="#1A1F29", height=80)
        header.pack(fill="x", side="top")

        title_lbl = tk.Label(
            header,
            text="CLASHBOT AI",
            font=("Segoe UI", 16, "bold"),
            fg="#00E676",
            bg="#1A1F29",
        )
        title_lbl.pack(anchor="w", padx=20, pady=(15, 2))

        sub_lbl = tk.Label(
            header,
            text="Autonomous Game Intelligence • Remote Device Bridge",
            font=("Segoe UI", 9),
            fg="#8A93A6",
            bg="#1A1F29",
        )
        sub_lbl.pack(anchor="w", padx=20, pady=(0, 15))

        # Main Content Card
        card = tk.Frame(self.root, bg="#12151B")
        card.pack(fill="both", expand=True, padx=20, pady=15)

        # 1. Server Link Input
        url_lbl = tk.Label(card, text="SERVER URL (Cloudflare Link or IP)", font=("Segoe UI", 9, "bold"), fg="#D0D5DD", bg="#12151B")
        url_lbl.pack(anchor="w", pady=(0, 5))

        url_row = tk.Frame(card, bg="#12151B")
        url_row.pack(fill="x", pady=(0, 15))

        self.url_var = tk.StringVar(value="https://holmes-recruiting-heat-bigger.trycloudflare.com")
        self.url_entry = tk.Entry(
            url_row,
            textvariable=self.url_var,
            font=("Segoe UI", 10),
            bg="#1E232F",
            fg="#FFFFFF",
            insertbackground="#00E676",
            relief="flat",
            bd=8,
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(0, 8))

        paste_btn = tk.Button(
            url_row,
            text="📋 Paste",
            font=("Segoe UI", 9, "bold"),
            bg="#2A3142",
            fg="#FFFFFF",
            activebackground="#3A435A",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=12,
            pady=6,
            cursor="hand2",
            command=self._paste_clipboard,
        )
        paste_btn.pack(side="right")

        # 2. Emulator Detection Row
        emu_lbl = tk.Label(card, text="LOCAL EMULATOR STATUS", font=("Segoe UI", 9, "bold"), fg="#D0D5DD", bg="#12151B")
        emu_lbl.pack(anchor="w", pady=(0, 5))

        emu_row = tk.Frame(card, bg="#1E232F", bd=8)
        emu_row.pack(fill="x", pady=(0, 15))

        self.emu_status_lbl = tk.Label(
            emu_row,
            text="Scanning for BlueStacks / LDPlayer...",
            font=("Segoe UI", 9),
            fg="#00E676",
            bg="#1E232F",
        )
        self.emu_status_lbl.pack(side="left", fill="x", expand=True)

        rescan_btn = tk.Button(
            emu_row,
            text="🔄 Rescan",
            font=("Segoe UI", 8, "bold"),
            bg="#2A3142",
            fg="#FFFFFF",
            relief="flat",
            bd=0,
            padx=8,
            pady=3,
            cursor="hand2",
            command=self._rescan_emulator,
        )
        rescan_btn.pack(side="right")

        # 3. Connect Button
        self.connect_btn = tk.Button(
            card,
            text="⚡ CONNECT TO SERVER",
            font=("Segoe UI", 12, "bold"),
            bg="#00C853",
            fg="#FFFFFF",
            activebackground="#00B0FF",
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            pady=10,
            cursor="hand2",
            command=self._toggle_connection,
        )
        self.connect_btn.pack(fill="x", pady=(5, 15))

        # 4. Status Indicator Badge
        status_row = tk.Frame(card, bg="#12151B")
        status_row.pack(fill="x", pady=(0, 5))

        tk.Label(status_row, text="CONNECTION STATUS:", font=("Segoe UI", 8, "bold"), fg="#8A93A6", bg="#12151B").pack(side="left")

        self.status_badge = tk.Label(
            status_row,
            text="● DISCONNECTED",
            font=("Segoe UI", 8, "bold"),
            fg="#FF5252",
            bg="#12151B",
        )
        self.status_badge.pack(side="left", padx=8)

        # 5. Activity Log Box
        self.log_text = tk.Text(
            card,
            font=("Consolas", 8),
            bg="#0D0F14",
            fg="#B0BEC5",
            insertbackground="#00E676",
            relief="flat",
            bd=6,
            height=8,
            wrap="word",
        )
        self.log_text.pack(fill="both", expand=True)
        self._log("Ready. Paste the Server Link above and click Connect.")

    def _paste_clipboard(self) -> None:
        try:
            content = self.root.clipboard_get()
            self.url_var.set(content.strip())
            self._log("Pasted link from clipboard.")
        except Exception:
            pass

    def _rescan_emulator(self) -> None:
        self.emu_port, name = detect_emulator()
        self.emu_status_lbl.config(text=f"Detected: {name} (Port {self.emu_port})")
        self._log(f"Emulator scan: {name} found on 127.0.0.1:{self.emu_port}")

    def _log(self, text: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        self.log_text.insert("end", f"[{timestamp}] {text}\n")
        self.log_text.see("end")

    def _update_status(self, text: str, color: str) -> None:
        self.status_badge.config(text=text, fg=color)

    def _toggle_connection(self) -> None:
        if not self.is_connected:
            url = self.url_var.get().strip()
            if not url:
                messagebox.showwarning("Missing Link", "Please paste the Server URL before connecting.")
                return

            normalized_url = normalize_ws_url(url)
            self._log(f"Initiating connection to {normalized_url}...")
            self._update_status("● CONNECTING...", "#FFD600")
            self.connect_btn.config(text="DISCONNECT", bg="#D50000")
            self.url_entry.config(state="disabled")
            self.is_connected = True

            # Start asyncio in background thread
            self.thread = threading.Thread(target=self._run_async_worker, args=(normalized_url,), daemon=True)
            self.thread.start()
        else:
            self._disconnect()

    def _disconnect(self) -> None:
        self.is_connected = False
        if self.loop and self.loop.is_running():
            self.loop.call_soon_threadsafe(self.loop.stop)
        self._update_status("● DISCONNECTED", "#FF5252")
        self.connect_btn.config(text="⚡ CONNECT TO SERVER", bg="#00C853")
        self.url_entry.config(state="normal")
        self._log("Disconnected from server.")

    def _run_async_worker(self, url: str) -> None:
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._async_worker_loop(url))
        except Exception as e:
            self.root.after(0, self._log, f"Connection ended: {e}")
        finally:
            self.root.after(0, self._handle_worker_exit)

    def _handle_worker_exit(self) -> None:
        if self.is_connected:
            self._disconnect()

    async def _async_worker_loop(self, url: str) -> None:
        while self.is_connected:
            try:
                self.root.after(0, self._log, f"Connecting to WebSocket...")
                async with websockets.connect(url, max_size=32 * 1024 * 1024, ping_interval=20, ping_timeout=20) as ws:
                    self.active_ws = ws

                    # 1. Authenticate
                    auth_bytes = self.token.encode("utf-8")
                    auth_frame = struct.pack("!IB", 1 + len(auth_bytes), MSG_AUTH) + auth_bytes
                    await ws.send(auth_frame)

                    reply = await asyncio.wait_for(ws.recv(), timeout=10)
                    if not isinstance(reply, bytes) or len(reply) < 5 or reply[4] != MSG_AUTH_OK:
                        self.root.after(0, self._log, "Authentication failed! Invalid token.")
                        return

                    self.root.after(0, self._log, "Authentication successful! Bridge is ACTIVE.")
                    self.root.after(0, self._update_status, "● ONLINE & ACTIVE", "#00E676")

                    # Handle messages
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

            except Exception as e:
                if not self.is_connected:
                    break
                self.root.after(0, self._log, f"Connection warning: {e}. Reconnecting in 5s...")
                self.root.after(0, self._update_status, "● RECONNECTING...", "#FFD600")
                await asyncio.sleep(5)

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
    app = ClientWorkerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
