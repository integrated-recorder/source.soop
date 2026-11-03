#!/usr/bin/env python3
# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""Bounded generated-media soak through MediaSink, StreamIO, TS and FFmpeg.

This exercises a synthetic media timeline only. It opens no SOOP connection
and is not live-network or real-time pacing evidence.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import time
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from soop_grid.aac import MAX_ADTS_BYTES, MAX_ADTS_FRAMES, parse_adts  # noqa: E402
from soop_grid.h264clock import parse_sps  # noqa: E402
from soop_grid.media import MediaSink  # noqa: E402
from soop_grid.mpegts import nals  # noqa: E402
from soop_grid.protocol import Frame, GridError  # noqa: E402
from soop_grid.stream import SoopGridReader, validate_media_output  # noqa: E402
from tools.verify_recording import verify  # noqa: E402

BASE_TIMESTAMP = 50_000_000
FPS = 10
SAMPLE_RATE = 48_000
MAX_MEDIA_BYTES = 1 << 30


def _run(binary, args, timeout):
    result = subprocess.run(
        [str(binary), "-v", "error", "-nostdin", *map(str, args)],
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode:
        raise RuntimeError("fixture_generation_failed")


def _access_units(data, expected_count):
    units = nals(data, max_units=max(1024, expected_count * 8))
    groups, current = [], []
    for unit in units:
        if unit[0] & 31 == 9 and current:
            groups.append(current)
            current = []
        current.append(unit)
    if current:
        groups.append(current)
    if len(groups) != expected_count:
        raise ValueError("generated_video_access_unit_count_invalid")
    if any(not any(unit[0] & 31 in (1, 5) for unit in group) for group in groups):
        raise ValueError("generated_video_access_unit_missing_vcl")
    return [b"".join(b"\x00\x00\x00\x01" + unit for unit in group) for group in groups]


def _adts_frames(path):
    data = path.read_bytes()
    frames = []
    offset = 0
    while offset < len(data):
        end = offset
        count = 0
        while end < len(data) and count < MAX_ADTS_FRAMES:
            if len(data) - end < 7:
                raise ValueError("generated_adts_truncated")
            header = data[end : end + 7]
            size = ((header[3] & 3) << 11) | (header[4] << 3) | (header[5] >> 5)
            if size < 7 or size > len(data) - end:
                raise ValueError("generated_adts_length_invalid")
            if count and end + size - offset > MAX_ADTS_BYTES:
                break
            end += size
            count += 1
        parsed = parse_adts(memoryview(data)[offset:end])
        if parsed.config.sample_rate != SAMPLE_RATE or parsed.config.audio_object_type != 2:
            raise ValueError("generated_aac_config_invalid")
        frames.extend(bytes(frame.data) for frame in parsed.frames)
        offset = end
    if not frames:
        raise ValueError("generated_adts_empty")
    return frames


def _body(payload, kind, frame_number, timestamp):
    body = bytearray(69 + len(payload))
    struct.pack_into("<HHIIQ", body, 0, 1, 69, 0, len(payload), frame_number)
    body[40] = ord(kind)
    struct.pack_into("<Q", body, 41, timestamp)
    struct.pack_into("<I", body, 57, 0)
    body[69:] = payload
    return bytes(body)


def _payload_identity(data, *, kinds):
    digest = hashlib.sha256()
    count = 0
    for unit in nals(data, max_units=2_000_000):
        if unit[0] & 31 in kinds:
            digest.update(len(unit).to_bytes(4, "big"))
            digest.update(unit)
            count += 1
    return count, digest.hexdigest()


def _rss_kib():
    try:
        with open("/proc/self/status", encoding="ascii") as status:
            for line in status:
                if line.startswith("VmRSS:"):
                    return int(line.split()[1])
    except OSError:
        return None
    return None


def _fd_count():
    try:
        return len(os.listdir("/proc/self/fd"))
    except OSError:
        return None


def run(minutes, ffmpeg, ffprobe, timeout, output_cap):
    duration = minutes * 60
    video_frames_expected = duration * FPS
    if output_cap < 1 << 20 or output_cap > MAX_MEDIA_BYTES:
        raise ValueError("output_cap_invalid")
    started = time.monotonic()
    with tempfile.TemporaryDirectory(prefix="soop-grid-offline-soak-") as temp:
        work = Path(temp)
        video_path = work / "source.h264"
        audio_path = work / "source.aac"
        output_path = work / "output.ts"
        _run(
            ffmpeg,
            [
                "-f",
                "lavfi",
                "-i",
                f"testsrc2=size=320x180:rate={FPS}",
                "-frames:v",
                video_frames_expected,
                "-an",
                "-c:v",
                "libx264",
                "-preset",
                "ultrafast",
                "-profile:v",
                "baseline",
                "-b:v",
                "350k",
                "-x264-params",
                "aud=1:repeat-headers=1:bframes=0:keyint=100:min-keyint=100:scenecut=0",
                "-f",
                "h264",
                video_path,
            ],
            min(timeout, 300),
        )
        _run(
            ffmpeg,
            [
                "-f",
                "lavfi",
                "-i",
                f"sine=frequency=440:sample_rate={SAMPLE_RATE}:duration={duration}",
                "-c:a",
                "aac",
                "-b:a",
                "96k",
                "-f",
                "adts",
                audio_path,
            ],
            min(timeout, 300),
        )

        video_data = video_path.read_bytes()
        video_aus = _access_units(video_data, video_frames_expected)
        sps = next((unit for unit in nals(video_data) if unit[0] & 31 == 7), None)
        if sps is None:
            raise ValueError("generated_sps_missing")
        sps_info = parse_sps(sps)
        # This installed libx264 emits POC Type 2 for the no-B-frame
        # Baseline stream. Record and enforce the observed SPS, rather than
        # claiming Type 0 based on encoder options that do not select POC.
        if sps_info["poc_type"] != 2 or sps_info["height"] != 180 or sps_info["width"] != 320:
            raise ValueError("generated_sps_unexpected")
        audio_frames = _adts_frames(audio_path)
        source_video_identity = _payload_identity(video_data, kinds=(1, 5))
        source_audio_digest = hashlib.sha256(b"".join(audio_frames)).hexdigest()

        class Config:
            diagnostics_dir = None

            @staticmethod
            def clear():
                pass

        stream = SimpleNamespace(config=Config(), buffer_size=2 << 20, timeout=5)

        def runner(_config, _network, emit, _report, stats):
            sink = MediaSink(emit, synchronize_startup=True)
            stats.update(sink.stats)
            sink.stats = stats
            video_index = audio_index = frame_number = 0
            try:
                while video_index < len(video_aus) or audio_index < len(audio_frames):
                    video_time = (
                        BASE_TIMESTAMP + video_index * 10_000_000 // FPS
                        if video_index < len(video_aus)
                        else None
                    )
                    audio_time = (
                        BASE_TIMESTAMP + audio_index * 1024 * 10_000_000 // SAMPLE_RATE
                        if audio_index < len(audio_frames)
                        else None
                    )
                    if video_time is not None and (audio_time is None or video_time <= audio_time):
                        payload = video_aus[video_index]
                        kind = "I" if any(unit[0] & 31 == 5 for unit in nals(payload)) else "P"
                        timestamp = video_time
                        video_index += 1
                    else:
                        payload = audio_frames[audio_index]
                        kind = "A"
                        timestamp = audio_time
                        audio_index += 1
                    frame_number += 1
                    sink.add(Frame(0xC748, _body(payload, kind, frame_number, timestamp)))
                sink.close()
                validate_media_output(sink.stats)
                stats["stop_reason"] = "duration_limit"
            except BaseException:
                if not sink.closed:
                    sink.close()
                raise

        reader = SoopGridReader(stream, runner=runner)
        before_fds = _fd_count()
        rss_samples = []
        output_bytes = 0
        reader.open()
        try:
            with output_path.open("xb") as output:
                while True:
                    block = reader.read(64 << 10)
                    if not block:
                        break
                    output_bytes += len(block)
                    if output_bytes > output_cap:
                        raise RuntimeError("soak_output_limit")
                    output.write(block)
                    if not rss_samples or time.monotonic() - rss_samples[-1][0] >= 1:
                        rss_samples.append((time.monotonic(), _rss_kib()))
        finally:
            reader.close()

        if reader.thread is not None and reader.thread.is_alive():
            raise RuntimeError("soak_reader_worker_alive")
        if reader.stats.get("reader_eof_observed") != 1:
            raise RuntimeError("soak_eof_missing")
        if reader.stats.get("stream_output_drain_complete") != 1:
            raise RuntimeError("soak_drain_incomplete")
        for emitted, observed in (
            ("stream_emit_bytes", output_bytes),
            ("stream_reader_bytes", output_bytes),
            ("stream_buffer_accepted_bytes", output_bytes),
        ):
            if reader.stats.get(emitted) != observed:
                raise RuntimeError("soak_byte_accounting_mismatch")
        if reader.stats.get("stream_buffer_discarded_bytes", 0) or reader.stats.get(
            "stream_buffer_unaccepted_bytes", 0
        ):
            raise RuntimeError("soak_output_discarded")
        if output_bytes % 188:
            raise RuntimeError("soak_ts_alignment_invalid")

        validation = verify(
            output_path,
            ffprobe=ffprobe,
            ffmpeg=ffmpeg,
            timeout=timeout,
            minimum_duration=duration - 2,
        )
        if not validation["passed"]:
            raise RuntimeError("soak_recording_validation_failed")

        demux_video = work / "output.h264"
        demux_audio = work / "output.aac"
        _run(
            ffmpeg,
            ["-i", output_path, "-map", "0:v:0", "-c:v", "copy", "-f", "h264", demux_video],
            min(timeout, 300),
        )
        _run(
            ffmpeg,
            ["-i", output_path, "-map", "0:a:0", "-c:a", "copy", "-f", "adts", demux_audio],
            min(timeout, 300),
        )
        output_video_identity = _payload_identity(demux_video.read_bytes(), kinds=(1, 5))
        if output_video_identity != source_video_identity:
            raise RuntimeError("soak_video_vcl_identity_mismatch")
        output_audio_frames = _adts_frames(demux_audio)
        output_audio_digest = hashlib.sha256(b"".join(output_audio_frames)).hexdigest()
        if output_audio_digest != source_audio_digest or len(output_audio_frames) != len(audio_frames):
            raise RuntimeError("soak_aac_identity_mismatch")

        after_fds = _fd_count()
        if before_fds is not None and after_fds != before_fds:
            raise RuntimeError("soak_fd_delta")
        elapsed = round(time.monotonic() - started, 3)
        rss_values = [sample[1] for sample in rss_samples if sample[1] is not None]
        return {
            "verdict": "pass",
            "scope": "generated_media_timeline_not_live_or_realtime",
            "timeline_seconds": duration,
            "elapsed_wall_seconds": elapsed,
            "sps": {
                "width": sps_info["width"],
                "height": sps_info["height"],
                "poc_type": sps_info["poc_type"],
                "max_reorder": sps_info["max_reorder"],
            },
            "audio": {
                "sample_rate": SAMPLE_RATE,
                "input_adts_frames": len(audio_frames),
                "output_adts_frames": len(output_audio_frames),
                "identity_sha256": source_audio_digest,
            },
            "video": {
                "input_access_units": len(video_aus),
                "input_vcl_nals": source_video_identity[0],
                "output_vcl_nals": output_video_identity[0],
                "identity_sha256": source_video_identity[1],
            },
            "output": {
                "bytes": output_bytes,
                "sha256": validation.get("ts_sha256"),
                "ts_packets": validation["ts"]["packets"],
                "ts_continuity_errors": validation["ts"]["continuity_errors"],
                "psi_crc_errors": validation["ts"]["psi_crc_errors"],
                "pcr_max_gap_seconds": validation["ts"]["max_pcr_value_delta_seconds"],
                "decoded_av": validation["decoded_av"],
                "streamio_eof_drain": True,
                "peak_buffer_bytes": reader.buffer.peak_bytes,
                "rss_sample_peak_kib": max(rss_values) if rss_values else None,
                "fd_count_before_after": [before_fds, after_fds],
            },
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=10, choices=range(1, 31))
    parser.add_argument("--ffmpeg", default=os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg"))
    parser.add_argument("--ffprobe", default=os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe"))
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--max-output-mib", type=int, default=512)
    args = parser.parse_args()
    if not args.ffmpeg or not args.ffprobe:
        parser.error("FFmpeg and FFprobe are required")
    if not 1 <= args.timeout <= 3600:
        parser.error("timeout must be in 1..3600 seconds")
    try:
        summary = run(
            args.minutes,
            args.ffmpeg,
            args.ffprobe,
            args.timeout,
            args.max_output_mib << 20,
        )
    except (GridError, OSError, RuntimeError, ValueError, subprocess.TimeoutExpired):
        print(json.dumps({"verdict": "fail", "error": "offline_media_soak_failed"}))
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
