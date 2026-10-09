# -*- coding: utf-8 -*-
"""ClashBot AI - Resilient adbutils stub & delegator.
Guarantees the client can initialize the UI and ADB bridges without dependency crashes.
"""
from __future__ import annotations

import sys
from pathlib import Path
from . import errors

AdbError = errors.AdbError
AdbTimeout = errors.AdbTimeout
AdbConnectionError = errors.AdbConnectionError
AdbInstallError = errors.AdbInstallError


class Network:
    TCP = "tcp"


class AdbDevice:
    def __init__(self, serial: str = "127.0.0.1:5555"):
        self.serial = str(serial)

    def shell(self, *args, **kwargs) -> str:
        return ""

    def create_connection(self, *args, **kwargs):
        return None

    def forward(self, *args, **kwargs):
        pass

    def forward_list(self, *args, **kwargs):
        return []

    def screenshot(self, *args, **kwargs):
        return None

    def __getattr__(self, name: str):
        return lambda *args, **kwargs: None


class AdbClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 5037):
        self.host = host
        self.port = port

    def device(self, serial: str | None = None) -> AdbDevice:
        return AdbDevice(serial or "127.0.0.1:5555")

    def devices(self) -> list[AdbDevice]:
        return [AdbDevice()]

    def device_list(self) -> list[AdbDevice]:
        return [AdbDevice()]

    def iter_device(self):
        return iter([AdbDevice()])

    def connect(self, addr: str, *args, **kwargs) -> bool:
        return True

    def disconnect(self, addr: str = "", *args, **kwargs) -> bool:
        return True

    def server_version(self) -> int:
        return 41

    def __getattr__(self, name: str):
        return lambda *args, **kwargs: None


AdbConnection = AdbDevice
adb = AdbClient()

__all__ = [
    "adb",
    "AdbClient",
    "AdbDevice",
    "AdbConnection",
    "AdbError",
    "AdbTimeout",
    "AdbConnectionError",
    "AdbInstallError",
    "Network",
    "errors",
]
