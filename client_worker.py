"""Remote ADB Client Worker.

Runs on your FRIEND'S LAPTOP (the Client).
Requires ZERO third-party libraries (uses only standard Python).
Contains ZERO bot source code, templates, or AI logic.

Connects to your Server PC and securely bridges the friend's local emulator
(BlueStacks, LDPlayer, MuMu, MEmu) so the server can control it.
"""

from __future__ import annotations

import argparse
import asyncio
import socket
import struct
import sys
import time

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
    """Scan common ports to auto-detect a running emulator."""
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
    print("[!] No running emulator automatically detected on common ports.")
    print("[*] Defaulting to port 5555 (Standard ADB).")
    return 5555


class ClientWorker:
    def __init__(self, server_host: str, server_port: int, token: str, emulator_port: int) -> None:
        self.server_host = server_host
        self.server_port = server_port
        self.token = token
        self.emulator_port = emulator_port
        self.channels: dict[int, tuple[asyncio.StreamReader, asyncio.StreamWriter]] = {}

    async def run(self) -> None:
        print("=" * 65)
        print("CLASHBOT AI - CLIENT WORKER")
        print("=" * 65)
        print(f"[+] Server Address : {self.server_host}:{self.server_port}")
        print(f"[+] Local Emulator : 127.0.0.1:{self.emulator_port}")
        print(f"[+] Status         : Connecting to server...")
        print("=" * 65)

        while True:
            try:
                reader, writer = await asyncio.open_connection(self.server_host, self.server_port)
                print(f"[OK] Connected to Server at {self.server_host}:{self.server_port}")

                # Authenticate
                auth_payload = self.token.encode("utf-8")
                writer.write(struct.pack("!IB", 1 + len(auth_payload), MSG_AUTH) + auth_payload)
                await writer.drain()

                # Read auth reply
                len_bytes = await reader.readexactly(4)
                (length,) = struct.unpack("!I", len_bytes)
                reply = await reader.readexactly(length)
                if reply[0] != MSG_AUTH_OK:
                    reason = reply[1:].decode("utf-8", errors="ignore")
                    print(f"[-] Authentication failed: {reason}")
                    writer.close()
                    await writer.wait_closed()
                    return

                print(f"[OK] Authentication successful! Bridge is now ACTIVE.")
                print(f"[OK] Your friend's server can now interact with your local emulator.")

                # Process tunnel commands
                await self._tunnel_loop(reader, writer)

            except (ConnectionRefusedError, OSError) as e:
                print(f"[!] Cannot connect to server ({e}). Retrying in 5 seconds...")
                await asyncio.sleep(5)
            except asyncio.IncompleteReadError:
                print("[-] Server disconnected. Retrying in 3 seconds...")
                await asyncio.sleep(3)
            except Exception as e:
                print(f"[-] Connection error: {e}. Retrying in 5 seconds...")
                await asyncio.sleep(5)

    async def _tunnel_loop(self, tunnel_reader: asyncio.StreamReader, tunnel_writer: asyncio.StreamWriter) -> None:
        while True:
            len_bytes = await tunnel_reader.readexactly(4)
            (length,) = struct.unpack("!I", len_bytes)
            frame = await tunnel_reader.readexactly(length)

            msg_type = frame[0]
            payload = frame[1:]

            if msg_type == MSG_OPEN_CHANNEL:
                (channel_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                asyncio.create_task(self._open_channel(channel_id, tunnel_writer))

            elif msg_type == MSG_CHANNEL_DATA:
                (channel_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                data = payload[4:]
                ch = self.channels.get(channel_id)
                if ch:
                    _, emu_w = ch
                    emu_w.write(data)
                    await emu_w.drain()

            elif msg_type == MSG_CLOSE_CHANNEL:
                (channel_id,) = CHANNEL_STRUCT.unpack(payload[:4])
                ch = self.channels.pop(channel_id, None)
                if ch:
                    _, emu_w = ch
                    try:
                        emu_w.close()
                    except Exception:
                        pass

    async def _open_channel(self, channel_id: int, tunnel_writer: asyncio.StreamWriter) -> None:
        """Connect to local emulator (127.0.0.1:emulator_port) and pipe to tunnel."""
        try:
            emu_r, emu_w = await asyncio.open_connection("127.0.0.1", self.emulator_port)
            self.channels[channel_id] = (emu_r, emu_w)

            # Inform server channel is open
            reply = struct.pack("!IB", 5, MSG_CHANNEL_OPENED) + CHANNEL_STRUCT.pack(channel_id)
            tunnel_writer.write(reply)
            await tunnel_writer.drain()

            # Pipe from emulator back to tunnel
            while True:
                data = await emu_r.read(65536)
                if not data:
                    break
                payload = CHANNEL_STRUCT.pack(channel_id) + data
                tunnel_writer.write(struct.pack("!IB", 1 + len(payload), MSG_CHANNEL_DATA) + payload)
                await tunnel_writer.drain()
        except Exception:
            pass
        finally:
            self.channels.pop(channel_id, None)
            try:
                close_frame = struct.pack("!IB", 5, MSG_CLOSE_CHANNEL) + CHANNEL_STRUCT.pack(channel_id)
                tunnel_writer.write(close_frame)
                await tunnel_writer.drain()
            except Exception:
                pass


def main() -> None:
    parser = argparse.ArgumentParser(description="ClashBot AI Client Worker")
    parser.add_argument("--server", default="192.168.0.9", help="Server IP or hostname")
    parser.add_argument("--port", type=int, default=9999, help="Server bridge port")
    parser.add_argument("--token", default="clashbot-secret-key-2026", help="Secret token")
    parser.add_argument("--emulator-port", type=int, default=None, help="Local emulator ADB port (e.g. 5555)")
    args = parser.parse_args()

    emu_port = args.emulator_port or detect_local_emulator()
    worker = ClientWorker(server_host=args.server, server_port=args.port, token=args.token, emulator_port=emu_port)

    try:
        asyncio.run(worker.run())
    except KeyboardInterrupt:
        print("\n[*] Worker stopped by user.")


if __name__ == "__main__":
    main()
