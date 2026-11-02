# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""Native Center authentication/JOIN/discovery, retaining server-issued credentials."""

import hmac
import json
import re
import struct
import time
from dataclasses import dataclass, field

from .crypto import AUTH_IV, AUTH_KEY, PREFIX, SALT, ctr, mixed_header, pad16, wire_hash
from .protocol import GridError, center_packet, read_frame

ADJUST = (1, 255, 253, 254, 1, 2)
JOINLOG = b"log\x11\x06&\x06os\x06=\x06Linux\x12"
GRID_QUALITY_CODES = frozenset((1, 2, 4, 8, 32))
JOIN_QUALITY_VALUES = frozenset(("high", "ori", "normal", "low", "high_4000", "high_8000"))


def valid_seed(seed):
    if not isinstance(seed, bytes) or len(seed) != 20:
        return False
    plain = bytes((b - ADJUST[i % 6]) & 255 for i, b in enumerate(seed))
    return hmac.compare_digest(wire_hash(plain[:4]), plain[4:])


@dataclass(repr=False)
class Credentials:
    ticket: bytes = field(repr=False)
    seed: bytes = field(repr=False)
    guid: str = field(repr=False)
    bno: int
    password: bytes = field(default=b"", repr=False)
    joinlog: bytes = field(default=JOINLOG, repr=False)

    @classmethod
    def parse(cls, body, guid, bno, password=b""):
        if (
            not isinstance(body, bytes)
            or not 44 <= len(body) <= 8192
            or struct.unpack_from("<I", body, 12)[0] != len(body) - 16
        ):
            raise GridError("certificate_length_invalid")
        text = body[16:-28]
        end = text.find(b"\0")
        seed = body[-28:-8]
        if (
            end < 1
            or end > 4096
            or any(b in text[:end] for b in (17, 18))
            or not valid_seed(seed)
            or not isinstance(guid, str)
            or not re.fullmatch(
                r"(?:[0-9A-Fa-f]{32}|[0-9A-Fa-f]{8}(?:-[0-9A-Fa-f]{4}){3}-[0-9A-Fa-f]{12})", guid
            )
            or type(bno) is not int
            or not 0 < bno <= 0xFFFFFFFF
        ):
            raise GridError("issued_certificate_invalid")
        if not isinstance(password, bytes) or len(password) > 12 or any(b < 32 or b > 126 for b in password):
            raise GridError("stream_password_encoding_invalid")
        return cls(text[:end], seed, guid, bno, password)

    def clear(self):
        self.ticket = self.seed = self.password = self.joinlog = b""
        self.guid = ""


def auth_body(c, counter=1):
    if not valid_seed(c.seed):
        raise GridError("issued_seed_required")
    data = struct.pack("<III", 2, 8, 0) + c.guid.replace("-", "").encode() + b"\0"
    ts = int.from_bytes(bytes((c.seed[i] - ADJUST[i % 6]) & 255 for i in range(4)), "little")
    mix = len(data) | 0x08000000
    for i, b in enumerate(data):
        v = b << ((i % 5 & 1) * 16)
        mix = mix | v if i % 2 == 0 else mix ^ v
    first = ctr(AUTH_KEY, AUTH_IV, mixed_header(ts, mix, counter, len(data)) + PREFIX + data)
    second = SALT + first
    digest = wire_hash(pad16(second))
    encrypted = ctr(digest, AUTH_IV, second)
    return struct.pack("<II", 8, 16 + len(encrypted)) + digest + encrypted


