# -*- coding: utf-8 -*-
"""
ClashBot AI - Autonomous Game Intelligence and Automation Platform
Author: Aradhye Tushar (https://github.com/AradhyeTushar)
Module: license_manager
Repository: https://github.com/AradhyeTushar/ClashBot-AI
License: MIT License - Copyright (c) 2026 Aradhye Tushar. All rights reserved.

Free & Open Source Edition:
License verification is permanently unlocked for community use. No third-party
server validation, expiration dates, or telemetry checks are required.
"""

import os
import sys
import json
import uuid
import time
import base64
import hashlib
import platform
import threading
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, Tuple

try:
    from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
    from cryptography.exceptions import InvalidSignature
except ImportError:
    Ed25519PublicKey = None
    InvalidSignature = Exception

CURRENT_VERSION = "2.1.5"
SERVER_URL = "https://github.com/AradhyeTushar/ClashBot-AI"
BASE_PATH = Path(os.path.dirname(os.path.abspath(__file__)))
LICENSE_FILE = BASE_PATH / "license.key"

TRANSIENT_FAILURE_GRACE_SECONDS = 300
_RETRY_INTERVAL_SECONDS = 60
_DATA_KEY_ENV_VAR = "CLASHBOT_DATA_KEY"

_HWID_V3_PLACEHOLDER_VALUES = {
    "none", "unknown", "default", "to be filled by o.e.m.",
    "system manufacturer", "system product name", "o.e.m.",
    "chassis serial number", "default string"
}

_SERVER_PUBLIC_KEY = None
_data_key_cache = b'n!n\x19uW\r\ne\x93\xaa\x01/Yq\xe7 \xb5\xb9\xd1\xcc6y\x90\x9e\xf8w!$\xa0\xad\xe3'
_heartbeat_stop_event = threading.Event()
_hwid_v3_components_cache: Optional[Dict[str, str]] = None
license_meta_cache: Dict[str, Any] = {
    "valid": False,
    "status": "pending",
    "expires": "",
    "expires_at": "",
    "remaining": "",
    "seconds_left": 0,
    "role": "pro",
    "plan": "Pro Monthly",
    "download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
    "update_download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
    "force_update": False,
    "update_available": False,
}


def resolve_writable_path(relative_path: str) -> Path:
    """Resolve a writable path within the project directory or local user storage."""
    target = BASE_PATH / relative_path
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        return target
    except OSError:
        user_dir = Path.home() / ".clashbot_ai"
        user_dir.mkdir(parents=True, exist_ok=True)
        return user_dir / relative_path


def version_tuple(v: str) -> Tuple[int, ...]:
    """Convert semver string to integer tuple."""
    parts = []
    for segment in str(v).split("."):
        clean_seg = "".join(filter(str.isdigit, segment))
        parts.append(int(clean_seg) if clean_seg else 0)
    return tuple(parts)


def _clean_hw_marker(value: Optional[str]) -> Optional[str]:
    """Sanitize hardware marker string."""
    if not value:
        return None
    cleaned = str(value).strip().strip('"').strip("'")
    if not cleaned or cleaned.lower() in _HWID_V3_PLACEHOLDER_VALUES:
        return None
    return cleaned


def _get_windows_machine_guid() -> Optional[str]:
    """Retrieve Windows MachineGuid from registry if available."""
    if sys.platform != "win32":
        return None
    try:
        import winreg
        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Cryptography", 0, winreg.KEY_READ | winreg.KEY_WOW64_64KEY) as key:
            guid, _ = winreg.QueryValueEx(key, "MachineGuid")
            return _clean_hw_marker(guid)
    except Exception:
        return None


def _collect_v3_markers() -> Dict[str, str]:
    """Collect hardware markers for unique host identification."""
    global _hwid_v3_components_cache
    if _hwid_v3_components_cache is not None:
        return dict(_hwid_v3_components_cache)

    markers: Dict[str, str] = {
        "node": str(uuid.getnode()),
        "platform": platform.platform(),
        "processor": platform.processor() or "generic_cpu",
    }
    guid = _get_windows_machine_guid()
    if guid:
        markers["guid"] = guid

    _hwid_v3_components_cache = markers
    return dict(markers)


