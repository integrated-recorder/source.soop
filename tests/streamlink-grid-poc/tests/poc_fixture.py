# SPDX-License-Identifier: AGPL-3.0-only
"""Small, deterministic header transformer for independently decoded POC probes.

It starts from a real progressive, no-B-frame x264 stream and rewrites only
SPS/slice-header POC syntax. Macroblock data and all other slice syntax bits
are copied verbatim. Fixtures are test-only and are independently decoded by
FFmpeg before they are used by receiver tests.
"""

from __future__ import annotations

from soop_grid.h264clock import parse_pps, parse_sps
from soop_grid.mpegts import nals


class _Bits:
    def __init__(self, data: bytes):
        self.values = [((byte >> bit) & 1) for byte in data for bit in range(7, -1, -1)]
        self.pos = 0

    def get(self, width: int) -> int:
        if width < 0 or self.pos + width > len(self.values):
            raise ValueError("truncated fixture syntax")
        value = 0
        for bit in self.values[self.pos : self.pos + width]:
            value = (value << 1) | bit
        self.pos += width
        return value

    def ue(self) -> int:
        zeros = 0
        while self.get(1) == 0:
            zeros += 1
            if zeros > 31:
                raise ValueError("fixture Exp-Golomb overflow")
        return (1 << zeros) - 1 + self.get(zeros)

    def se(self) -> int:
        code = self.ue()
        return (code + 1) // 2 if code & 1 else -(code // 2)


def _ue(value: int) -> list[int]:
    code = value + 1
    width = code.bit_length()
    return [0] * (width - 1) + [((code >> shift) & 1) for shift in range(width - 1, -1, -1)]


def _se(value: int) -> list[int]:
    return _ue(2 * value - 1 if value > 0 else -2 * value)


def _syntax_bits(data: bytes) -> list[int]:
    """Return RBSP syntax bits without the rbsp_trailing_bits suffix."""
    reader = _Bits(data)
    last_one = max((index for index, bit in enumerate(reader.values) if bit), default=-1)
    if last_one < 0:
        raise ValueError("RBSP lacks stop bit")
    if any(reader.values[last_one + 1 :]):
        raise ValueError("invalid RBSP padding")
    return reader.values[:last_one]


def _pack_rbsp(bits: list[int]) -> bytes:
    bits = [*bits, 1]
    bits.extend([0] * (-len(bits) % 8))
    output = bytearray()
    for start in range(0, len(bits), 8):
        value = 0
        for bit in bits[start : start + 8]:
            value = (value << 1) | bit
        output.append(value)
    return bytes(output)


def _unescape(ebsp: bytes) -> bytes:
    output = bytearray()
    zeros = 0
    for byte in ebsp:
        if zeros >= 2 and byte == 3:
            zeros = 0
            continue
        output.append(byte)
        zeros = zeros + 1 if byte == 0 else 0
    return bytes(output)


def _escape(rbsp: bytes) -> bytes:
    output = bytearray()
    zeros = 0
    for byte in rbsp:
        if zeros >= 2 and byte <= 3:
            output.append(3)
            zeros = 0
        output.append(byte)
        zeros = zeros + 1 if byte == 0 else 0
    return bytes(output)


def _rewrite_sps(nal: bytes, target_type: int, *, delta_always_zero: bool = True) -> bytes:
    if target_type not in (1, 2):
        raise ValueError("target POC type must be 1 or 2")
    rbsp = _unescape(nal[1:])
    syntax = _syntax_bits(rbsp)
    reader = _Bits(rbsp)
    reader.get(24)  # profile_idc, constraint flags, level_idc
    reader.ue()  # seq_parameter_set_id
    reader.ue()  # log2_max_frame_num_minus4
    poc_type_start = reader.pos
    old_type = reader.ue()
    if old_type != 0:
        raise ValueError("fixture source must use POC type 0")
    reader.ue()  # log2_max_pic_order_cnt_lsb_minus4
    if reader.pos > len(syntax):
        raise ValueError("SPS POC syntax exceeds RBSP")
    replacement = _ue(target_type)
    if target_type == 1:
        # Use a one-entry reference cycle: each reference frame advances POC
        # by two. Type-1 fixtures with B pictures carry a per-slice delta.
        replacement.append(int(delta_always_zero))
        replacement.extend(_se(0))  # offset_for_non_ref_pic
        replacement.extend(_se(0))  # offset_for_top_to_bottom_field
        replacement.extend(_ue(1))  # num_ref_frames_in_pic_order_cnt_cycle
        replacement.extend(_se(2))  # offset_for_ref_frame[0]
    rewritten = [*syntax[:poc_type_start], *replacement, *syntax[reader.pos :]]
    return bytes([nal[0], *_escape(_pack_rbsp(rewritten))])


