# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""Offline H.264 POC type -> MediaSink -> StreamIO -> TS integration checks."""

import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import threading
from types import SimpleNamespace

import pytest

from conftest import media_body
from poc_fixture import rewrite_type0_stream
from soop_grid.h264clock import parse_pps, parse_slice, parse_sps
from soop_grid.media import MediaSink, parse_adts
from soop_grid.mpegts import nals
from soop_grid.parent import Parent, receive_media
from soop_grid.protocol import Frame, parent_packet
from soop_grid.stream import SoopGridReader, validate_media_output


BASE = 50_000_000
FRAME_STEP = 333_333


def _run(binary, *args):
    result = subprocess.run([str(binary), *map(str, args)], capture_output=True, timeout=30)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return result.stdout


def _aus(data):
    groups = []
    current = []
    for unit in nals(data, max_units=512):
        if unit[0] & 31 == 9 and current:
            groups.append(current)
            current = []
        current.append(unit)
    if current:
        groups.append(current)
    return groups


def _annexb(group):
    return b"".join(b"\x00\x00\x00\x01" + unit for unit in group)


def _video_decode_hashes(ffmpeg, path):
    output = _run(ffmpeg, "-v", "error", "-xerror", "-i", path, "-map", "0:v:0", "-f", "framemd5", "-")
    return [
        line.rsplit(b",", 1)[-1].strip() for line in output.splitlines() if line and not line.startswith(b"#")
    ]


@pytest.fixture(scope="module")
def generated_poc_streams(tmp_path_factory):
    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg and FFprobe are required to create and independently verify POC bitstreams")
    ffmpeg, ffprobe = Path(ffmpeg), Path(ffprobe)
    root = tmp_path_factory.mktemp("poc-type-e2e")
    bframe_source = root / "type0-bframes.h264"
    type2_source = root / "type2-low-delay.h264"
    audio_source = root / "tone.aac"
    common = [
        "-y",
        "-v",
        "error",
        "-nostdin",
        "-f",
        "lavfi",
        "-i",
        "testsrc2=size=320x180:rate=30",
        "-frames:v",
        "30",
        "-an",
        "-c:v",
        "libx264",
        "-preset",
        "ultrafast",
        "-g",
        "300",
    ]
    _run(
        ffmpeg,
        *common,
        "-profile:v",
        "main",
        "-coder",
        "0",
        "-bf",
        "2",
        "-x264-params",
        "aud=1:repeat-headers=1:bframes=2:b-pyramid=none:keyint=300:min-keyint=300:scenecut=0:cabac=0",
        "-f",
        "h264",
        bframe_source,
    )
    _run(
        ffmpeg,
        *common,
        "-profile:v",
        "baseline",
        "-bf",
        "0",
        "-x264-params",
        "aud=1:repeat-headers=1:bframes=0:keyint=300:min-keyint=300:scenecut=0",
        "-f",
        "h264",
        type2_source,
    )
    _run(
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-nostdin",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=1.1",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-f",
        "adts",
        audio_source,
    )

    source_bytes = bframe_source.read_bytes()
    source_sps_nal = next(unit for unit in nals(source_bytes) if unit[0] & 31 == 7)
    source_sps = parse_sps(source_sps_nal)
    if source_sps["poc_type"] != 0:
        pytest.fail(f"x264 B-frame source unexpectedly used POC type {source_sps['poc_type']}")
    type1_bytes = rewrite_type0_stream(source_bytes, 1)
    type1_path = root / "type1-cycle-delta.h264"
    type1_path.write_bytes(type1_bytes)
    type0_path = bframe_source

    type2_bytes = type2_source.read_bytes()
    type2_sps = parse_sps(next(unit for unit in nals(type2_bytes) if unit[0] & 31 == 7))
    if type2_sps["poc_type"] != 2:
        pytest.fail(f"x264 low-delay source did not produce POC type 2 (got {type2_sps['poc_type']})")

    # Prove the derived type-1 headers retain the same decoded pictures as the
    # real POC-0 x264 bitstream, not merely that both parsers accept the SPS.
    assert _video_decode_hashes(ffmpeg, type0_path) == _video_decode_hashes(ffmpeg, type1_path)
    streams = {
        0: (type0_path, type0_path.read_bytes()),
        1: (type1_path, type1_bytes),
        2: (type2_source, type2_bytes),
    }
    metadata = {}
    for poc_type, (path, data) in streams.items():
        info = parse_sps(next(unit for unit in nals(data) if unit[0] & 31 == 7))
        if info["poc_type"] != poc_type:
            pytest.fail(f"requested fixture type {poc_type}, encoded SPS says {info['poc_type']}")
        decode = subprocess.run(
            [str(ffmpeg), "-v", "error", "-xerror", "-i", str(path), "-f", "null", "-"],
            capture_output=True,
            timeout=30,
        )
        assert decode.returncode == 0, decode.stderr.decode("utf-8", "replace")
        metadata[poc_type] = {
            "path": path,
            "data": data,
            "sps": info,
            "sha256": hashlib.sha256(data).hexdigest(),
        }
    full_audio = audio_source.read_bytes()
    audio_frames = parse_adts(full_audio).frames[:46]
    assert len(audio_frames) == 46
    audio_payload = b"".join(bytes(frame.data) for frame in audio_frames)
    return ffmpeg, ffprobe, root, metadata, audio_payload


