# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
import hashlib
import random
import pytest

from conftest import synthetic_sps
from soop_grid.media import adts_info, parse_adts, sps_info
from soop_grid.mpegts import PCR_INTERVAL_90K, PCR_MAX_RECOVERY_GAP_90K, TSMux, crc_mpeg, pts_bytes
from soop_grid.protocol import GridError


def _packetize_reference(mux, pid, data, start=True, pcr=None):
    """Pre-optimization packetizer retained as a byte-exact test oracle."""
    data = memoryview(data)
    packets = []
    while data:
        packet = bytearray(b"\xff" * 188)
        packet[:4] = bytes(
            (0x47, ((pid >> 8) & 31) | (0x40 if start else 0), pid & 255, 0x10 | mux.cc.get(pid, 0))
        )
        mux.cc[pid] = (mux.cc.get(pid, 0) + 1) & 15
        capacity = 176 if pcr is not None else 184
        n = min(len(data), capacity)
        adapt = 8 if pcr is not None else 0
        if n < capacity:
            adapt = 184 - n
        pos = 4
        if adapt:
            packet[3] |= 0x20
            packet[pos] = adapt - 1
            if adapt >= 2:
                packet[pos + 1] = 0
            if pcr is not None:
                value = pcr & ((1 << 33) - 1)
                packet[pos + 1 : pos + 8] = bytes(
                    (
                        0x10,
                        (value >> 25) & 255,
                        (value >> 17) & 255,
                        (value >> 9) & 255,
                        (value >> 1) & 255,
                        ((value << 7) & 255) | 0x7E,
                        0,
                    )
                )
            pos += adapt
        packet[pos : pos + n] = data[:n]
        packets.append(bytes(packet))
        data = data[n:]
        start = False
        pcr = None
    return b"".join(packets)


@pytest.mark.parametrize(
    "size", [0, 1, 2, 7, 8, 175, 176, 177, 183, 184, 185, 359, 360, 361, 367, 368, 369, 4097, 65536, 1048576]
)
@pytest.mark.parametrize("pcr", [None, 0, 123456789, (1 << 33) - 1])
@pytest.mark.parametrize("start", [False, True])
def test_preallocated_packetizer_matches_reference(size, pcr, start):
    data = bytes((i * 29 + 7) & 255 for i in range(size))
    expected_mux, actual_mux = TSMux(), TSMux()
    expected = _packetize_reference(expected_mux, 0x123, data, start=start, pcr=pcr)
    actual = actual_mux.packetize(0x123, data, start=start, pcr=pcr)
    assert actual == expected
    assert actual_mux.cc == expected_mux.cc


def test_preallocated_packetizer_matches_reference_for_deterministic_random_inputs():
    randomizer = random.Random(0x5017)
    for _ in range(250):
        size = randomizer.randrange(0, 24_000)
        data = randomizer.randbytes(size)
        pid = randomizer.randrange(0x2000)
        pcr = randomizer.choice((None, 0, randomizer.randrange(1 << 40)))
        start = bool(randomizer.getrandbits(1))
        expected_mux, actual_mux = TSMux(), TSMux()
        expected = _packetize_reference(expected_mux, pid, data, start=start, pcr=pcr)
        actual = actual_mux.packetize(pid, data, start=start, pcr=pcr)
        assert actual == expected
        assert actual_mux.cc == expected_mux.cc


def test_go_ts_golden_and_preroll(golden):
    g = golden["ts"]
    m = TSMux()
    assert m.add("P", 40_000_000, b"\0\0\1\x41") == b""
    assert m.add("A", 40_000_000, bytes.fromhex(g["audio"])) == b""
    ts = m.add("I", 50_000_000, bytes.fromhex(g["video"]))
    ts += m.add("A", 50_010_000, bytes.fromhex(g["audio"]))
    ts += m.add("P", 50_333_333, b"\0\0\1\x41\x88")
    assert ts.hex() == g["ts"] and m.preroll_video == 1


