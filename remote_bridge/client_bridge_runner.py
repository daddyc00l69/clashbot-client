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

    def _find_emulator_executables(self) -> list[tuple[str, str]]:
        """Find installed emulator executables on Windows."""
        import os
        results = []
        cfg_paths = [
            os.path.join(os.path.dirname(__file__), "..", "src", "profiles", "config.json"),
            os.path.join(os.path.dirname(__file__), "..", "profiles", "config.json"),
        ]
        preferred = ""
        custom_paths = {}
        for p in cfg_paths:
            if os.path.isfile(p):
                try:
                    with open(p, "r", encoding="utf-8") as f:
                        cd = json.load(f)
                        preferred = cd.get("EMULATOR_SELECTION", "").lower()
                        custom_paths = cd.get("EMULATOR_INSTALL_PATHS", {})
                    break
                except Exception:
                    pass

        for emu_key, emu_path in custom_paths.items():
            if emu_path and os.path.isfile(emu_path):
                results.append((emu_key.capitalize(), emu_path))

        standard_candidates = [
            ("BlueStacks", [
                r"C:\Program Files\BlueStacks_nxt\HD-Player.exe",
                r"C:\Program Files (x86)\BlueStacks_nxt\HD-Player.exe",
                r"C:\Program Files\BlueStacks\HD-Player.exe",
            ]),
            ("LDPlayer", [
                r"C:\LDPlayer\LDPlayer9\dnplayer.exe",
                r"C:\LDPlayer\LDPlayer14\dnplayer.exe",
                r"C:\LDPlayer\dnplayer.exe",
                r"D:\LDPlayer\LDPlayer9\dnplayer.exe",
                r"D:\LDPlayer\LDPlayer14\dnplayer.exe",
                r"D:\LDPlayer\dnplayer.exe",
            ]),
            ("MuMu", [
                r"C:\Program Files\Netease\MuMuPlayer\nx_main\MuMuNxMain.exe",
                r"C:\Program Files\Netease\MuMuPlayer\shell\MuMuPlayer.exe",
                r"C:\Program Files\MuMuPlayer\nx_main\MuMuNxMain.exe",
                r"C:\Program Files\MuMuPlayer\shell\MuMuPlayer.exe",
                r"C:\Program Files\Netease\MuMuPlayerGlobal-12.0\shell\MuMuPlayer.exe",
                r"C:\Program Files\Netease\MuMuPlayer-12.0\shell\MuMuPlayer.exe",
            ]),
            ("NoxPlayer", [
                r"C:\Program Files\Nox\bin\Nox.exe",
                r"C:\Program Files (x86)\Nox\bin\Nox.exe",
            ]),
        ]

        for name, paths in standard_candidates:
            if preferred and preferred in name.lower():
                for p in paths:
                    if os.path.isfile(p) and (name, p) not in results:
                        results.insert(0, (name, p))
            else:
                for p in paths:
                    if os.path.isfile(p) and (name, p) not in results:
                        results.append((name, p))

        return results

    def _build_emulator_command(self, name: str, exe_path: str, instance_str: str = "") -> list[str]:
        """Build exact command line to boot the Android device VM, avoiding bare launcher window."""
        import os, re
        cmd = [exe_path]
        name_lower = name.lower()

        inst_val = ""
        if instance_str and ":" in instance_str:
            inst_val = instance_str.split(":", 1)[1].strip()
        elif instance_str:
            inst_val = instance_str.strip()

        if "mumu" in name_lower:
            # MuMu 12 / 6: '-v <index>' boots the actual Android instance
            idx = inst_val if inst_val.isdigit() else "0"
            cmd.extend(["-v", idx])
        elif "ldplayer" in name_lower:
            # LDPlayer: 'index=<index>' boots the actual Android instance
            idx = inst_val if inst_val.isdigit() else "0"
            cmd.append(f"index={idx}")
        elif "bluestacks" in name_lower:
            # BlueStacks: '--instance <name>'
            inst_name = inst_val if inst_val and inst_val != "default" else ""
            if not inst_name:
                for conf_p in [r"C:\ProgramData\BlueStacks_nxt\bluestacks.conf", r"C:\ProgramData\BlueStacks\bluestacks.conf"]:
                    if os.path.isfile(conf_p):
                        try:
                            with open(conf_p, "r", encoding="utf-8", errors="ignore") as f:
                                for line in f:
                                    if "bst.installed_images" in line:
                                        m = re.search(r'=\s*["\']?([^"\'\r\n]+)', line)
                                        if m:
                                            inst_name = m.group(1).split(",")[0].strip()
                                            break
                        except Exception:
                            pass
            if not inst_name:
                inst_name = "Pie64"
            cmd.extend(["--instance", inst_name])
        elif "nox" in name_lower:
            idx = inst_val if inst_val.isdigit() else "0"
            cmd.append(f"-clone:Nox_{idx}")

        return cmd

    def try_auto_launch_emulator(self) -> int | None:
        """Attempt to automatically locate and launch installed emulator if it is closed."""
        candidates = self._find_emulator_executables()
        if not candidates:
            return None

        name, exe_path = candidates[0]
        pref_inst = getattr(self, "preferred_instance", "")
        launch_cmd = self._build_emulator_command(name, exe_path, pref_inst)

        print("=" * 68)
        print(f"[*] Android emulator is closed. Launching Android device: {name}...")
        print(f"[*] Executable: {exe_path}")
        print(f"[*] Command   : {' '.join(launch_cmd)}")
        print("=" * 68)
        try:
            import subprocess
            subprocess.Popen(launch_cmd, close_fds=True)
        except Exception as e:
            print(f"[!] Could not launch emulator automatically: {e}")
            return None

        print("[*] Waiting for Android device to boot and initialize ADB (up to 60s)...")
        start_time = time.time()
        common_ports = [self.emulator_port, 16384, 16416, 5555, 5554, 21503, 7555, 62001, 58526]
        while time.time() - start_time < 60:
            time.sleep(2)
            for port in common_ports:
                try:
                    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                        s.settimeout(0.3)
                        if s.connect_ex(("127.0.0.1", port)) == 0:
                            print(f"[+] {name} Android device online! ADB active on 127.0.0.1:{port}")
                            self.emulator_port = port
                            return port
                except Exception:
                    pass
        print("[!] Timed out waiting for emulator ADB. Please ensure ADB is enabled in emulator settings.")
        return None

    def scan_emulator_port(self) -> int | None:
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

        # If not running, automatically launch installed emulator!
        launched_port = self.try_auto_launch_emulator()
        if launched_port is not None:
            return launched_port

        print("=" * 68)
        print("[!] WARNING: No running Android emulator automatically detected!")
        print("[*] Please ensure BlueStacks, LDPlayer, or MuMu is RUNNING with ADB enabled.")
        print("[*] Common emulator ports checked: 5555, 5554, 16384 (MuMu 12), 7555, 21503.")
        print("=" * 68)
        return None

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
            connect_kwargs = {
                "max_size": 32 * 1024 * 1024,
                "ping_interval": 20,
                "ping_timeout": 20,
            }
            import inspect
            sig = inspect.signature(websockets.connect)
            bypass_headers = {"Bypass-Tunnel-Reminder": "true", "User-Agent": "Mozilla/5.0"}
            if "additional_headers" in sig.parameters:
                connect_kwargs["additional_headers"] = bypass_headers
            elif "extra_headers" in sig.parameters:
                connect_kwargs["extra_headers"] = bypass_headers

            async with websockets.connect(
                ws_url,
                **connect_kwargs,
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