@pytest.mark.parametrize("poc_type", [0, 1, 2])
@pytest.mark.parametrize("corrupt", [False, True], ids=["valid", "bad-vcl-header"])
def test_poc_type_full_grid_parent_streamio_and_decode(generated_poc_streams, poc_type, corrupt, monkeypatch):
    ffmpeg, ffprobe, root, streams, audio_payload = generated_poc_streams
    source_path, source = streams[poc_type]["path"], streams[poc_type]["data"]
    source_sps = streams[poc_type]["sps"]
    source_groups = _aus(source)
    assert len(source_groups) == 30

    # Grid composition is derived from FFprobe display order for type 0/1;
    # type 2 has decode order equal to output order, as required by the mode.
    if poc_type in (0, 1):
        probe = json.loads(
            _run(
                ffprobe,
                "-v",
                "error",
                "-f",
                "h264",
                "-show_frames",
                "-show_entries",
                "frame=coded_picture_number",
                "-of",
                "json",
                source_path,
            )
        )["frames"]
        display_rank = {int(row["coded_picture_number"]): rank for rank, row in enumerate(probe)}
        assert set(display_rank) == set(range(len(source_groups)))
    else:
        display_rank = dict(enumerate(range(len(source_groups))))
    lead = source_sps["max_reorder"]

    class Config:
        diagnostics_dir = None

        @staticmethod
        def clear():
            pass

    stream = SimpleNamespace(config=Config(), buffer_size=2 << 20, timeout=2)

    class LocalParentSocket:
        def __init__(self):
            self.wire = bytearray()
            self.closed = False

        def settimeout(self, _timeout):
            pass

        def recv(self, size):
            if self.closed:
                return b""
            count = min(size, 13, len(self.wire))
            result = bytes(self.wire[:count])
            del self.wire[:count]
            return result

        def close(self):
            self.closed = True

    class LocalParentNetwork:
        def __init__(self):
            self.stop = threading.Event()
            self._lock = threading.Lock()
            self._sockets = set()
            self.socket = LocalParentSocket()
            self.requests = []

        def connect(self, _address):
            with self._lock:
                self._sockets.add(self.socket)
            return self.socket

        def send(self, _sock, data):
            command = struct.unpack_from("<H", data, 2)[0]
            self.requests.append(command)
            if command == 0xCB2B:
                self.stop.set()

        def release(self, sock):
            with self._lock:
                self._sockets.discard(sock)
            sock.close()

        def close(self):
            self.stop.set()
            with self._lock:
                sockets = tuple(self._sockets)
            for sock in sockets:
                self.release(sock)

    import soop_grid.stream as grid_stream

    monkeypatch.setattr(grid_stream, "Network", LocalParentNetwork)

    def runner(_config, _network, emit, _report, stats):
        sink = MediaSink(emit)
        stats.update(sink.stats)
        sink.stats = stats
        frame_number = 0
        server_packets = [parent_packet(0xC746), parent_packet(0xC747)]
        for index, group in enumerate(source_groups):
            au = _annexb(group)
            sps_nal = next((unit for unit in group if unit[0] & 31 == 7), None)
            active_sps = parse_sps(sps_nal) if sps_nal else next(iter(sink.video_clock.sps.values()), None)
            if active_sps is None:
                active_sps = source_sps
            pps_id = next((unit for unit in group if unit[0] & 31 == 8), None)
            active_pps = (
                parse_pps(pps_id, {active_sps["id"]: active_sps})
                if pps_id
                else next(iter(sink.video_clock.pps.values()), None)
            )
            if active_pps is None:
                active_pps = parse_pps(
                    next(unit for unit in nals(source) if unit[0] & 31 == 8), {active_sps["id"]: active_sps}
                )
            vcl = next(unit for unit in group if unit[0] & 31 in (1, 5))
            header = parse_slice(vcl, active_sps, active_pps)
            frame_number += 1
            offset_frames = display_rank[index] - index + lead
            assert offset_frames >= 0
            composition = round(offset_frames * 10_000_000 / 30)
            kind = header.slice_kind if header.slice_kind in ("I", "P", "B") else "I"
            if header.idr:
                kind = "I"
            if corrupt and index == 5:
                au = bytearray(au)
                vcl_offset = au.index(b"\x00\x00\x00\x01" + vcl) + 4
                au[vcl_offset] |= 0x80  # forbidden_zero_bit: deterministic malformed NAL header
                au = bytes(au)
            server_packets.append(
                parent_packet(
                    0xC748,
                    media_body(au, kind, frame_number, BASE + index * FRAME_STEP, composition),
                )
            )
        audio_timestamp = BASE + round(lead * 10_000_000 / 30)
        frame_number += 1
        server_packets.append(
            parent_packet(0xC748, media_body(audio_payload, "A", frame_number, audio_timestamp))
        )
        server_packets.append(parent_packet(0xC742))
        _network.socket.wire.extend(b"".join(server_packets))
        receive_media(
            _network,
            [Parent(("127.0.0.1", 9000), quality=1, frame=0)],
            bno=42,
            node_key=12345,
            sink=sink,
            report=_report,
        )
        assert _network.requests == [0xCB2E, 0xCB2F, 0xCB30, 0xCB2B]
        sink.close()
        validate_media_output(sink.stats)
        stats["stop_reason"] = "duration_limit"

    reader = SoopGridReader(stream, runner=runner)
    try:
        reader.open()
        output = bytearray()
        if corrupt:
            with pytest.raises(OSError, match="h264_nal_header_invalid"):
                while True:
                    block = reader.read(64 << 10)
                    if not block:
                        break
                    output.extend(block)
        else:
            while True:
                block = reader.read(64 << 10)
                if not block:
                    break
                output.extend(block)
    finally:
        reader.close()

    if corrupt:
        assert output
        assert reader.failure_code == "h264_nal_header_invalid"
        assert reader.stats["reader_eof_observed"] == 0
        assert reader.stats["stream_output_drain_complete"] == 0
        assert reader.network.requests == [0xCB2E, 0xCB2F, 0xCB30]
        assert not reader.network._sockets
        partial_ts = root / f"poc-{poc_type}-bad-header.ts"
        partial_h264 = root / f"poc-{poc_type}-bad-header.h264"
        partial_ts.write_bytes(output)
        _run(
            ffmpeg,
            "-y",
            "-v",
            "error",
            "-i",
            partial_ts,
            "-map",
            "0:v:0",
            "-c",
            "copy",
            "-f",
            "h264",
            partial_h264,
        )
        accepted_vcl = [unit for unit in nals(partial_h264.read_bytes()) if unit[0] & 31 in (1, 5)]
        expected_prefix = [unit for group in source_groups[:5] for unit in group if unit[0] & 31 in (1, 5)]
        assert accepted_vcl == expected_prefix
        return

    assert output and len(output) % 188 == 0
    assert all(output[offset] == 0x47 for offset in range(0, len(output), 188))
    assert reader.stats["reader_eof_observed"] == 1
    assert reader.stats["stream_output_drain_complete"] == 1
    assert reader.stats["stream_output_bytes_drained"] == 1
    assert reader.stats["stream_reader_bytes"] == len(output) == reader.stats["stream_emit_bytes"]
    assert reader.stats["h264_poc_type"] == poc_type
    assert reader.stats["video_output_frames"] == 30
    assert reader.stats["audio_output_access_units"] == 46

    ts_path = root / f"poc-{poc_type}.ts"
    ts_path.write_bytes(output)
    probe = json.loads(
        _run(
            ffprobe,
            "-v",
            "error",
            "-count_frames",
            "-show_entries",
            "stream=index,codec_name,width,height,nb_read_frames,sample_rate,channels",
            "-of",
            "json",
            ts_path,
        )
    )
    video = next(stream_info for stream_info in probe["streams"] if stream_info["codec_name"] == "h264")
    audio = next(stream_info for stream_info in probe["streams"] if stream_info["codec_name"] == "aac")
    assert (video["width"], video["height"], int(video["nb_read_frames"])) == (320, 180, 30)
    assert int(audio["sample_rate"]) == 48000 and int(audio["channels"]) == 1
    _run(ffmpeg, "-v", "error", "-xerror", "-i", ts_path, "-f", "null", "-")

    packet_rows = json.loads(
        _run(
            ffprobe,
            "-v",
            "error",
            "-show_packets",
            "-show_entries",
            "packet=stream_index,pts,dts",
            "-of",
            "json",
            ts_path,
        )
    )["packets"]
    video_packets = [row for row in packet_rows if row["stream_index"] == video["index"]]
    audio_packets = [row for row in packet_rows if row["stream_index"] == audio["index"]]
    assert len(video_packets) == 30 and len(audio_packets) == 46
    video_dts = [int(row["dts"]) for row in video_packets]
    video_pts = [int(row["pts"]) for row in video_packets]
    audio_pts = [int(row["pts"]) for row in audio_packets]
    assert all(right > left for left, right in zip(video_dts, video_dts[1:], strict=False))
    assert len(set(video_pts)) == len(video_pts)
    assert all(right > left for left, right in zip(audio_pts, audio_pts[1:], strict=False))
    expected_common_start = 90_000 + round(lead * FRAME_STEP * 90_000 / 10_000_000)
    assert abs(min(video_pts) - expected_common_start) <= 1
    assert abs(min(audio_pts) - expected_common_start) <= 1

    recovered = root / f"poc-{poc_type}-demux.h264"
    _run(ffmpeg, "-y", "-v", "error", "-i", ts_path, "-map", "0:v:0", "-c", "copy", "-f", "h264", recovered)
    expected_vcl = [unit for unit in nals(source, max_units=1024) if unit[0] & 31 in (1, 5)]
    recovered_vcl = [unit for unit in nals(recovered.read_bytes(), max_units=1024) if unit[0] & 31 in (1, 5)]
    assert recovered_vcl == expected_vcl

    recovered_audio = root / f"poc-{poc_type}-demux.aac"
    _run(
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-i",
        ts_path,
        "-map",
        "0:a:0",
        "-c",
        "copy",
        "-f",
        "adts",
        recovered_audio,
    )
    expected_raw_aac = [bytes(frame.data[frame.header_bytes :]) for frame in parse_adts(audio_payload).frames]
    actual_raw_aac = [
        bytes(frame.data[frame.header_bytes :]) for frame in parse_adts(recovered_audio.read_bytes()).frames
    ]
    assert actual_raw_aac == expected_raw_aac


