# -*- coding: utf-8 -*-
"""ClashBot AI - Resilient adbutils.errors stub."""

class AdbError(Exception):
    """Base adb error."""
    pass


class AdbTimeout(AdbError):
    """Timeout communicating with adb-server."""
    pass


class AdbConnectionError(AdbError):
    """Connection error communicating with adb-server."""
    pass


class AdbInstallError(AdbError):
    def __init__(self, output: str = ""):
        self.output = str(output)
        self.reason = "Unknown"

    def __str__(self):
        return self.output


__all__ = [
    "AdbError",
    "AdbTimeout",
    "AdbConnectionError",
    "AdbInstallError",
]
