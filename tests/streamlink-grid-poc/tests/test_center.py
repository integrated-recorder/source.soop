# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
import struct

import pytest

from soop_grid.center import Credentials, auth_body, discover_parent, join_body, json_body
from soop_grid.protocol import Frame, GridError


def credentials(golden):
    c = Credentials.parse(
        bytes.fromhex(golden["center"]["certificate"]), "0123456789ABCDEF0123456789ABCDEF", 12345
    )
    c.joinlog = b"log\x11offline\x12"
    return c


def test_go_center_auth_and_password_golden(golden):
    c = credentials(golden)
    assert auth_body(c).hex() == golden["center"]["center_auth"]
    assert join_body(c).hex() == golden["center"]["center_join"]
    c.password = b"fixture-only"
    assert join_body(c).hex() == golden["center"]["center_join_password"]
    assert "fixture" not in repr(c)
    c.clear()
    with pytest.raises(GridError):
        auth_body(c)


def test_join_supports_measured_low_auto_profile(golden):
    body = join_body(credentials(golden), quality="low", is_auto=True)
    assert b"\x12quality\x11low\x12is_auto\x11true\x12passwd\x11" in body
    with pytest.raises(GridError, match="join_quality_invalid"):
        join_body(credentials(golden), quality="unmeasured", is_auto=True)
    with pytest.raises(GridError, match="join_quality_invalid"):
        join_body(credentials(golden), quality="low", is_auto=1)


@pytest.mark.parametrize("kind", ["short", "length", "seed", "unterminated", "password"])
def test_issued_certificate_rejects_corruption(golden, kind):
    b = bytearray.fromhex(golden["center"]["certificate"])
    password = b""
    if kind == "short":
        b = b[:20]
    if kind == "length":
        b[12] ^= 1
    if kind == "seed":
        b[-20] ^= 1
    if kind == "unterminated":
        b[16:24] = b"x" * 8
    if kind == "password":
        password = b"bad\x11field"
    with pytest.raises(GridError):
        Credentials.parse(bytes(b), "0" * 32, 12345, password)


@pytest.mark.parametrize("join_first", [False, True])
def test_center_normal_sequence_and_server_denial(golden, monkeypatch, join_first):
    import soop_grid.center as center

    class Net:
        def __init__(self):
            self.wires = []
            self.released = False

        def connect(self, address):
            return object()

        def send(self, sock, wire):
            self.wires.append(wire)

        def release(self, sock):
            self.released = True

    join_replies = [Frame(0x4A, bytes(52)), Frame(0x46, b"")]
    if join_first:
        join_replies.reverse()
    replies = iter(
        [
            Frame(2, bytes(8)),
            Frame(3, struct.pack("<II", 0, 42)),
            *join_replies,
            Frame(0x50, b""),
            Frame(
                0x69,
                json_body(
                    {
                        "list": [
                            {"parent_ip": 0x08080808, "parent_port": 0x1027, "quality": 1, "cur_frame_no": 99}
                        ]
                    }
                ),
            ),
        ]
    )
    monkeypatch.setattr(center, "read_frame", lambda *a: next(replies))
    n = Net()
    events = []
    parents, key = discover_parent(n, ("8.8.8.8", 1), credentials(golden), events.append)
    assert key == 42 and parents[0].address == ("8.8.8.8", 10000)
    assert [struct.unpack_from("<I", x)[0] for x in n.wires] == [
        2,
        3,
        0x3E,
        0x14,
        0x2A,
        0x46,
        0x71,
        0x50,
        0x69,
    ]
    assert n.released
    monkeypatch.setattr(center, "read_frame", lambda *a: Frame(2, b"", -1))
    with pytest.raises(GridError, match="access_denied"):
        discover_parent(Net(), ("8.8.8.8", 1), credentials(golden), events.append)


@pytest.mark.parametrize("ticket", [b"x\x12passwd\x11injected", b"x\x11injected"])
def test_issued_ticket_cannot_inject_join_fields(golden, ticket):
    body = bytearray.fromhex(golden["center"]["certificate"])
    body[16:-28] = ticket + b"\0"
    struct.pack_into("<I", body, 12, len(body) - 16)
    with pytest.raises(GridError, match="issued_certificate_invalid"):
        Credentials.parse(bytes(body), "0" * 32, 12345)


def test_join_revalidates_mutable_credentials(golden):
    c = credentials(golden)
    c.ticket = b"ticket\x12passwd\x11injected"
    with pytest.raises(GridError):
        join_body(c)