@pytest.mark.parametrize("poc_type", [0, 1, 2])
def test_poc_type_streamio_44100_stereo_aac_identity_and_decode(generated_poc_streams, poc_type, tmp_path):
    """Exercise 44.1 kHz stereo with each verified POC structure."""
    ffmpeg, ffprobe, root, streams, _ = generated_poc_streams
    source_path, source = streams[poc_type]["path"], streams[poc_type]["data"]
    source_sps = streams[poc_type]["sps"]
    source_groups = _aus(source)
    audio_path = root / "tone-44100-stereo.aac"
    _run(
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-nostdin",
        "-f",
        "lavfi",
        "-i",
        "aevalsrc=0.25*sin(2*PI*440*t)|0.125*sin(2*PI*997*t):s=44100:d=1.1",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-f",
        "adts",
        audio_path,
    )
    audio = parse_adts(audio_path.read_bytes())
    assert audio.config.sample_rate == 44100 and audio.config.channels == 2
    # 43 AAC-LC frames span about 0.998 s, matching this 30-frame video
    # fixture closely enough for the independent output-coverage gate.
    audio_frames = audio.frames[:43]
    assert len(audio_frames) == 43 and all(frame.core_samples == 1024 for frame in audio_frames)
    if poc_type in (0, 1):
        display_frames = json.loads(
            _run(
                ffprobe,
                "-f",
                "h264",
                "-show_frames",
                "-show_entries",
                "frame=coded_picture_number",
                "-of",
                "json",
                source_path,
            )
        )["frames"]
        display_rank = {int(frame["coded_picture_number"]): rank for rank, frame in enumerate(display_frames)}
        assert set(display_rank) == set(range(len(source_groups)))
    else:
        display_rank = dict(enumerate(range(len(source_groups))))
    lead = source_sps["max_reorder"]
    source_units = nals(source)
    pps = parse_pps(next(unit for unit in source_units if unit[0] & 31 == 8), {source_sps["id"]: source_sps})
    events = []
    for index, group in enumerate(source_groups):
        vcl = next(unit for unit in group if unit[0] & 31 in (1, 5))
        header = parse_slice(vcl, source_sps, pps)
        offset_frames = display_rank[index] - index + lead
        assert offset_frames >= 0
        composition = round(offset_frames * 10_000_000 / 30)
        events.append(
            (
                BASE + index * FRAME_STEP,
                0,
                "video",
                _annexb(group),
                "I" if header.idr else header.slice_kind,
                composition,
            )
        )
    sample_offset = 0
    for audio_frame in audio_frames:
        timestamp = (
            BASE + round(lead * 10_000_000 / 30) + sample_offset * 10_000_000 // audio.config.sample_rate
        )
        events.append((timestamp, 1, "audio", bytes(audio_frame.data), "A", 0))
        sample_offset += audio_frame.core_samples
    events.sort(key=lambda event: (event[0], event[1]))
    assert sum(left[2] != right[2] for left, right in zip(events, events[1:], strict=False)) >= 20

    class Config:
        diagnostics_dir = None

        @staticmethod
        def clear():
            pass

    stream = SimpleNamespace(config=Config(), buffer_size=2 << 20, timeout=2)

    def runner(_config, _network, emit, _report, stats):
        sink = MediaSink(emit)
        stats.update(sink.stats)
        sink.stats = stats
        frame_number = 0
        for timestamp, _priority, _track, payload, kind, composition in events:
            frame_number += 1
            sink.add(
                Frame(
                    0xC748,
                    media_body(
                        payload,
                        kind,
                        frame_number,
                        timestamp,
                        composition,
                    ),
                )
            )
        sink.close()
        validate_media_output(sink.stats)
        stats["stop_reason"] = "duration_limit"

    reader = SoopGridReader(stream, runner=runner)
    try:
        reader.open()
        output = bytearray()
        while block := reader.read(64 << 10):
            output.extend(block)
    finally:
        reader.close()

    assert output and len(output) % 188 == 0
    assert reader.stats["reader_eof_observed"] == 1
    assert reader.stats["stream_output_drain_complete"] == 1
    assert reader.stats["stream_output_bytes_drained"] == 1
    assert reader.stats["stream_reader_bytes"] == len(output) == reader.stats["stream_emit_bytes"]
    assert reader.stats["h264_poc_type"] == poc_type
    assert reader.stats["audio_output_access_units"] == len(audio_frames)

    ts_path = tmp_path / f"poc{poc_type}-44100-stereo.ts"
    ts_path.write_bytes(output)
    probe = json.loads(
        _run(
            ffprobe,
            "-count_frames",
            "-show_entries",
            "stream=codec_name,width,height,nb_read_frames,sample_rate,channels",
            "-of",
            "json",
            ts_path,
        )
    )
    video = next(item for item in probe["streams"] if item["codec_name"] == "h264")
    audio_stream = next(item for item in probe["streams"] if item["codec_name"] == "aac")
    assert (video["width"], video["height"], int(video["nb_read_frames"])) == (320, 180, 30)
    assert int(audio_stream["sample_rate"]) == 44100 and int(audio_stream["channels"]) == 2
    _run(ffmpeg, "-xerror", "-i", ts_path, "-f", "null", "-")

    recovered_video = tmp_path / f"poc{poc_type}-44100-video.h264"
    _run(ffmpeg, "-y", "-i", ts_path, "-map", "0:v:0", "-c", "copy", "-f", "h264", recovered_video)
    assert [unit for unit in nals(recovered_video.read_bytes()) if unit[0] & 31 in (1, 5)] == [
        unit for unit in nals(source) if unit[0] & 31 in (1, 5)
    ]
    recovered_audio = tmp_path / f"poc{poc_type}-44100-audio.aac"
    _run(ffmpeg, "-y", "-i", ts_path, "-map", "0:a:0", "-c", "copy", "-f", "adts", recovered_audio)
    expected_aac = [bytes(frame.data[frame.header_bytes :]) for frame in audio_frames]
    actual_aac = [
        bytes(frame.data[frame.header_bytes :]) for frame in parse_adts(recovered_audio.read_bytes()).frames
    ]
    assert actual_aac == expected_aac