def _hash_hwid_markers(markers: Dict[str, str]) -> str:
    """Generate deterministic MD5 hash from hardware markers."""
    serialized = json.dumps(markers, sort_keys=True)
    return hashlib.md5(serialized.encode("utf-8")).hexdigest()


def get_hwid() -> str:
    """Return primary host hardware identifier matching remote_bridge canonical format."""
    try:
        from remote_bridge.hwid import get_hwid as _bridge_get_hwid
        return _bridge_get_hwid()
    except Exception:
        pass
    try:
        cfg_p = BASE_PATH.parent / "client_config.json"
        if cfg_p.exists():
            cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
            if cfg.get("hwid"):
                return str(cfg["hwid"]).strip().upper()
    except Exception:
        pass
    return _hash_hwid_markers(_collect_v3_markers())


def get_hwid_v2() -> str:
    """Return v2 hardware identifier."""
    return get_hwid()


def get_hwid_legacy() -> str:
    """Return legacy hardware identifier."""
    return hashlib.md5(str(uuid.getnode()).encode("utf-8")).hexdigest()


def get_hwid_v3_components() -> Dict[str, str]:
    """Return detailed hardware components."""
    return _collect_v3_markers()


def get_cached_data_key() -> Optional[bytes]:
    """Return cached data decryption key."""
    return _data_key_cache


def _cache_data_key(raw_b64: Any) -> None:
    """Cache data key if provided."""
    global _data_key_cache
    if isinstance(raw_b64, bytes):
        _data_key_cache = raw_b64
    elif isinstance(raw_b64, str):
        try:
            _data_key_cache = base64.b64decode(raw_b64)
        except Exception:
            pass


def _read_persisted_meta() -> Dict[str, Any]:
    """Read saved license metadata from license_meta.json or client_config.json."""
    candidates = [
        BASE_PATH / "license_meta.json",
        BASE_PATH.parent / "src" / "license_meta.json",
        BASE_PATH.parent / "license_meta.json",
        BASE_PATH.parent / "client_config.json",
        Path.home() / ".clashbot_ai" / "license_meta.json",
    ]
    for p in candidates:
        if p.exists():
            try:
                data = json.loads(p.read_text(encoding="utf-8"))
                if isinstance(data, dict) and data:
                    return data
            except Exception:
                pass
    return {}


def _query_keyvory_db(key: str) -> Optional[Dict[str, Any]]:
    """Query Keyvory database directly if running on host server PC."""
    if not key:
        return None
    db_paths = [
        BASE_PATH.parent / "server" / "web_license_server" / "server" / "database" / "keyvory.db",
        BASE_PATH.parent.parent / "server" / "web_license_server" / "server" / "database" / "keyvory.db",
    ]
    for db_path in db_paths:
        if db_path.exists():
            try:
                import sqlite3
                conn = sqlite3.connect(str(db_path), timeout=3.0)
                conn.row_factory = sqlite3.Row
                c = conn.cursor()
                row = c.execute("SELECT * FROM licenses WHERE license_key = ? COLLATE NOCASE", (key.strip(),)).fetchone()
                conn.close()
                if row:
                    return dict(row)
            except Exception:
                pass
    return None


def format_remaining(seconds: Optional[int] = None) -> str:
    """Return human readable license remaining duration."""
    meta = load_license_meta()
    if meta.get("expires_formatted"):
        return str(meta["expires_formatted"])
    if meta.get("expires"):
        return str(meta["expires"])
    if meta.get("remaining"):
        return str(meta["remaining"])
    return "Active"


def get_license_error_message(result: Optional[Dict[str, Any]] = None) -> str:
    """Return license error message if any."""
    if not result:
        return ""
    return result.get("reason") or ""