@pytest.mark.parametrize("n", [1, 175, 176, 177, 183, 184, 185, 1000])
@pytest.mark.parametrize("pcr", [None, 123456789])
def test_ts_boundaries_and_original_payload(n, pcr):
    data = bytes([37]) * n
    out = TSMux().packetize(256, data, pcr=pcr)
    restored = bytearray()
    for i in range(0, len(out), 188):
        packet = out[i : i + 188]
        assert len(packet) == 188 and packet[0] == 0x47 and packet[3] & 15 == i // 188 % 16
        pos = 4 + ((packet[4] + 1) if packet[3] & 32 else 0)
        restored.extend(packet[pos:])
    assert restored == data


def test_pat_pmt_crc_and_timestamp_bounds():
    out = TSMux().tables()
    for offset in (0, 188):
        packet = out[offset : offset + 188]
        pos = 4 + packet[4] + 1 + 1
        section = packet[pos:]
        assert crc_mpeg(section) == 0
    m = TSMux()
    m.add("I", 50_000_000, synthetic_sps())
    with pytest.raises(GridError):
        m.add("P", 1, b"\0\0\1\x41")


def test_pts_dts_timestamp_serialization_wraps_at_33_bits():
    wrap = 1 << 33
    assert pts_bytes(wrap + 12345) == pts_bytes(12345)


def test_pcr_encoding_wraps_33_bit_base_without_reversing_unwrapped_clock():
    wrap = 1 << 33
    mux = TSMux()
    mux.started = True
    first_dts = wrap - 4_500
    data = mux.add_video(first_dts, first_dts, b"first")
    data += mux.add_video(wrap + 4_500, wrap + 4_500, b"second")
    pcrs = []
    for offset in range(0, len(data), 188):
        packet = data[offset : offset + 188]
        control = (packet[3] >> 4) & 3
        if ((packet[1] & 31) << 8 | packet[2]) == 0x100 and control in (2, 3) and packet[5] & 0x10:
            base = (
                (packet[6] << 25)
                | (packet[7] << 17)
                | (packet[8] << 9)
                | (packet[9] << 1)
                | (packet[10] >> 7)
            )
            extension = ((packet[10] & 1) << 8) | packet[11]
            pcrs.append(base * 300 + extension)
    assert pcrs == [(wrap - 4_500) * 300, 4_500 * 300]


def test_video_pcr_interval_at_100ms_boundary_is_encoded_correctly():
    mux = TSMux()
    idr = b"\0\0\1\x67\x42\0\0\1\x68\xce\0\0\1\x65\x88"
    data = mux.add_video(0, 0, idr, idr=True)
    data += mux.add_video(9_000, 9_000, b"\0\0\1\x41\x88")
    packets = [data[i : i + 188] for i in range(0, len(data), 188)]
    pcrs = []
    for packet in packets:
        pid = ((packet[1] & 31) << 8) | packet[2]
        control = (packet[3] >> 4) & 3
        if pid != 0x100 or control not in (2, 3) or packet[4] < 7 or not packet[5] & 0x10:
            continue
        base = (packet[6] << 25) | (packet[7] << 17) | (packet[8] << 9) | (packet[9] << 1) | (packet[10] >> 7)
        extension = ((packet[10] & 1) << 8) | packet[11]
        pcrs.append(base * 300 + extension)
    assert len(pcrs) == 2
    assert pcrs[1] - pcrs[0] == 9_000 * 300


def _read_pcr_samples(data):
    samples = []
    for offset in range(0, len(data), 188):
        packet = data[offset : offset + 188]
        pid = ((packet[1] & 31) << 8) | packet[2]
        control = (packet[3] >> 4) & 3
        if pid != 0x100 or control not in (2, 3) or packet[4] < 7 or not packet[5] & 0x10:
            continue
        base = (packet[6] << 25) | (packet[7] << 17) | (packet[8] << 9) | (packet[9] << 1) | (packet[10] >> 7)
        extension = ((packet[10] & 1) << 8) | packet[11]
        samples.append((base * 300 + extension, packet))
    return samples