@pytest.mark.parametrize("command", [0x50, 0x69])
def test_center_rejects_discovery_before_join(golden, monkeypatch, command):
    import soop_grid.center as center

    class Net:
        released = False

        def connect(self, address):
            return object()

        def send(self, *args):
            pass

        def release(self, sock):
            self.released = True

    parent_list = json_body(
        {"list": [{"parent_ip": 0x08080808, "parent_port": 0x1027, "quality": 1, "cur_frame_no": 99}]}
    )
    replies = iter([Frame(2, bytes(8)), Frame(3, bytes(8)), Frame(command, parent_list)])
    monkeypatch.setattr(center, "read_frame", lambda *a: next(replies))
    net = Net()
    with pytest.raises(GridError, match="sequence"):
        discover_parent(net, ("8.8.8.8", 1), credentials(golden), lambda _: None)
    assert net.released


@pytest.mark.parametrize("quality", [1, 2, 4, 8])
def test_center_requests_only_measured_grid_quality_and_checks_assignment(golden, monkeypatch, quality):
    import json
    import soop_grid.center as center

    class Net:
        def __init__(self):
            self.wires = []

        def connect(self, _address):
            return object()

        def send(self, _sock, wire):
            self.wires.append(wire)

        def release(self, _sock):
            pass

    parent_list = json_body(
        {"list": [{"parent_ip": 0x08080808, "parent_port": 0x1027, "quality": quality, "cur_frame_no": 99}]}
    )
    replies = iter(
        [
            Frame(2, bytes(8)),
            Frame(3, struct.pack("<II", 0, 42)),
            Frame(0x4A, bytes(52)),
            Frame(0x46, b""),
            Frame(0x50, b""),
            Frame(0x69, parent_list),
        ]
    )
    monkeypatch.setattr(center, "read_frame", lambda *_args: next(replies))
    net = Net()
    parents, _key = discover_parent(net, ("8.8.8.8", 1), credentials(golden), lambda _: None, quality=quality)
    request = json.loads(net.wires[-1][24:])
    assert request["list"][0]["quality"] == quality
    assert parents[0].quality == quality


def test_center_sends_measured_q8_low_auto_join(golden, monkeypatch):
    import soop_grid.center as center

    class Net:
        def __init__(self):
            self.wires = []

        def connect(self, _address):
            return object()

        def send(self, _sock, wire):
            self.wires.append(wire)

        def release(self, _sock):
            pass

    replies = iter(
        [
            Frame(2, bytes(8)),
            Frame(3, struct.pack("<II", 0, 42)),
            Frame(0x4A, bytes(52)),
            Frame(0x46, b""),
            Frame(0x50, b""),
            Frame(
                0x69,
                json_body(
                    {
                        "list": [
                            {"parent_ip": 0x08080808, "parent_port": 0x1027, "quality": 8, "cur_frame_no": 99}
                        ]
                    }
                ),
            ),
        ]
    )
    monkeypatch.setattr(center, "read_frame", lambda *_args: next(replies))
    net = Net()
    parents, _ = discover_parent(
        net,
        ("8.8.8.8", 1),
        credentials(golden),
        lambda _: None,
        quality=8,
        join_quality="low",
        is_auto=True,
    )
    join_wire = next(wire for wire in net.wires if struct.unpack_from("<I", wire)[0] == 0x46)
    assert b"\x12quality\x11low\x12is_auto\x11true\x12passwd\x11" in join_wire
    assert parents[0].quality == 8


def test_center_rejects_quality_assignment_mismatch(golden, monkeypatch):
    import soop_grid.center as center

    class Net:
        def connect(self, _address):
            return object()

        def send(self, *_args):
            pass

        def release(self, _sock):
            pass

    parent_list = json_body(
        {"list": [{"parent_ip": 0x08080808, "parent_port": 0x1027, "quality": 1, "cur_frame_no": 99}]}
    )
    replies = iter(
        [
            Frame(2, bytes(8)),
            Frame(3, struct.pack("<II", 0, 42)),
            Frame(0x4A, bytes(52)),
            Frame(0x46, b""),
            Frame(0x50, b""),
            Frame(0x69, parent_list),
        ]
    )
    monkeypatch.setattr(center, "read_frame", lambda *_args: next(replies))
    with pytest.raises(GridError, match="center_quality_not_honored") as caught:
        discover_parent(Net(), ("8.8.8.8", 1), credentials(golden), lambda _: None, quality=2)
    assert caught.value.safe_facts == {
        "requested_grid_quality_code": 2,
        "returned_grid_quality_count": 1,
        "returned_grid_quality_codes": [1],
    }


def test_center_rejects_unmeasured_quality_before_network(golden):
    class Net:
        def connect(self, _address):
            raise AssertionError("unsupported quality must be rejected before connecting")

    with pytest.raises(GridError, match="grid_quality_unsupported"):
        discover_parent(Net(), ("8.8.8.8", 1), credentials(golden), lambda _: None, quality=3)
