# -*- coding: utf-8 -*-
"""
ClashBot AI - Client Remote Engine Runner
Allows the authentic PySide6 ClashBot AI interface to run on the client laptop,
while all attack, farming, and vision intelligence execute securely on the server.
"""

from __future__ import annotations

import asyncio
import functools
import json
import os
import socket
import struct
import sys
import threading
import time
from pathlib import Path

# Safe print with flush
print = functools.partial(print, flush=True)

# Protocol definitions
from remote_bridge.protocol import (
    CHANNEL_STRUCT,
    MSG_AUTH,
    MSG_AUTH_FAIL,
    MSG_AUTH_OK,
    MSG_BOT_CONTROL,
    MSG_BOT_TELEMETRY,
    MSG_CHANNEL_DATA,
    MSG_CHANNEL_OPENED,
    MSG_CLOSE_CHANNEL,
    MSG_OPEN_CHANNEL,
    MSG_PING,
    MSG_PONG,
    pack_channel_cmd,
    pack_data,
    pack_frame,
)


class ClientRemoteEngine:
    def __init__(self, server_url: str, token: str, emulator_port: int = 5555, stats=None) -> None:
        self.server_url = server_url
        self.token = token
        self.emulator_port = emulator_port
        self.stats = stats

        self.channels: dict[int, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}
        self.running = True
        self.ws = None
        self.loop = None

    def scan_emulator_port(self) -> int:
        """Scan common Android emulator ADB ports to auto-detect active emulator."""
        common_ports = [self.emulator_port, 5555, 5554, 16384, 21503, 7555, 62001, 58526]
        seen = set()
        for port in common_ports:
            if port in seen:
                continue
            seen.add(port)
            try:
                s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                s.settimeout(0.2)
                res = s.connect_ex(("127.0.0.1", port))
                s.close()
                if res == 0:
                    print(f"[+] Detected active Android emulator on 127.0.0.1:{port}")
                    self.emulator_port = port
                    return port
            except Exception:
                pass
        print(f"[*] Defaulting to emulator port: 127.0.0.1:{self.emulator_port}")
        return self.emulator_port

    def get_ws_url(self) -> str:
        url = self.server_url.strip()
        if url.startswith("https://"):
            url = "wss://" + url[8:]
        elif url.startswith("http://"):
            url = "ws://" + url[7:]
        elif not url.startswith("ws://") and not url.startswith("wss://"):
            url = f"wss://{url}"
        if not url.endswith("/ws") and not url.endswith("/"):
            url = f"{url}/ws"
        return url

    async def run(self, config_dict: dict | None = None) -> None:
        import websockets

        ws_url = self.get_ws_url()
        print("=" * 68)
        print("CLASHBOT AI - CONNECTING TO SECURE CLOUD ENGINE")
        print("=" * 68)
        print(f"[+] Cloud Server  : {ws_url}")
        print(f"[+] Local Emulator: 127.0.0.1:{self.emulator_port}")
        print("[*] Initiating secure WebSocket bridge connection...")

        try:
            async with websockets.connect(
                ws_url,
                max_size=32 * 1024 * 1024,
                ping_interval=20,
                ping_timeout=20,
            ) as ws:
                self.ws = ws
                print("[+] Tunnel connection opened. Authenticating...")

                # 1. Send auth frame
                await ws.send(pack_frame(MSG_AUTH, self.token.encode("utf-8")))
                resp = await ws.recv()
                if not isinstance(resp, bytes) or len(resp) < 5 or resp[4] != MSG_AUTH_OK:
                    print("[-] Authentication rejected by server! Check token or server URL.")
                    return

                print("[OK] Authentication successful! Secure session established.")
                print("[+] Synchronizing village profiles with server...")

                # 2. Send Start Bot Control Command with config
                start_payload = json.dumps({
                    "action": "start",
                    "config": config_dict or {},
                }).encode("utf-8")
                await ws.send(pack_frame(MSG_BOT_CONTROL, start_payload))

                print("[+] Remote Bot Engine active! Receiving live combat telemetry...")
                print("=" * 68)

                # 3. Handle messages from server
                async for raw in ws:
                    if not self.running:
                        break
                    if isinstance(raw, bytes) and len(raw) >= 5:
                        msg_type = raw[4]
                        payload = raw[5:]

                        if msg_type == MSG_OPEN_CHANNEL:
                            (ch_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                            asyncio.create_task(self._open_channel(ch_id))

                        elif msg_type == MSG_CHANNEL_DATA:
                            (ch_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                            data = payload[4:]
                            ch = self.channels.get(ch_id)
                            if ch:
                                _, ch_w = ch
                                ch_w.write(data)
                                await ch_w.drain()

                        elif msg_type == MSG_CLOSE_CHANNEL:
                            (ch_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                            ch = self.channels.pop(ch_id, None)
                            if ch:
                                _, ch_w = ch
                                try:
                                    ch_w.close()
                                except Exception:
                                    pass

                        elif msg_type == MSG_BOT_TELEMETRY:
                            self._handle_telemetry(payload)

                        elif msg_type == MSG_PING:
                            await ws.send(pack_frame(MSG_PONG, b""))

        except Exception as e:
            if self.running:
                print(f"[-] Connection to Cloud Server lost: {e}")
        finally:
            print("[+] Session disconnected cleanly.")

    async def _open_channel(self, ch_id: int) -> None:
        try:
            r, w = await asyncio.open_connection("127.0.0.1", self.emulator_port)
            self.channels[ch_id] = (r, w)
            if self.ws:
                await self.ws.send(pack_channel_cmd(MSG_CHANNEL_OPENED, ch_id))
            asyncio.create_task(self._pump_channel_to_server(ch_id, r))
        except Exception as e:
            if self.ws:
                await self.ws.send(pack_channel_cmd(MSG_CLOSE_CHANNEL, ch_id))

    async def _pump_channel_to_server(self, ch_id: int, r: asyncio.StreamReader) -> None:
        try:
            while self.running and ch_id in self.channels:
                data = await r.read(64 * 1024)
                if not data:
                    break
                if self.ws:
                    await self.ws.send(pack_data(ch_id, data))
        except Exception:
            pass
        finally:
            self.channels.pop(ch_id, None)
            if self.ws:
                try:
                    await self.ws.send(pack_channel_cmd(MSG_CLOSE_CHANNEL, ch_id))
                except Exception:
                    pass

    def _handle_telemetry(self, payload: bytes) -> None:
        try:
            data = json.loads(payload.decode("utf-8"))
            log_line = data.get("log")
            if log_line:
                # Print directly to stdout so PySide6 MainWindow / TeeStream captures it
                print(log_line)

            # Update live stats if stats object was passed
            if self.stats:
                if "gold" in data and hasattr(self.stats, "gold_looted"):
                    self.stats.gold_looted = data["gold"]
                if "elixir" in data and hasattr(self.stats, "elixir_looted"):
                    self.stats.elixir_looted = data["elixir"]
                if "de" in data and hasattr(self.stats, "dark_elixir_looted"):
                    self.stats.dark_elixir_looted = data["de"]
                if "wins" in data and hasattr(self.stats, "attacks_won"):
                    self.stats.attacks_won = data["wins"]
        except Exception:
            pass

    def stop(self) -> None:
        self.running = False
        if self.ws and self.loop:
            async def _send_stop():
                try:
                    stop_payload = json.dumps({"action": "stop"}).encode("utf-8")
                    await self.ws.send(pack_frame(MSG_BOT_CONTROL, stop_payload))
                    await self.ws.close()
                except Exception:
                    pass
            asyncio.run_coroutine_threadsafe(_send_stop(), self.loop)
