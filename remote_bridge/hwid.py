# -*- coding: utf-8 -*-
"""ClashBot AI - Hardware Identification (HWID) Fingerprinting Module.

Computes a deterministic, tamper-resistant, machine-specific HWID on Windows.
Formatted as: CB-XXXX-XXXX-XXXX (e.g., CB-9F00-36A4-ABF3).
"""

from __future__ import annotations

import hashlib
import os
import platform
import subprocess
import sys
import uuid

_CACHED_HWID: str | None = None


def get_machine_guid() -> str:
    """Retrieve Windows installation MachineGuid from registry."""
    if sys.platform == "win32":
        try:
            import winreg
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography")
            val, _ = winreg.QueryValueEx(key, "MachineGuid")
            winreg.CloseKey(key)
            if val and len(str(val).strip()) > 10:
                return str(val).strip().lower()
        except Exception:
            pass
    return ""


def get_system_uuid() -> str:
    """Retrieve Motherboard / BIOS UUID via WMIC or PowerShell on Windows."""
    if sys.platform == "win32":
        # 1. Try PowerShell CimInstance
        try:
            res = subprocess.run(
                ["powershell", "-NoProfile", "-Command", "(Get-CimInstance Win32_ComputerSystemProduct).UUID"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            out = res.stdout.strip()
            if out and len(out) > 10 and "error" not in out.lower():
                return out.lower()
        except Exception:
            pass

        # 2. Try wmic fallback
        try:
            res = subprocess.run(
                ["wmic", "csproduct", "get", "uuid"],
                capture_output=True,
                text=True,
                timeout=2,
            )
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip() and "uuid" not in l.lower()]
            if lines and len(lines[0]) > 10:
                return lines[0].lower()
        except Exception:
            pass

    return ""


def get_mac_address() -> str:
    """Retrieve primary network interface MAC address."""
    try:
        node = uuid.getnode()
        if (node >> 40) % 2 == 0:  # Valid non-random MAC
            return hex(node)[2:].zfill(12).lower()
    except Exception:
        pass
    return ""


def get_hwid() -> str:
    """Compute and return formatted ClashBot HWID (e.g. CB-9F00-36A4-ABF3)."""
    global _CACHED_HWID
    if _CACHED_HWID:
        return _CACHED_HWID

    # Gather hardware components
    m_guid = get_machine_guid()
    s_uuid = get_system_uuid()
    mac = get_mac_address()
    node = platform.node().strip().lower()

    # Raw entropy string
    raw_str = f"CLASHBOT:{m_guid}:{s_uuid}:{mac}:{node}"

    # SHA256 digest
    digest = hashlib.sha256(raw_str.encode("utf-8")).hexdigest().upper()

    # Format into standard 12-hex-character chunks
    formatted = f"CB-{digest[:4]}-{digest[4:8]}-{digest[8:12]}"
    _CACHED_HWID = formatted
    return formatted


def get_system_metadata() -> dict:
    """Return dictionary of system hardware info for telemetry and logging."""
    return {
        "hwid": get_hwid(),
        "hostname": platform.node(),
        "os": f"{platform.system()} {platform.release()}",
        "architecture": platform.machine(),
    }


if __name__ == "__main__":
    print(f"ClashBot HWID: {get_hwid()}")
    print(f"System Metadata: {get_system_metadata()}")
