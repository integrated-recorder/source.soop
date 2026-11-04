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
                if header.mmco5:
                    # The MMCO-5 picture is frame_num 0 for the next picture.
                    previous_frame_num = previous_frame_num_offset = 0
                else:
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


def rewrite_type2_stream_to_type1_delta_zero(data: bytes) -> bytes:
    """Convert a no-B POC-2 stream to an equivalent Type-1 zero-delta stream.

    The source must use reference pictures only and advance its POC by two per
    frame. The SPS cycle is set to the corresponding +2 reference offset and
    ``delta_pic_order_always_zero_flag`` is set, so slice syntax is unchanged.
    Callers independently decode the result before treating it as a fixture.
    """
    from soop_grid.h264clock import parse_sps

    units = nals(data)
    sps_nal = next((unit for unit in units if unit[0] & 31 == 7), None)
    if sps_nal is None:
        raise ValueError("Type-1 zero-delta fixture requires an SPS")
    source_sps = parse_sps(sps_nal)
    if source_sps["poc_type"] != 2:
        raise ValueError("Type-1 zero-delta source must use POC type 2")
    if source_sps["max_reorder"] != 0:
        raise ValueError("Type-1 zero-delta source must have no reordering")

    rbsp = _unescape(sps_nal[1:])
    syntax = _syntax_bits(rbsp)
    reader = _Bits(rbsp)
    reader.get(24)  # profile_idc, constraint flags, level_idc
    reader.ue()  # seq_parameter_set_id
    reader.ue()  # log2_max_frame_num_minus4
    poc_type_start = reader.pos
    if reader.ue() != 2:
        raise ValueError("Type-1 zero-delta source must use POC type 2")
    replacement = [*_ue(1), 1, *_se(0), *_se(0), *_ue(1), *_se(2)]
    rewritten = [*syntax[:poc_type_start], *replacement, *syntax[reader.pos :]]
    new_sps = bytes([sps_nal[0], *_escape(_pack_rbsp(rewritten))])
    parse_sps(new_sps)
    return b"".join(b"\x00\x00\x00\x01" + (new_sps if unit is sps_nal else unit) for unit in units)


def rewrite_type1_stream_with_bottom_delta_zero(data: bytes) -> bytes:
    """Enable PPS bottom-field POC syntax and insert delta_pic_order_cnt[1]=0.

    This preserves each frame's POC for progressive Type-1 streams whose
    ``offset_for_top_to_bottom_field`` is zero. Input must currently omit the
    PPS flag and use explicit Type-1 delta syntax.
    """
    from soop_grid.h264clock import parse_pps, parse_sps

    units = nals(data)
    sps_nal = next((unit for unit in units if unit[0] & 31 == 7), None)
    pps_nal = next((unit for unit in units if unit[0] & 31 == 8), None)
    if sps_nal is None or pps_nal is None:
        raise ValueError("Type-1 bottom-delta fixture requires SPS and PPS")
    sps = parse_sps(sps_nal)
    pps = parse_pps(pps_nal, {sps["id"]: sps})
    if sps["poc_type"] != 1 or sps["delta_pic_order_always_zero"] or pps["bottom_poc"]:
        raise ValueError("Type-1 bottom-delta source is outside the supported transform subset")
    if sps["offset_for_top_to_bottom_field"] != 0:
        raise ValueError("Type-1 bottom-delta transform requires zero top-to-bottom offset")

    pps_rbsp = _unescape(pps_nal[1:])
    pps_bits = _syntax_bits(pps_rbsp)
    pps_reader = _Bits(pps_rbsp)
    pps_reader.ue()  # pic_parameter_set_id
    pps_reader.ue()  # seq_parameter_set_id
    pps_reader.get(1)  # entropy_coding_mode_flag
    bottom_flag_pos = pps_reader.pos
    if pps_reader.get(1) != 0:
        raise ValueError("Type-1 bottom-delta source already signals bottom POC syntax")
    pps_bits[bottom_flag_pos] = 1
    new_pps = bytes([pps_nal[0], *_escape(_pack_rbsp(pps_bits))])
    parse_pps(new_pps, {sps["id"]: sps})

    converted = []
    for unit in units:
        if unit is pps_nal:
            converted.append(new_pps)
            continue
        if unit[0] & 31 not in (1, 5):
            converted.append(unit)
            continue
        slice_rbsp = _unescape(unit[1:])
        slice_bits = _syntax_bits(slice_rbsp)
        reader = _Bits(slice_rbsp)
        reader.ue()  # first_mb_in_slice
        reader.ue()  # slice_type
        reader.ue()  # pic_parameter_set_id
        reader.get(sps["log2_frame_num"])
        if unit[0] & 31 == 5:
            reader.ue()  # idr_pic_id
        reader.se()  # delta_pic_order_cnt[0]
        insertion = reader.pos
        converted.append(
            bytes([unit[0], *_escape(_pack_rbsp(slice_bits[:insertion] + _se(0) + slice_bits[insertion:]))])
        )
    return b"".join(
        b"\x00\x00\x00\x01" + (new_pps if unit is pps_nal else converted[index])
        for index, unit in enumerate(units)
    )