@pytest.mark.parametrize("poc_type", [0, 1, 2])
def test_mmco5_progressive_grid_composition_streamio_and_decode(encoded_mmco5_poc0, poc_type, tmp_path):
    ffmpeg, ffprobe, source_path, type0_path, type0_data = encoded_mmco5_poc0
    if poc_type == 0:
        transformed_path, transformed = type0_path, type0_data
    else:
        from poc_fixture import rewrite_type0_stream

        transformed = rewrite_type0_stream(type0_data, poc_type)
        transformed_path = tmp_path / f"mmco5-poc{poc_type}.h264"
        transformed_path.write_bytes(transformed)
    assert _video_decode_hashes(ffmpeg, source_path) == _video_decode_hashes(ffmpeg, transformed_path)

    units = nals(transformed, max_units=2048)
    groups = _aus(transformed)
    assert len(groups) == 60
    sps_nal = next(unit for unit in units if unit[0] & 31 == 7)
    pps_nal = next(unit for unit in units if unit[0] & 31 == 8)
    sps = parse_sps(sps_nal)
    pps = parse_pps(pps_nal, {sps["id"]: sps})
    headers = [
        parse_slice(next(unit for unit in group if unit[0] & 31 in (1, 5)), sps, pps) for group in groups
    ]
    assert sps["poc_type"] == poc_type
    assert [index for index, header in enumerate(headers) if header.mmco5] == [10]
    assert headers[10].frame_num == 10 and headers[11].frame_num == 1
    if poc_type == 0:
        assert headers[10].poc_lsb == 20 and headers[11].poc_lsb == 22
    else:
        assert headers[10].poc_lsb is None and headers[11].poc_lsb is None

    audio_path = tmp_path / "mmco-audio.aac"
    _run(
        ffmpeg,
        "-y",
        "-v",
        "error",
        "-nostdin",
        "-f",
        "lavfi",
        "-i",
        "sine=frequency=440:sample_rate=48000:duration=2.1",
        "-c:a",
        "aac",
        "-b:a",
        "96k",
        "-f",
        "adts",
        audio_path,
    )
    audio_frames = parse_adts(audio_path.read_bytes()).frames[:94]
    assert len(audio_frames) == 94

    class Config:
        diagnostics_dir = None

        @staticmethod
        def clear():
            pass

    stream = SimpleNamespace(config=Config(), buffer_size=2 << 20, timeout=2)

    def runner(_config, _network, emit, _report, stats):
        sink = MediaSink(emit)
        stats.update(sink.stats)
        sink.stats = stats
        for index, (group, header) in enumerate(zip(groups, headers, strict=True)):
            kind = "I" if header.idr else header.slice_kind
            sink.add(
                Frame(
                    0xC748,
                    media_body(_annexb(group), kind, index + 1, BASE + index * FRAME_STEP, 0),
                )
            )
        for index, frame in enumerate(audio_frames):
            timestamp = BASE + index * 1024 * 10_000_000 // 48_000
            sink.add(Frame(0xC748, media_body(bytes(frame.data), "A", 61 + index, timestamp)))
        sink.close()
        validate_media_output(sink.stats)
        stats["stop_reason"] = "duration_limit"

    reader = SoopGridReader(stream, runner=runner)
    output = bytearray()
    try:
        reader.open()
        while block := reader.read(64 << 10):
            output.extend(block)
    finally:
        reader.close()

    assert output and len(output) % 188 == 0
    assert reader.stats["reader_eof_observed"] == 1
    assert reader.stats["stream_output_drain_complete"] == 1
    assert reader.stats["stream_reader_bytes"] == len(output) == reader.stats["stream_emit_bytes"]
    assert reader.stats["h264_poc_type"] == poc_type
    assert reader.stats["video_output_frames"] == 60
    assert reader.stats["audio_output_access_units"] == 94

    ts_path = tmp_path / f"poc{poc_type}-mmco5.ts"
    ts_path.write_bytes(output)
    _run(ffmpeg, "-v", "error", "-xerror", "-i", ts_path, "-map", "0:v:0", "-map", "0:a:0", "-f", "null", "-")
    output_video = tmp_path / f"poc{poc_type}-mmco5-demux.h264"
    _run(
        ffmpeg, "-y", "-v", "error", "-i", ts_path, "-map", "0:v:0", "-c", "copy", "-f", "h264", output_video
    )
    expected_vcl = [unit for unit in units if unit[0] & 31 in (1, 5)]
    actual_vcl = [unit for unit in nals(output_video.read_bytes()) if unit[0] & 31 in (1, 5)]
    assert actual_vcl == expected_vcl
    assert _video_decode_hashes(ffmpeg, ts_path) == _video_decode_hashes(ffmpeg, transformed_path)