def _assert_transport_continuity(data):
    last_payload_cc = {}
    for offset in range(0, len(data), 188):
        packet = data[offset : offset + 188]
        assert len(packet) == 188 and packet[0] == 0x47
        pid = ((packet[1] & 31) << 8) | packet[2]
        control = (packet[3] >> 4) & 3
        assert control in (1, 2, 3)
        cc = packet[3] & 15
        if control == 2:
            if pid in last_payload_cc:
                assert cc == last_payload_cc[pid]
        elif pid in last_payload_cc:
            assert cc == (last_payload_cc[pid] + 1) & 15
        if control in (1, 3):
            last_payload_cc[pid] = cc


@pytest.mark.parametrize(
    ("delta", "expected_intermediate"),
    [(9_001, 1), (9_090, 1), (20_790, 2), (45_000, 4), (180_000, 19)],
)
def test_mux_inserts_bounded_pcr_only_samples_for_dts_gaps(delta, expected_intermediate):
    mux = TSMux()
    mux.started = True
    mux.add_video(0, 0, b"first")
    output = mux.add_video(delta, delta, b"second")
    samples = _read_pcr_samples(output)
    assert len(samples) == expected_intermediate + 1
    values = [sample[0] // 300 for sample in samples]
    assert values == [*range(PCR_INTERVAL_90K, delta, PCR_INTERVAL_90K), delta]
    assert all(0 < b - a <= PCR_INTERVAL_90K for a, b in zip(values, values[1:], strict=False))
    intermediate = [sample[1] for sample in samples[:-1]]
    assert all(((packet[3] >> 4) & 3) == 2 for packet in intermediate)
    assert all(packet[4] == 183 and packet[5] == 0x10 for packet in intermediate)
    # Adaptation-only packets keep the previous payload CC for this PID.
    assert all((packet[3] & 15) == 0 for packet in intermediate)
    assert mux.last_pcr_dts == delta


def test_mux_rejects_pcr_gap_over_recovery_bound_before_mutating_state():
    mux = TSMux()
    mux.started = True
    mux.add_video(0, 0, b"first")
    before = (mux.last_dts, mux.last_pcr_dts, mux.video_frames, dict(mux.cc))
    with pytest.raises(GridError, match="media_pcr_gap_limit"):
        mux.add_video(PCR_MAX_RECOVERY_GAP_90K + 1, PCR_MAX_RECOVERY_GAP_90K + 1, b"second")
    assert (mux.last_dts, mux.last_pcr_dts, mux.video_frames, dict(mux.cc)) == before


def test_pcr_only_samples_preserve_payload_cc_and_wrap_the_33_bit_clock():
    mux = TSMux()
    mux.started = True
    first_dts = (1 << 33) - 4_500
    mux.add_video(first_dts, first_dts, b"first")
    output = mux.add_video((1 << 33) + 13_500, (1 << 33) + 13_500, b"second")
    samples = _read_pcr_samples(output)
    bases = [sample[0] // 300 for sample in samples]
    assert bases == [4_500, 13_500]
    assert all((sample[1][3] & 15) == 0 for sample in samples[:-1])


def test_pcr_recovery_ts_with_real_encoded_access_units_decodes(encoded_bframes, tmp_path):
    import json
    import os
    import shutil
    import subprocess

    from soop_grid.h264clock import H264Clock

    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg/FFprobe required to independently validate recovered PCR output")

    from soop_grid.mpegts import nals

    idrs = [unit for unit, _kind in encoded_bframes if any(nal[0] & 31 == 5 for nal in nals(unit))]
    assert len(idrs) >= 2
    clock, mux = H264Clock(), TSMux()
    first = clock.inspect(idrs[0], 50_000_000, idrs[0].composition_offset_100ns)
    second = clock.inspect(idrs[1], 52_310_000, idrs[1].composition_offset_100ns)
    assert second["dts"] - first["dts"] == 20_790
    output = bytearray(mux.add_video(first["dts"], first["pts"], idrs[0], idr=True))
    audio_path = tmp_path / "test-audio.aac"
    encoded_audio = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-nostdin",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=880:sample_rate=44100",
            "-t",
            "0.25",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-f",
            "adts",
            str(audio_path),
        ],
        capture_output=True,
        timeout=30,
    )
    assert encoded_audio.returncode == 0, encoded_audio.stderr.decode("utf-8", "replace")
    output.extend(mux.add_audio(first["dts"] + 3_000, audio_path.read_bytes()))
    output.extend(mux.add_video(second["dts"], second["pts"], idrs[1], idr=True))
    pcr_values = [sample[0] // 300 for sample in _read_pcr_samples(output)]
    assert pcr_values == [
        first["dts"],
        first["dts"] + PCR_INTERVAL_90K,
        first["dts"] + 2 * PCR_INTERVAL_90K,
        second["dts"],
    ]
    assert all(0 < b - a <= PCR_INTERVAL_90K for a, b in zip(pcr_values, pcr_values[1:], strict=False))
    _assert_transport_continuity(output)
    ts_path = tmp_path / "pcr-recovered.ts"
    ts_path.write_bytes(output)
    from tools.verify_recording import verify

    facts = verify(ts_path, ffprobe, ffmpeg, timeout=30)
    assert facts["passed"], facts["failures"]
    assert facts["ts"]["max_pcr_value_delta_seconds"] <= 0.1
    assert facts["ts"]["pcr_pid_declarations"] == ["0x100"]
    assert facts["ts"]["continuity_errors"] == 0
    assert facts["ts"]["psi_crc_errors"] == 0
    video_pes = facts["ts"]["pes_payloads"]["0x100"]
    assert video_pes["bytes"] == sum(len(unit) for unit in idrs)
    assert video_pes["sha256"] == hashlib.sha256(b"".join(idrs)).hexdigest()
    audio_es = b"".join(frame.data for frame in parse_adts(audio_path.read_bytes()).frames)
    audio_pes = facts["ts"]["pes_payloads"]["0x101"]
    assert audio_pes["bytes"] == len(audio_es)
    assert audio_pes["sha256"] == hashlib.sha256(audio_es).hexdigest()
    decoded = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-xerror",
            "-nostdin",
            "-i",
            str(ts_path),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-f",
            "null",
            "-",
        ],
        capture_output=True,
        timeout=30,
    )
    assert decoded.returncode == 0, decoded.stderr.decode("utf-8", "replace")
    probe = subprocess.run(
        [ffprobe, "-v", "error", "-show_entries", "stream=codec_type,nb_frames", "-of", "json", str(ts_path)],
        capture_output=True,
        timeout=30,
    )
    assert probe.returncode == 0, probe.stderr.decode("utf-8", "replace")
    assert {stream["codec_type"] for stream in json.loads(probe.stdout)["streams"]} == {"video", "audio"}


def test_mux_tracks_presentation_extent_across_b_frame_reordering():
    mux = TSMux()
    mux.started = True
    mux.add_video(0, 300, b"first")
    mux.add_video(100, 400, b"second")
    mux.add_video(200, 250, b"third")
    assert mux.last_pts == 250
    assert mux.min_pts == 250
    assert mux.max_pts == 400


def test_sps_cropping_and_adts_metadata(golden):
    info = sps_info(synthetic_sps())
    assert (info["width"], info["height"]) == (1920, 1080)
    assert sps_info(b"\0\0\1\x41") is None
    with pytest.raises(GridError):
        sps_info(b"\0\0\1\x67\0")
    assert adts_info(bytes.fromhex(golden["ts"]["audio"])) == {
        "codec": "aac",
        "sample_rate": 44100,
        "channels": 2,
    }