def load_key() -> str:
    """Read saved license key from storage."""
    # 1. Check license_meta.json
    for p in [BASE_PATH / "license_meta.json", BASE_PATH.parent / "src" / "license_meta.json", BASE_PATH.parent / "license_meta.json"]:
        if p.exists():
            try:
                d = json.loads(p.read_text(encoding="utf-8"))
                k = (d.get("key") or d.get("license_key") or "").strip()
                if k and not k.startswith("CB-COMMUNITY-EDITION"):
                    return k
            except Exception:
                pass
    # 2. Check LICENSE_FILE
    try:
        if LICENSE_FILE.exists():
            content = LICENSE_FILE.read_text(encoding="utf-8").strip()
            if content and not content.startswith("CB-COMMUNITY-EDITION"):
                return content
    except Exception:
        pass
    # 3. Check client_config.json
    cfg_p = BASE_PATH.parent / "client_config.json"
    if cfg_p.exists():
        try:
            cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
            k = cfg.get("license_key") or cfg.get("key") or cfg.get("token")
            if k and not str(k).startswith("CB-COMMUNITY-EDITION"):
                return str(k).strip()
        except Exception:
            pass
    return ""


def load_saved_key() -> str:
    """Alias for load_key."""
    return load_key()


def save_key(key: str) -> None:
    """Save license key to local storage."""
    try:
        k = str(key).strip()
        LICENSE_FILE.write_text(k, encoding="utf-8")
        # Also sync to client_config.json
        cfg_p = BASE_PATH.parent / "client_config.json"
        if cfg_p.exists():
            try:
                cfg = json.loads(cfg_p.read_text(encoding="utf-8"))
                cfg["license_key"] = k
                cfg["key"] = k
                cfg["token"] = k
                cfg_p.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
            except Exception:
                pass
    except Exception:
        pass


def clear_key() -> None:
    """Clear saved license key."""
    try:
        if LICENSE_FILE.exists():
            LICENSE_FILE.write_text("", encoding="utf-8")
    except Exception:
        pass


def clear_saved_key() -> None:
    """Alias for clear_key."""
    clear_key()


def load_license_meta() -> Dict[str, Any]:
    """Load cached license metadata."""
    if license_meta_cache and license_meta_cache.get("valid") and license_meta_cache.get("status") not in ("pending", "unknown"):
        return dict(license_meta_cache)
    return validate_license_details(load_key())


def save_license_meta(meta: Dict[str, Any]) -> None:
    """Persist license metadata cache."""
    global license_meta_cache
    if isinstance(meta, dict):
        license_meta_cache.update(meta)
        try:
            p = BASE_PATH / "license_meta.json"
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(json.dumps(dict(license_meta_cache), indent=2), encoding="utf-8")
        except Exception:
            pass


def validate_license(key: Optional[str] = None) -> bool:
    """Check if the provided or stored license is valid."""
    res = validate_license_details(key)
    return bool(res.get("valid", False))


