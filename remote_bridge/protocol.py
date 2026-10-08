"""Binary framing and message types for the remote ADB tunnel."""

from __future__ import annotations

import struct

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
MSG_BOT_CONTROL = 0x30
MSG_BOT_CONFIG = 0x31
MSG_BOT_TELEMETRY = 0x32
MSG_FAST_SCREENSHOT_REQ = 0x40
MSG_FAST_SCREENSHOT_RESP = 0x41


HEADER_STRUCT = struct.Struct("!IB")  # 4 bytes payload length, 1 byte type
CHANNEL_STRUCT = struct.Struct("!I")  # 4 bytes channel_id


def pack_frame(msg_type: int, payload: bytes = b"") -> bytes:
    length = 1 + len(payload)
    return struct.pack("!IB", length, msg_type) + payload


def pack_data(channel_id: int, data: bytes) -> bytes:
    payload = CHANNEL_STRUCT.pack(channel_id) + data
    length = 1 + len(payload)
    return struct.pack("!IB", length, MSG_CHANNEL_DATA) + payload


def pack_channel_cmd(msg_type: int, channel_id: int) -> bytes:
    payload = CHANNEL_STRUCT.pack(channel_id)
    return pack_frame(msg_type, payload)
