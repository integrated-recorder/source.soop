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
import mmap
import os
from pathlib import Path
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
from types import SimpleNamespace

from streamlink.exceptions import StreamError

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from soop_grid.aac import MAX_ADTS_BYTES, MAX_ADTS_FRAMES, parse_adts  # noqa: E402
from soop_grid.h264clock import parse_pps, parse_slice, parse_sps  # noqa: E402
from soop_grid.media import MediaSink  # noqa: E402
from soop_grid.mpegts import nals  # noqa: E402
from soop_grid.protocol import Cancelled, Frame, GridError  # noqa: E402
from soop_grid.stream import SoopGridReader, validate_media_output  # noqa: E402
from tools.verify_recording import verify  # noqa: E402

BASE_TIMESTAMP = 50_000_000
FPS = 10
SAMPLE_RATE = 48_000
MAX_MEDIA_BYTES = 2 << 30
MAX_FIXTURE_BYTES = 512 << 20
MAX_TOTAL_FIXTURE_BYTES = 2 << 30
MAX_SEGMENT_MINUTES = 10


def _remaining_timeout(deadline, *, now=None):
    remaining = deadline - (time.monotonic() if now is None else now)
    if remaining <= 0:
        raise subprocess.TimeoutExpired("offline_media_soak", timeout=0)
    return remaining