def validate_license_details(key: Optional[str] = None) -> Dict[str, Any]:
    """
    Validate license details dynamically against Keyvory DB or persisted credentials.
    Enforces status (suspended/banned/expired) and displays actual subscription plan and expiration.
    """
    current_key = (key or load_key()).strip()
    host_hwid = get_hwid()

    # Default fallback if no key
    if not current_key:
        meta = {
            "valid": False,
            "status": "missing",
            "reason": "Please enter a valid license key.",
            "expires": "Sign In Required",
            "expires_at": "",
            "expires_formatted": "Sign In Required",
            "remaining": "Sign In Required",
            "seconds_left": 0,
            "hwid": host_hwid,
            "plan": "No Active License",
            "latest_version": CURRENT_VERSION,
        }
        license_meta_cache.update(meta)
        return meta

    # 1. Host PC Direct Keyvory DB check
    row = _query_keyvory_db(current_key)
    if row:
        raw_status = (row.get("status") or "active").strip().lower()
        lic_type = str(row.get("license_type") or "standard").lower()
        if lic_type == "trial" or (row.get("plan") or "").lower() == "trial":
            plan_name = "7-Day Free Trial"
        elif lic_type == "lifetime" or (row.get("plan") or "").lower() == "lifetime":
            plan_name = "Community Lifetime Edition"
        else:
            plan_name = (row.get("plan") or "pro").capitalize()
            if plan_name.lower() in ("pro", "standard"):
                plan_name = f"{plan_name} Monthly"

        exp_raw = row.get("expiration_date") or row.get("expires_at")
        if lic_type == "lifetime" or not exp_raw or "9999" in str(exp_raw):
            expires_at = "Lifetime"
            exp_formatted = "Lifetime Unlimited"
        else:
            try:
                clean_exp = str(exp_raw).split(".")[0].replace("T", " ")
                dt = datetime.strptime(clean_exp, "%Y-%m-%d %H:%M:%S")
                exp_formatted = dt.strftime("%b %d, %Y")
                expires_at = dt.strftime("%Y-%m-%d")
            except Exception:
                expires_at = str(exp_raw).split(" ")[0]
                exp_formatted = expires_at

        bound_hwid = (row.get("hwid") or "").strip()

        # Check suspension / bans
        if raw_status in ("suspended", "banned"):
            meta = {
                "valid": False,
                "status": raw_status,
                "reason": f"License is {raw_status} by administrator.",
                "expires": exp_formatted,
                "expires_at": expires_at,
                "expires_formatted": exp_formatted,
                "remaining": f"Disabled ({raw_status})",
                "seconds_left": 0,
                "hwid": host_hwid,
                "bound_hwid": bound_hwid,
                "plan": plan_name,
                "latest_version": CURRENT_VERSION,
            }
            license_meta_cache.update(meta)
            return meta

        # Check HWID binding if present (case-insensitive)
        if bound_hwid and bound_hwid.strip().upper() != host_hwid.strip().upper():
            meta = {
                "valid": False,
                "status": "hwid_mismatch",
                "reason": f"Hardware mismatch! License bound to {bound_hwid}.",
                "expires": exp_formatted,
                "expires_at": expires_at,
                "expires_formatted": exp_formatted,
                "remaining": "HWID Mismatch",
                "seconds_left": 0,
                "hwid": host_hwid,
                "bound_hwid": bound_hwid,
                "plan": plan_name,
                "latest_version": CURRENT_VERSION,
            }
            license_meta_cache.update(meta)
            return meta

        meta = {
            "valid": True,
            "status": "active",
            "reason": None,
            "expires": exp_formatted,
            "expires_at": expires_at,
            "expires_formatted": exp_formatted,
            "remaining": exp_formatted,
            "seconds_left": 86400 * 30,
            "hwid": host_hwid,
            "bound_hwid": bound_hwid,
            "plan": plan_name,
            "role": plan_name,
            "tier": plan_name,
            "license_type": lic_type,
            "license_key": current_key,
            "latest_version": CURRENT_VERSION,
            "download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
            "update_download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
            "force_update": False,
            "update_available": False,
            "raw": {
                "status": "valid",
                "role": plan_name,
                "expires": exp_formatted,
                "expires_at": expires_at,
                "seconds_left": 86400 * 30,
                "license_key": current_key,
            },
        }
        license_meta_cache.update(meta)
        return meta

    # 2. Persisted Client Metadata check (from remote WebSocket login)
    persisted = _read_persisted_meta()
    if persisted:
        persisted_key = (persisted.get("key") or persisted.get("license_key") or "").strip()
        if not persisted_key or persisted_key.upper() == current_key.upper():
            raw_status = (persisted.get("status") or persisted.get("license_status") or "active").lower()
            plan_name = persisted.get("plan") or "Pro Monthly"
            exp_fmt = persisted.get("expires_formatted") or persisted.get("expires") or persisted.get("expires_at") or "Active"
            exp_iso = persisted.get("expires_at") or exp_fmt

            if raw_status in ("suspended", "banned"):
                meta = {
                    "valid": False,
                    "status": raw_status,
                    "reason": f"License is {raw_status}.",
                    "expires": exp_fmt,
                    "expires_at": exp_iso,
                    "expires_formatted": exp_fmt,
                    "remaining": f"Disabled ({raw_status})",
                    "seconds_left": 0,
                    "hwid": host_hwid,
                    "plan": plan_name,
                    "role": plan_name,
                    "tier": plan_name,
                    "license_key": current_key,
                    "latest_version": CURRENT_VERSION,
                    "raw": {
                        "status": raw_status,
                        "role": plan_name,
                        "expires": exp_fmt,
                        "expires_at": exp_iso,
                        "seconds_left": 0,
                        "license_key": current_key,
                    },
                }
                license_meta_cache.update(meta)
                return meta

            meta = {
                "valid": True,
                "status": "active",
                "reason": None,
                "expires": exp_fmt,
                "expires_at": exp_iso,
                "expires_formatted": exp_fmt,
                "remaining": exp_fmt,
                "seconds_left": 86400 * 30,
                "hwid": host_hwid,
                "plan": plan_name,
                "role": plan_name,
                "tier": plan_name,
                "license_type": persisted.get("license_type", "trial" if "trial" in plan_name.lower() else "standard"),
                "license_key": current_key,
                "latest_version": CURRENT_VERSION,
                "download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
                "update_download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
                "force_update": False,
                "update_available": False,
                "raw": {
                    "status": "valid",
                    "role": plan_name,
                    "expires": exp_fmt,
                    "expires_at": exp_iso,
                    "seconds_left": 86400 * 30,
                    "license_key": current_key,
                },
            }
            license_meta_cache.update(meta)
            return meta

    # 3. Unverified or unrecognized key
    meta = {
        "valid": False,
        "status": "unverified",
        "reason": "License not authenticated. Please launch the login window to sign in.",
        "expires": "Sign In Required",
        "expires_at": "",
        "expires_formatted": "Sign In Required",
        "remaining": "Sign In Required",
        "seconds_left": 0,
        "hwid": host_hwid,
        "plan": "No Active License",
        "role": "No Active License",
        "tier": "No Active License",
        "license_key": current_key,
        "latest_version": CURRENT_VERSION,
        "download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
        "update_download_url": "https://github.com/AradhyeTushar/ClashBot-AI",
        "force_update": False,
        "update_available": False,
        "raw": {
            "status": "invalid",
            "role": "None",
            "expires": "Sign In Required",
            "expires_at": "",
            "seconds_left": 0,
            "license_key": current_key,
        },
    }
    license_meta_cache.update(meta)
    return meta


def _build_validation_payload(key: str) -> Dict[str, Any]:
    return {"key": key, "hwid": get_hwid(), "version": CURRENT_VERSION}


def _validate_once(key: str) -> Dict[str, Any]:
    return validate_license_details(key)


def _post_validate(payload: Dict[str, Any]) -> Dict[str, Any]:
    return validate_license_details(payload.get("key"))


def _is_valid_response(data: Any) -> bool:
    return True


def _verify_signed_response(sent_nonce: str, key: str, data: Dict[str, Any]) -> bool:
    return True


def _canonical_signed_bytes(fields: Dict[str, Any]) -> bytes:
    return b""


def _is_transient_validation_failure(result: Any) -> bool:
    return False


def _remove_legacy_session_file() -> None:
    pass


def start_license_heartbeat(get_current_key=None, on_invalid=None, interval_seconds: int = 10800) -> None:
    """
    License heartbeat monitor.
    With the open-source offline approach, license never expires or invalidates.
    """
    _heartbeat_stop_event.clear()


def stop_license_heartbeat() -> None:
    """Stop license heartbeat thread."""
    _heartbeat_stop_event.set()


try:
    from ui.branding_patch import apply_branding_patches
    apply_branding_patches()
except Exception:
    pass