def _rewrite_slice(
    nal: bytes,
    sps: dict,
    pps: dict,
    target_type: int,
    *,
    target_delta: int = 0,
) -> bytes:
    nal_type = nal[0] & 31
    if nal_type not in (1, 5):
        return nal
    rbsp = _unescape(nal[1:])
    syntax = _syntax_bits(rbsp)
    reader = _Bits(rbsp)
    reader.ue()  # first_mb_in_slice
    reader.ue()  # slice_type
    reader.ue()  # pic_parameter_set_id
    reader.get(sps["log2_frame_num"])
    if nal_type == 5:
        reader.ue()  # idr_pic_id
    poc_syntax_start = reader.pos
    reader.get(sps["log2_poc_lsb"])
    if pps["bottom_poc"]:
        reader.se()
    poc_bits = _se(target_delta) if target_type == 1 else []
    rewritten = [*syntax[:poc_syntax_start], *poc_bits, *syntax[reader.pos :]]
    return bytes([nal[0], *_escape(_pack_rbsp(rewritten))])


def rewrite_type0_stream(data: bytes, target_type: int) -> bytes:
    """Rewrite a progressive POC-0 no-B stream to a valid POC-1 or POC-2 form."""
    if target_type not in (1, 2):
        raise ValueError("target POC type must be 1 or 2")
    seq = next((unit for unit in nals(data) if unit[0] & 31 == 7), None)
    pic = next((unit for unit in nals(data) if unit[0] & 31 == 8), None)
    if seq is None or pic is None:
        raise ValueError("fixture source needs SPS and PPS")
    source_sps = parse_sps(seq)
    source_pps = parse_pps(pic, {source_sps["id"]: source_sps})
    if source_sps["poc_type"] != 0:
        raise ValueError("fixture source must use POC type 0")
    # parse_sps rejects interlaced SPS, so accepted input is frame-coded.
    if source_pps["bottom_poc"]:
        raise ValueError("fixture source must omit delta_pic_order_cnt_bottom")

    from soop_grid.h264clock import H264Clock, parse_slice

    converted = []
    clock = H264Clock()
    previous_frame_num = 0
    previous_frame_num_offset = 0
    previous_nonreference = False
    for unit in nals(data):
        kind = unit[0] & 31
        if kind == 7:
            converted.append(_rewrite_sps(unit, target_type, delta_always_zero=target_type != 1))
        elif kind in (1, 5):
            header = parse_slice(unit, source_sps, source_pps)
            if header.mmco5:
                raise ValueError("fixture source with MMCO5 is outside the generated subset")
            source_poc = clock._picture_order(header, source_sps)
            delta = 0
            if target_type == 1:
                if header.idr:
                    frame_num_offset = 0
                else:
                    frame_num_offset = previous_frame_num_offset
                    if previous_frame_num > header.frame_num:
                        frame_num_offset += source_sps["max_frame_num"]
                abs_frame_num = frame_num_offset + header.frame_num
                if not header.nal_ref_idc and abs_frame_num > 0:
                    abs_frame_num -= 1
                expected = 2 * abs_frame_num
                delta = source_poc - expected
                previous_frame_num = header.frame_num
                previous_frame_num_offset = frame_num_offset
            elif target_type == 2:
                if previous_nonreference and not header.nal_ref_idc:
                    raise ValueError("POC type 2 cannot encode consecutive non-reference pictures")
            previous_nonreference = not bool(header.nal_ref_idc)
            converted.append(_rewrite_slice(unit, source_sps, source_pps, target_type, target_delta=delta))
        else:
            converted.append(unit)
    return b"".join(b"\x00\x00\x00\x01" + unit for unit in converted)