def join_body(c, quality="ori", is_auto=False):
    if (
        not isinstance(c.ticket, bytes)
        or not 0 < len(c.ticket) <= 4096
        or any(b in c.ticket for b in (0, 17, 18))
        or type(c.bno) is not int
        or not 0 < c.bno <= 0xFFFFFFFF
    ):
        raise GridError("issued_ticket_required")
    if (
        not isinstance(c.password, bytes)
        or len(c.password) > 12
        or any(b < 32 or b > 126 for b in c.password)
        or not isinstance(c.joinlog, bytes)
        or len(c.joinlog) > 8192
    ):
        raise GridError("join_field_bounds")
    if not isinstance(quality, str) or quality not in JOIN_QUALITY_VALUES or type(is_auto) is not bool:
        raise GridError("join_quality_invalid")
    log = re.sub(b"liveualog\x11[^\x12]*\x12", b"", c.joinlog, count=1)
    text = (
        log
        + b"ticket\x11"
        + c.ticket
        + b"\x12quality\x11"
        + quality.encode("ascii")
        + b"\x12is_auto\x11"
        + (b"true" if is_auto else b"false")
        + b"\x12passwd\x11"
        + c.password
        + b"\x12"
    )
    if len(text) > 8192 or b"\0" in text:
        raise GridError("join_field_bounds")
    return struct.pack("<5I", 0, 0, c.bno, 20, len(text)) + text + b"\0"


def json_body(data):
    text = json.dumps(data, separators=(",", ":")).encode()
    return struct.pack("<I", len(text)) + text


def discover_parent(network, address, credentials, report, quality=1, join_quality="ori", is_auto=False):
    if type(quality) is not int or quality not in GRID_QUALITY_CODES:
        raise GridError("grid_quality_unsupported")
    authentication = auth_body(credentials)
    join = join_body(credentials, join_quality, is_auto)
    sock = network.connect(address)

    def send(cmd, body=b""):
        network.send(sock, center_packet(cmd, body))

    def receive():
        f = read_frame(sock, "center", network.remaining(3) if hasattr(network, "remaining") else 3)
        if f.result < 0:
            raise GridError("center_access_denied")
        return f

    try:
        send(2, b"\0")
        frame = receive()
        if frame.command != 2 or len(frame.body) < 8:
            raise GridError("center_init_unexpected")
        started = time.monotonic()
        send(3)
        for _ in range(4):
            frame = receive()
            if frame.command == 3:
                break
        if frame.command != 3 or len(frame.body) < 8:
            raise GridError("center_session_missing")
        node_key = struct.unpack_from("<I", frame.body, 4)[0]
        send(0x3E, struct.pack("<HHI", 4, int((time.monotonic() - started) * 500) & 65535, 0))
        send(0x14, bytes(12))
        send(0x2A, authentication)
        send(0x46, join)
        handle = None
        joined = False
        requested = False
        parent_requested = False
        for _ in range(24):
            frame = receive()
            if frame.command == 0x4A and len(frame.body) >= 52:
                handle = frame.body[:4]
            if frame.command == 0x46:
                joined = True
            if joined and handle is not None and not requested:
                requested = True
                report("center_join_accepted")
                send(0x71, json_body({"broad_no": 0, "relay_port": 0, "reverse_port": 0}))
                send(0x50, handle)
            if frame.command == 0x50:
                if not requested or parent_requested:
                    raise GridError("center_discovery_sequence_invalid")
                parent_requested = True
                send(
                    0x69,
                    json_body(
                        {"list": [{"alloc_type": 1, "parent_ip": 0, "parent_port": 0, "quality": quality}]}
                    ),
                )
            if frame.command == 0x69:
                if not parent_requested:
                    raise GridError("center_discovery_sequence_invalid")
                from .parent import parse_parents

                parents = parse_parents(frame.body)
                matching = [parent for parent in parents if parent.quality == quality]
                if not matching:
                    raise GridError(
                        "center_quality_not_honored",
                        safe_facts={
                            "requested_grid_quality_code": quality,
                            "returned_grid_quality_count": len(parents),
                            "returned_grid_quality_codes": sorted({parent.quality for parent in parents})[:8],
                        },
                    )
                report("parent_discovery_received")
                return matching, node_key
        raise GridError("parent_discovery_missing")
    finally:
        network.release(sock)
