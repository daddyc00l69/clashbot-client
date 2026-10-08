"""Remote ADB Client Worker with Cloudflare Tunnel & WebSocket support.

Runs on your FRIEND'S LAPTOP (the Client).
Connects to your Server via a Cloudflare public link (wss://xxxx.trycloudflare.com)
or a local address (ws://192.168.x.x:8765) and bridges the local emulator.
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import struct
import sys
import time

import websockets

# Message Types
MSG_AUTH = 0x01
MSG_AUTH_OK = 0x02
MSG_AUTH_FAIL = 0x03
MSG_OPEN_CHANNEL = 0x10
MSG_CHANNEL_OPENED = 0x11
MSG_CHANNEL_DATA = 0x12
MSG_CLOSE_CHANNEL = 0x13
MSG_PING = 0x20
MSG_PONG = 0x21

CHANNEL_STRUCT = struct.Struct("!I")

COMMON_EMULATOR_PORTS = [
    (5555, "BlueStacks / LDPlayer / Generic"),
    (16384, "MuMu Player 12"),
    (7555, "MuMu Player 6"),
    (62001, "NoxPlayer / LDPlayer alt"),
    (21503, "MEmu Play"),
]


def detect_local_emulator() -> int:
    """Scan common ports to auto-detect a running emulator, or auto-launch if closed."""
    print("[*] Scanning for active Android emulators on this computer...")
    for port, name in COMMON_EMULATOR_PORTS:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(0.2)
            try:
                if s.connect_ex(("127.0.0.1", port)) == 0:
                    print(f"[OK] Detected {name} on port {port}!")
                    return port
            except Exception:
                pass

    # Try auto-launching installed emulator if closed
    import os, subprocess
    candidates = [
        ("BlueStacks", [r"C:\Program Files\BlueStacks_nxt\HD-Player.exe", r"C:\Program Files (x86)\BlueStacks_nxt\HD-Player.exe"]),
        ("LDPlayer", [r"C:\LDPlayer\LDPlayer9\dnplayer.exe", r"C:\LDPlayer\dnplayer.exe"]),
        ("MuMu", [r"C:\Program Files\Netease\MuMuPlayer\nx_main\MuMuNxMain.exe", r"C:\Program Files\MuMuPlayer\nx_main\MuMuNxMain.exe"]),
    ]
    for emu_name, paths in candidates:
        for p in paths:
            if os.path.isfile(p):
                cmd = [p]
                if emu_name == "MuMu":
                    cmd.extend(["-v", "0"])
                elif emu_name == "LDPlayer":
                    cmd.append("index=0")
                elif emu_name == "BlueStacks":
                    cmd.extend(["--instance", "Pie64"])

                print(f"[*] Emulator is closed. Launching Android device: {' '.join(cmd)}...")
                try:
                    subprocess.Popen(cmd, close_fds=True)
                    print("[*] Waiting for Android device to boot and open ADB (up to 60s)...")
                    start_t = time.time()
                    while time.time() - start_t < 60:
                        time.sleep(2)
                        for port, name in COMMON_EMULATOR_PORTS:
                            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                                s.settimeout(0.3)
                                if s.connect_ex(("127.0.0.1", port)) == 0:
                                    print(f"[OK] {emu_name} online on port {port}!")
                                    return port
                except Exception as e:
                    print(f"[!] Auto-launch error: {e}")
                break

    print("[!] No running emulator automatically detected on common ports.")
    print("[*] Defaulting to port 5555 (Standard ADB).")
    return 5555


import re


def normalize_ws_url(raw_url: str) -> str:
    """Robustly extract and normalize Cloudflare or local WebSocket URL."""
    text = raw_url.strip().strip('"').strip("'")
    # Extract URL if user accidentally pasted label or prefix like "Paste Server URL: https://..."
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


class WebSocketClientWorker:
    def __init__(self, server_url: str, token: str, emulator_port: int) -> None:
        self.server_url = normalize_ws_url(server_url)
        self.token = token
        self.emulator_port = emulator_port
        self.channels: dict[int, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}

    async def run(self) -> None:
        print("=" * 70)
        print("CLASHBOT AI - CLIENT WORKER")
        print("=" * 70)
        print(f"[+] Server URL     : {self.server_url}")
        print(f"[+] Local Emulator : 127.0.0.1:{self.emulator_port}")
        print(f"[+] Status         : Connecting to server...")
        print("=" * 70)

        while True:
            try:
                async with websockets.connect(self.server_url, max_size=32 * 1024 * 1024, ping_interval=20, ping_timeout=20) as ws:
                    print(f"[OK] Connected to Server at {self.server_url}")

                    # Authenticate
                    auth_bytes = self.token.encode("utf-8")
                    auth_frame = struct.pack("!IB", 1 + len(auth_bytes), MSG_AUTH) + auth_bytes
                    await ws.send(auth_frame)

                    # Read reply
                    reply = await asyncio.wait_for(ws.recv(), timeout=10)
                    if not isinstance(reply, bytes) or len(reply) < 5 or reply[4] != MSG_AUTH_OK:
                        reason = reply[5:].decode("utf-8", errors="ignore") if isinstance(reply, bytes) and len(reply) > 5 else "Failed"
                        print(f"[-] Authentication failed: {reason}")
                        return

                    print(f"[OK] Authentication successful! Bridge is now ACTIVE.")
                    print(f"[OK] Your friend's server can now control your local emulator.")

                    await self._ws_loop(ws)

            except (websockets.exceptions.WebSocketException, OSError, asyncio.TimeoutError) as e:
                print(f"[!] Connection dropped/failed ({e}). Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except Exception as e:
                print(f"[-] Unexpected error: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def _ws_loop(self, ws: websockets.WebSocketClientProtocol) -> None:
        async for raw in ws:
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

    async def _open_channel(self, channel_id: int, ws: websockets.WebSocketClientProtocol) -> None:
        """Connect to local emulator (127.0.0.1:emulator_port) and pipe to WebSocket."""
        try:
            emu_r, emu_w = await asyncio.open_connection("127.0.0.1", self.emulator_port)
            self.channels[channel_id] = (emu_r, emu_w)

            # Inform server channel is open
            reply = struct.pack("!IB", 5, MSG_CHANNEL_OPENED) + CHANNEL_STRUCT.pack(channel_id)
            await ws.send(reply)

            # Pipe from emulator back to WebSocket
            while True:
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
    parser = argparse.ArgumentParser(description="ClashBot AI WebSocket Client Worker")
    parser.add_argument("--server", required=True, help="Server URL or IP (e.g. https://xxx.trycloudflare.com or 192.168.0.9:8765)")
    parser.add_argument("--token", default="clashbot-secret-key-2026", help="Secret token")
    parser.add_argument("--emulator-port", type=int, default=None, help="Local emulator ADB port (e.g. 5555)")
    args = parser.parse_args()

    emu_port = args.emulator_port or detect_local_emulator()
    worker = WebSocketClientWorker(server_url=args.server, token=args.token, emulator_port=emu_port)

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("\n[*] Worker stopped by user.")


if __name__ == "__main__":
    main()