def _run(binary, args, deadline):
    result = subprocess.run(
        [str(binary), "-v", "error", "-nostdin", *map(str, args)],
        capture_output=True,
        timeout=_remaining_timeout(deadline),
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


def _scan_adts(path, segment_seconds=()):
    """Hash one AAC encode and locate sample-clock segment boundaries boundedly."""
    digest = hashlib.sha256()
    boundaries = [0]
    segment_counts = []
    target_counts = []
    elapsed = 0
    for seconds in segment_seconds[:-1]:
        elapsed += seconds
        target_counts.append((elapsed * SAMPLE_RATE + 1023) // 1024)
    target_index = previous_target = frame_count = 0
    config = None
    with path.open("rb") as source, mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mapped:
        cursor = 0
        while cursor < len(mapped):
            batch_start = cursor
            frame_ends = []
            while (
                cursor < len(mapped)
                and len(frame_ends) < MAX_ADTS_FRAMES
                and cursor - batch_start < MAX_ADTS_BYTES
            ):
                if len(mapped) - cursor < 7:
                    raise ValueError("generated_adts_truncated")
                header = mapped[cursor : cursor + 7]
                size = ((header[3] & 3) << 11) | (header[4] << 3) | (header[5] >> 5)
                if size < 7 or size > len(mapped) - cursor or size > MAX_ADTS_BYTES:
                    raise ValueError("generated_adts_length_invalid")
                if frame_ends and cursor + size - batch_start > MAX_ADTS_BYTES:
                    break
                cursor += size
                frame_ends.append(cursor)
            batch = parse_adts(memoryview(mapped)[batch_start:cursor])
            if (
                batch.config_changed
                or batch.config.sample_rate != SAMPLE_RATE
                or batch.config.audio_object_type != 2
            ):
                raise ValueError("generated_aac_config_invalid")
            if config is None:
                config = batch.config
            elif batch.config != config:
                raise ValueError("generated_aac_config_changed")
            for frame, end in zip(batch.frames, frame_ends, strict=True):
                if frame.raw_data_blocks != 1:
                    raise ValueError("generated_aac_blocks_unsupported")
                digest.update(frame.data)
                frame_count += 1
                if target_index < len(target_counts) and frame_count == target_counts[target_index]:
                    boundaries.append(end)
                    segment_counts.append(frame_count - previous_target)
                    previous_target = frame_count
                    target_index += 1
            del frame, batch
        if target_index != len(target_counts) or not frame_count:
            raise ValueError("generated_adts_empty_or_short")
        boundaries.append(len(mapped))
    segment_counts.append(frame_count - previous_target)
    ranges = list(zip(boundaries, boundaries[1:], strict=False))
    if segment_seconds and len(ranges) != len(segment_seconds):
        raise ValueError("generated_adts_segment_count_invalid")
    return {
        "frame_count": frame_count,
        "digest": digest.hexdigest(),
        "config": config,
        "ranges": ranges,
        "segment_counts": segment_counts,
    }


def _adts_frames_range(mapped, start, end):
    frames = []
    cursor = start
    while cursor < end:
        batch_start = cursor
        frame_ends = []
        while cursor < end and len(frame_ends) < MAX_ADTS_FRAMES and cursor - batch_start < MAX_ADTS_BYTES:
            if end - cursor < 7:
                raise ValueError("generated_adts_truncated")
            header = mapped[cursor : cursor + 7]
            size = ((header[3] & 3) << 11) | (header[4] << 3) | (header[5] >> 5)
            if size < 7 or size > end - cursor or size > MAX_ADTS_BYTES:
                raise ValueError("generated_adts_length_invalid")
            if frame_ends and cursor + size - batch_start > MAX_ADTS_BYTES:
                break
            cursor += size
            frame_ends.append(cursor)
        parsed = parse_adts(memoryview(mapped)[batch_start:cursor])
        if (
            parsed.config_changed
            or parsed.config.sample_rate != SAMPLE_RATE
            or parsed.config.audio_object_type != 2
        ):
            raise ValueError("generated_aac_config_invalid")
        if any(frame.raw_data_blocks != 1 for frame in parsed.frames):
            raise ValueError("generated_aac_blocks_unsupported")
        frames.extend(bytes(frame.data) for frame in parsed.frames)
        del parsed
    return frames


def _body(payload, kind, frame_number, timestamp, composition=0):
    body = bytearray(69 + len(payload))
    struct.pack_into("<HHIIQ", body, 0, 1, 69, 0, len(payload), frame_number)
    body[40] = ord(kind)
    struct.pack_into("<Q", body, 41, timestamp)
    struct.pack_into("<I", body, 57, composition)
    body[69:] = payload
    return bytes(body)


def _update_payload_identity(digest, data, *, kinds):
    import re

    count = starts = 0
    previous = None
    for match in re.finditer(b"\x00\x00(?:\x00)?\x01", data):
        starts += 1
        if starts > 2_000_000:
            raise GridError("h264_nal_count_limit")
        if previous is not None:
            unit = data[previous.end() : match.start()]
            if unit and unit[0] & 31 in kinds:
                digest.update(len(unit).to_bytes(4, "big"))
                digest.update(unit)
                count += 1
        previous = match
    if previous is not None:
        unit = data[previous.end() : len(data)]
        if unit and unit[0] & 31 in kinds:
            digest.update(len(unit).to_bytes(4, "big"))
            digest.update(unit)
            count += 1
    return count


def _payload_identity(data, *, kinds):
    digest = hashlib.sha256()
    count = _update_payload_identity(digest, data, kinds=kinds)
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


def _resource_sample():
    return {
        "rss_kib": _rss_kib(),
        "fd_count": _fd_count(),
        "thread_count": threading.active_count(),
    }


def _pace_until(network, wall_start, media_timestamp, deadline):
    target = wall_start + max(0, media_timestamp - BASE_TIMESTAMP) / 10_000_000
    delay = target - time.monotonic()
    if delay <= 0:
        return
    remaining = _remaining_timeout(deadline)
    if delay >= remaining:
        if network.stop.wait(remaining):
            raise Cancelled("offline_soak_cancelled")
        raise subprocess.TimeoutExpired("offline_media_soak", timeout=0)
    if network.stop.wait(delay):
        raise Cancelled("offline_soak_cancelled")


def run(
    minutes,
    ffmpeg,
    ffprobe,
    timeout,
    output_cap,
    realtime=False,
    b_frames=False,
    poc1_b_frames=False,
    reference_b_frames=False,
    poc1_reference_b_frames=False,
):
    if not 1 <= minutes <= 360:
        raise ValueError("timeline_duration_invalid")
    if sum((b_frames, poc1_b_frames, reference_b_frames, poc1_reference_b_frames)) > 1:
        raise ValueError("b_frame_poc_mode_conflict")
    duration = minutes * 60
    if output_cap < 1 << 20 or output_cap > MAX_MEDIA_BYTES:
        raise ValueError("output_cap_invalid")
    started = time.monotonic()
    deadline = started + timeout
    with tempfile.TemporaryDirectory(prefix="soop-grid-offline-soak-") as temp:
        work = Path(temp)
        output_path = work / "output.ts"
        chunks = []
        generated_input_bytes = 0
        source_video_digest = hashlib.sha256()
        source_video_count = 0
        sps_info = None
        b_picture_count = 0
        reference_b_vcl_count = 0
        audio_path = work / "source.aac"
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
            deadline,
        )
        segment_seconds = [
            min(MAX_SEGMENT_MINUTES, minutes - start) * 60 for start in range(0, minutes, MAX_SEGMENT_MINUTES)
        ]
        audio_facts = _scan_adts(audio_path, segment_seconds)
        source_audio_digest_hex = audio_facts["digest"]
        generated_input_bytes = audio_path.stat().st_size
        if generated_input_bytes > MAX_TOTAL_FIXTURE_BYTES:
            raise RuntimeError("soak_fixture_size_limit")

        use_b_frames = b_frames or poc1_b_frames or reference_b_frames or poc1_reference_b_frames
        if poc1_b_frames or poc1_reference_b_frames:
            tests_path = str(ROOT / "tests")
            if tests_path not in sys.path:
                sys.path.insert(0, tests_path)
            from poc_fixture import rewrite_type0_stream

        for segment_start in range(0, minutes, MAX_SEGMENT_MINUTES):
            segment_minutes = min(MAX_SEGMENT_MINUTES, minutes - segment_start)
            segment_duration = segment_minutes * 60
            video_path = work / f"source-{segment_start:03d}.h264"
            video_frames_expected = segment_duration * FPS
            x264_params = (
                "aud=1:repeat-headers=1:open-gop=0:bframes="
                + ("3" if reference_b_frames or poc1_reference_b_frames else "2")
                + ":b-adapt=0:b-pyramid="
                + ("normal" if reference_b_frames or poc1_reference_b_frames else "none")
                + ":keyint=100:min-keyint=100:scenecut=0"
                if use_b_frames
                else "aud=1:repeat-headers=1:bframes=0:keyint=100:min-keyint=100:scenecut=0"
            )
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
                    "main" if use_b_frames else "baseline",
                    "-b:v",
                    "350k",
                    "-x264-params",
                    x264_params,
                    "-f",
                    "h264",
                    video_path,
                ],
                deadline,
            )
            segment_input_bytes = video_path.stat().st_size
            generated_input_bytes += segment_input_bytes
            if segment_input_bytes > MAX_FIXTURE_BYTES or generated_input_bytes > MAX_TOTAL_FIXTURE_BYTES:
                raise RuntimeError("soak_fixture_size_limit")
            video_data = video_path.read_bytes()
            timeline_video_path = video_path
            if poc1_b_frames or poc1_reference_b_frames:
                video_data = rewrite_type0_stream(video_data, 1)
                generated_input_bytes += len(video_data)
                if len(video_data) > MAX_FIXTURE_BYTES or generated_input_bytes > MAX_TOTAL_FIXTURE_BYTES:
                    raise RuntimeError("soak_fixture_size_limit")
                timeline_video_path = video_path.with_suffix(".poc1.h264")
                timeline_video_path.write_bytes(video_data)
            video_aus = _access_units(video_data, video_frames_expected)
            sps = next((unit for unit in nals(video_data) if unit[0] & 31 == 7), None)
            if sps is None:
                raise ValueError("generated_sps_missing")
            current_sps = parse_sps(sps)
            expected_poc_type = (
                1
                if poc1_b_frames or poc1_reference_b_frames
                else 0
                if (b_frames or reference_b_frames)
                else 2
            )
            if (
                current_sps["poc_type"] != expected_poc_type
                or current_sps["height"] != 180
                or current_sps["width"] != 320
            ):
                raise ValueError("generated_sps_unexpected")
            if sps_info is None:
                sps_info = current_sps
            elif current_sps != sps_info:
                raise ValueError("generated_sps_changed_between_segments")
            composition_offsets = [0] * video_frames_expected
            if use_b_frames:
                probe = subprocess.run(
                    [
                        str(ffprobe),
                        "-v",
                        "error",
                        "-f",
                        "h264",
                        "-show_frames",
                        "-show_entries",
                        "frame=coded_picture_number,pict_type",
                        "-of",
                        "json",
                        str(timeline_video_path),
                    ],
                    capture_output=True,
                    timeout=_remaining_timeout(deadline),
                    check=True,
                )
                frame_rows = json.loads(probe.stdout)["frames"]
                display_rank = {int(row["coded_picture_number"]): rank for rank, row in enumerate(frame_rows)}
                if set(display_rank) != set(range(video_frames_expected)):
                    raise ValueError("generated_bframe_order_unverified")
                b_picture_count += sum(row.get("pict_type") == "B" for row in frame_rows)
                if not b_picture_count or current_sps["max_reorder"] < 1:
                    raise ValueError("generated_bframe_sps_mismatch")
                lead = current_sps["max_reorder"]
                for coded_index in range(video_frames_expected):
                    offset_frames = display_rank[coded_index] - coded_index + lead
                    if offset_frames < 0:
                        raise ValueError("generated_bframe_composition_negative")
                    composition_offsets[coded_index] = round(offset_frames * 10_000_000 / FPS)
            if reference_b_frames or poc1_reference_b_frames:
                pps_nal = next(unit for unit in nals(video_data) if unit[0] & 31 == 8)
                pps_info = parse_pps(pps_nal, {current_sps["id"]: current_sps})
                reference_b_vcl_count += sum(
                    header.slice_kind == "B" and bool(header.nal_ref_idc)
                    for header in (
                        parse_slice(unit, current_sps, pps_info)
                        for unit in nals(video_data)
                        if unit[0] & 31 in (1, 5)
                    )
                )
                if current_sps["max_reorder"] < 2 or reference_b_vcl_count == 0:
                    raise ValueError("generated_reference_b_picture_unverified")
            source_video_count += _update_payload_identity(source_video_digest, video_data, kinds=(1, 5))
            audio_start, audio_end = audio_facts["ranges"][len(chunks)]
            chunks.append(
                {
                    "video_path": timeline_video_path,
                    "video_frames": len(video_aus),
                    "audio_start": audio_start,
                    "audio_end": audio_end,
                    "audio_frames": audio_facts["segment_counts"][len(chunks)],
                    "composition_offsets": composition_offsets,
                }
            )
            del video_aus, video_data

        source_video_identity = source_video_count, source_video_digest.hexdigest()

        class Config:
            diagnostics_dir = None

            @staticmethod
            def clear():
                pass

        # Give the offline reader a finite readiness window bounded by the
        # remaining overall deadline; production timeout policy is unchanged.
        stream = SimpleNamespace(config=Config(), buffer_size=2 << 20, timeout=_remaining_timeout(deadline))

        def runner(_config, _network, emit, _report, stats):
            sink = MediaSink(emit, synchronize_startup=True)
            stats.update(sink.stats)
            sink.stats = stats
            video_index = audio_index = frame_number = 0
            media_wall_start = time.monotonic()
            try:
                with (
                    audio_path.open("rb") as source,
                    mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as audio_map,
                ):
                    for chunk in chunks:
                        video_aus = _access_units(chunk["video_path"].read_bytes(), chunk["video_frames"])
                        audio_frames = _adts_frames_range(audio_map, chunk["audio_start"], chunk["audio_end"])
                        if len(audio_frames) != chunk["audio_frames"]:
                            raise ValueError("generated_aac_segment_count_invalid")
                        chunk_video_index = chunk_audio_index = 0
                        while chunk_video_index < len(video_aus) or chunk_audio_index < len(audio_frames):
                            video_time = (
                                BASE_TIMESTAMP + video_index * 10_000_000 // FPS
                                if chunk_video_index < len(video_aus)
                                else None
                            )
                            audio_time = (
                                BASE_TIMESTAMP
                                + sps_info["max_reorder"] * 10_000_000 // FPS
                                + audio_index * 1024 * 10_000_000 // SAMPLE_RATE
                                if chunk_audio_index < len(audio_frames)
                                else None
                            )
                            if video_time is not None and (audio_time is None or video_time <= audio_time):
                                payload = video_aus[chunk_video_index]
                                kind = "I" if any(unit[0] & 31 == 5 for unit in nals(payload)) else "P"
                                timestamp = video_time
                                composition = chunk["composition_offsets"][chunk_video_index]
                                chunk_video_index += 1
                                video_index += 1
                            else:
                                payload = audio_frames[chunk_audio_index]
                                kind = "A"
                                timestamp = audio_time
                                composition = 0
                                chunk_audio_index += 1
                                audio_index += 1
                            frame_number += 1
                            if realtime:
                                _pace_until(_network, media_wall_start, timestamp, deadline)
                            sink.add(
                                Frame(0xC748, _body(payload, kind, frame_number, timestamp, composition))
                            )
                        del video_aus, audio_frames
                sink.close()
                validate_media_output(sink.stats)
                stats["stop_reason"] = "duration_limit"
            except BaseException:
                if not sink.closed:
                    sink.close()
                raise

        reader = SoopGridReader(stream, runner=runner)
        before_fds = _fd_count()
        resource_samples = []
        output_bytes = 0
        reader.open()
        try:
            with output_path.open("xb") as output:
                while True:
                    _remaining_timeout(deadline)
                    block = reader.read(64 << 10)
                    if not block:
                        break
                    output_bytes += len(block)
                    if output_bytes > output_cap:
                        raise RuntimeError("soak_output_limit")
                    output.write(block)
                    now = time.monotonic()
                    if not resource_samples or now - resource_samples[-1][0] >= 30:
                        resource_samples.append((now, _resource_sample()))
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
            timeout=_remaining_timeout(deadline),
            minimum_duration=duration - 2,
        )
        if not validation["passed"]:
            raise RuntimeError("soak_recording_validation_failed")

        demux_video = work / "output.h264"
        demux_audio = work / "output.aac"
        _run(
            ffmpeg,
            ["-i", output_path, "-map", "0:v:0", "-c:v", "copy", "-f", "h264", demux_video],
            deadline,
        )
        _run(
            ffmpeg,
            ["-i", output_path, "-map", "0:a:0", "-c:a", "copy", "-f", "adts", demux_audio],
            deadline,
        )
        with (
            demux_video.open("rb") as source,
            mmap.mmap(source.fileno(), 0, access=mmap.ACCESS_READ) as mapped,
        ):
            output_video_identity = _payload_identity(mapped, kinds=(1, 5))
        if output_video_identity != source_video_identity:
            raise RuntimeError("soak_video_vcl_identity_mismatch")
        output_audio_facts = _scan_adts(demux_audio)
        if (
            output_audio_facts["digest"] != source_audio_digest_hex
            or output_audio_facts["frame_count"] != audio_facts["frame_count"]
        ):
            raise RuntimeError("soak_aac_identity_mismatch")

        after_fds = _fd_count()
        resource_samples.append((time.monotonic(), _resource_sample()))
        if before_fds is not None and after_fds != before_fds:
            raise RuntimeError("soak_fd_delta")
        elapsed = round(time.monotonic() - started, 3)
        rss_values = [sample[1]["rss_kib"] for sample in resource_samples if sample[1]["rss_kib"] is not None]
        fd_values = [
            sample[1]["fd_count"] for sample in resource_samples if sample[1]["fd_count"] is not None
        ]
        thread_values = [sample[1]["thread_count"] for sample in resource_samples]
        return {
            "verdict": "pass",
            "scope": "offline_generated_media_realtime_paced"
            if realtime
            else "generated_media_timeline_not_live_or_realtime",
            "realtime_paced": realtime,
            "timeline_seconds": duration,
            "elapsed_wall_seconds": elapsed,
            "generated_input_bytes": generated_input_bytes,
            "sps": {
                "width": sps_info["width"],
                "height": sps_info["height"],
                "poc_type": sps_info["poc_type"],
                "max_reorder": sps_info["max_reorder"],
                "b_picture_count": b_picture_count,
                "reference_b_vcl_count": reference_b_vcl_count,
            },
            "audio": {
                "sample_rate": SAMPLE_RATE,
                "input_adts_frames": audio_facts["frame_count"],
                "output_adts_frames": output_audio_facts["frame_count"],
                "identity_sha256": source_audio_digest_hex,
            },
            "video": {
                "input_access_units": sum(chunk["video_frames"] for chunk in chunks),
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
                "resource_samples": len(resource_samples),
                "rss_kib_first_last_peak": [rss_values[0], rss_values[-1], max(rss_values)]
                if rss_values
                else None,
                "fd_count_first_last_peak": [fd_values[0], fd_values[-1], max(fd_values)]
                if fd_values
                else None,
                "thread_count_first_last_peak": [thread_values[0], thread_values[-1], max(thread_values)],
                "fd_count_before_after": [before_fds, after_fds],
            },
        }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--minutes", type=int, default=10, choices=range(1, 361))
    parser.add_argument("--ffmpeg", default=os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg"))
    parser.add_argument("--ffprobe", default=os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe"))
    parser.add_argument("--timeout", type=float, default=900)
    parser.add_argument("--max-output-mib", type=int, default=512, choices=range(1, 2049))
    parser.add_argument(
        "--realtime",
        action="store_true",
        help="pace synthetic Grid media in wall-clock time; not a live SOOP test",
    )
    parser.add_argument(
        "--b-frames",
        action="store_true",
        help="generate and probe POC-Type-0 B pictures, then apply composition timestamps",
    )
    parser.add_argument(
        "--poc1-b-frames",
        action="store_true",
        help="transform the generated POC-0 B-picture stream to POC Type 1 and verify it",
    )
    parser.add_argument(
        "--reference-b-frames",
        action="store_true",
        help="generate POC-Type-0 B-pyramid pictures and verify reference B slices",
    )
    parser.add_argument(
        "--poc1-reference-b-frames",
        action="store_true",
        help="transform generated POC-Type-0 reference B pictures to POC Type 1 and verify",
    )
    args = parser.parse_args()
    if sum((args.b_frames, args.poc1_b_frames, args.reference_b_frames, args.poc1_reference_b_frames)) > 1:
        parser.error("B-frame mode options are mutually exclusive")
    if not args.ffmpeg or not args.ffprobe:
        parser.error("FFmpeg and FFprobe are required")
    if not 1 <= args.timeout <= 28800:
        parser.error("timeout must be in 1..28800 seconds")
    try:
        summary = run(
            args.minutes,
            args.ffmpeg,
            args.ffprobe,
            args.timeout,
            args.max_output_mib << 20,
            args.realtime,
            args.b_frames,
            args.poc1_b_frames,
            args.reference_b_frames,
            args.poc1_reference_b_frames,
        )
    except (GridError, OSError, RuntimeError, StreamError, ValueError, subprocess.TimeoutExpired):
        print(json.dumps({"verdict": "fail", "error": "offline_media_soak_failed"}))
        return 1
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