def add_mmco5_type0(data: bytes, target_frame: int = 10) -> bytes:
    """Create one independently decodable POC-0/MMCO-5 no-B fixture.

    The accepted source subset is a single-SPS/PPS, progressive, CAVLC,
    no-B-frame libx264 Baseline stream with one reference frame. The transform
    inserts the POC-0 fields, performs MMCO 5 on one reference P picture, and
    renumbers later frame_num values from the MMCO reset. Callers must decode
    and compare the result independently before using it as a conformance case.
    """
    from soop_grid.h264clock import _slice_pps_id, parse_slice

    units = nals(data)
    sps_by_id, pps_by_id = {}, {}
    for unit in units:
        kind = unit[0] & 31
        if kind == 7:
            info = parse_sps(unit)
            sps_by_id[info["id"]] = info
        elif kind == 8:
            info = parse_pps(unit, sps_by_id)
            pps_by_id[info["id"]] = info
    if len(sps_by_id) != 1 or len(pps_by_id) != 1:
        raise ValueError("MMCO-5 fixture requires one SPS and one PPS")
    sps, pps = next(iter(sps_by_id.values())), next(iter(pps_by_id.values()))
    if (
        sps["poc_type"] != 2
        or sps["max_num_ref_frames"] != 1
        or pps["entropy_coding"]
        or pps["weighted_pred"]
        or pps["weighted_bipred"]
        or pps["bottom_poc"]
        or pps["redundant"]
    ):
        raise ValueError("MMCO-5 fixture source is outside the supported transform subset")

    def rewrite_sps(unit):
        raw = _unescape(unit[1:])
        syntax = _syntax_bits(raw)
        reader = _Bits(raw)
        reader.get(24)  # profile_idc, constraint flags, level_idc
        reader.ue()  # seq_parameter_set_id
        reader.ue()  # log2_max_frame_num_minus4
        poc_type_start = reader.pos
        if reader.ue() != 2:
            raise ValueError("MMCO-5 fixture source must signal POC type 2")
        replacement = _ue(0) + _ue(4)  # type 0, 8-bit pic_order_cnt_lsb
        return bytes(
            [unit[0], *_escape(_pack_rbsp(syntax[:poc_type_start] + replacement + syntax[reader.pos :]))]
        )

    def marking_span(unit, type0_sps):
        reader = _Bits(_unescape(unit[1:]))
        reader.ue()  # first_mb_in_slice
        slice_kind = reader.ue() % 5
        reader.ue()  # pic_parameter_set_id
        reader.get(sps["log2_frame_num"])
        if unit[0] & 31 == 5:
            reader.ue()  # idr_pic_id
        reader.get(type0_sps["log2_poc_lsb"])
        if pps["redundant"]:
            reader.ue()
        if slice_kind != 0:  # P slices only in this fixture
            raise ValueError("MMCO-5 fixture target must be a P slice")
        if reader.get(1):
            raise ValueError("MMCO-5 fixture does not support reference-count overrides")
        if reader.get(1):  # ref_pic_list_modification_flag_l0
            for _ in range(64):
                operation = reader.ue()
                if operation == 3:
                    break
                if operation in (0, 1, 2):
                    reader.ue()
                else:
                    raise ValueError("unsupported reference-list modification")
            else:
                raise ValueError("reference-list modification limit exceeded")
        start = reader.pos
        if not ((unit[0] >> 5) & 3):
            raise ValueError("MMCO-5 target must be a reference picture")
        if reader.get(1):
            raise ValueError("fixture source already uses adaptive reference marking")
        return start, reader.pos

    frame_index = -1
    target_source_frame_num = None
    output = []
    for unit in units:
        kind = unit[0] & 31
        if kind == 9:
            frame_index += 1
        if kind == 7:
            unit = rewrite_sps(unit)
        elif kind in (1, 5):
            if frame_index < 0:
                raise ValueError("fixture VCL precedes its access-unit delimiter")
            pps_id = _slice_pps_id(unit)
            active_sps = sps_by_id[pps["sps_id"]]
            if pps_id != pps["id"]:
                raise ValueError("MMCO-5 fixture uses an unexpected PPS")
            header = parse_slice(unit, active_sps, pps)
            if header.idr:
                if frame_index != 0 or frame_index >= target_frame:
                    raise ValueError("MMCO-5 fixture expects one initial IDR before the target")
            if frame_index == target_frame:
                if header.slice_kind != "P" or not header.nal_ref_idc:
                    raise ValueError("MMCO-5 target must be a reference P picture")
                target_source_frame_num = header.frame_num

            raw = _unescape(unit[1:])
            syntax = _syntax_bits(raw)
            reader = _Bits(raw)
            reader.ue()
            reader.ue()
            reader.ue()
            frame_num_pos = reader.pos
            original_frame_num = reader.get(sps["log2_frame_num"])
            idr_bits = []
            if header.idr:
                idr_start = reader.pos
                reader.ue()
                idr_bits = syntax[idr_start : reader.pos]
            if frame_index > target_frame and not header.idr:
                new_frame_num = (original_frame_num - target_source_frame_num) % sps["max_frame_num"]
            else:
                new_frame_num = original_frame_num
            rewritten = (
                syntax[:frame_num_pos]
                + [(new_frame_num >> shift) & 1 for shift in range(sps["log2_frame_num"] - 1, -1, -1)]
                + idr_bits
                + [(frame_index * 2 >> shift) & 1 for shift in range(7, -1, -1)]
                + syntax[reader.pos :]
            )
            unit = bytes([unit[0], *_escape(_pack_rbsp(rewritten))])
            if frame_index == target_frame:
                type0_sps = {**sps, "poc_type": 0, "log2_poc_lsb": 8}
                start, end = marking_span(unit, type0_sps)
                marked = _syntax_bits(_unescape(unit[1:]))
                command = [1] + _ue(5) + _ue(0)  # adaptive marking, MMCO 5, terminator
                unit = bytes([unit[0], *_escape(_pack_rbsp(marked[:start] + command + marked[end:]))])
        output.append(unit)

    if frame_index < target_frame + 1 or target_source_frame_num is None:
        raise ValueError("MMCO-5 target access unit is absent")
    transformed = b"".join(b"\x00\x00\x00\x01" + unit for unit in output)
    parsed_sps = next(parse_sps(unit) for unit in nals(transformed) if unit[0] & 31 == 7)
    if parsed_sps["poc_type"] != 0 or parsed_sps["log2_poc_lsb"] != 8:
        raise ValueError("MMCO-5 fixture SPS transform did not validate")
    found_mmco5 = []
    for unit in nals(transformed):
        if unit[0] & 31 in (1, 5):
            header = parse_slice(unit, parsed_sps, pps)
            if header.mmco5:
                found_mmco5.append(header.frame_num)
    if found_mmco5 != [target_source_frame_num]:
        raise ValueError("MMCO-5 fixture marking did not round-trip")
    return transformed
