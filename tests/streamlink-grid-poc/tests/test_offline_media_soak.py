# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
import os
import shutil
import subprocess
import sys
import threading
import time
from types import SimpleNamespace

import pytest

from soop_grid.protocol import Cancelled
from tools.offline_media_soak import (
    MAX_SEGMENT_MINUTES,
    _body,
    _decoded_frame_identity,
    _pace_until,
    _remaining_timeout,
    _run,
    run,
)


def test_offline_soak_parent_body_serializes_composition_offset():
    body = _body(b"fixture-vcl", "P", 7, 123_456_789, composition=234_567)
    assert int.from_bytes(body[57:61], "little") == 234_567
    assert body[69:] == b"fixture-vcl"


def test_offline_soak_uses_one_global_subprocess_deadline():
    assert _remaining_timeout(100, now=90) == 10
    assert _remaining_timeout(900, now=0) == 900
    assert _remaining_timeout(100, now=99.25) == 0.75


def test_offline_soak_expired_deadline_fails_closed():
    with pytest.raises(subprocess.TimeoutExpired):
        _remaining_timeout(10, now=10)


def test_offline_soak_frame_identity_rejects_decoder_failure(monkeypatch):
    monkeypatch.setattr(
        "tools.offline_media_soak.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=1, stdout=b""),
    )
    with pytest.raises(RuntimeError, match="decoded_frame_identity_failed"):
        _decoded_frame_identity("ffmpeg", "fixture.h264", time.monotonic() + 1)


def test_offline_soak_kills_child_at_global_deadline(tmp_path):
    child = tmp_path / "slow-fixture-generator"
    child.write_text(f"#!{sys.executable}\nimport time\ntime.sleep(30)\n", encoding="utf-8")
    child.chmod(0o755)
    started = time.monotonic()
    with pytest.raises(subprocess.TimeoutExpired):
        _run(child, [], started + 0.05)
    assert time.monotonic() - started < 2


def test_offline_soak_chunks_fixture_to_bound_peak_input_working_set():
    assert MAX_SEGMENT_MINUTES == 10


def test_offline_soak_rejects_conflicting_b_frame_modes():
    with pytest.raises(ValueError, match="b_frame_poc_mode_conflict"):
        run(1, "unused-ffmpeg", "unused-ffprobe", 1, 1 << 20, b_frames=True, poc1_b_frames=True)
    with pytest.raises(ValueError, match="b_frame_poc_mode_conflict"):
        run(1, "unused-ffmpeg", "unused-ffprobe", 1, 1 << 20, b_frames=True, reference_b_frames=True)
    with pytest.raises(ValueError, match="b_frame_poc_mode_conflict"):
        run(
            1,
            "unused-ffmpeg",
            "unused-ffprobe",
            1,
            1 << 20,
            reference_b_frames=True,
            poc1_reference_b_frames=True,
        )


def test_offline_soak_poc1_bframes_survive_production_sink_and_decode():
    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg and FFprobe are required for the POC Type 1 timeline fixture")
    result = run(1, ffmpeg, ffprobe, 120, 128 << 20, poc1_b_frames=True)
    assert result["sps"]["poc_type"] == 1
    assert result["sps"]["b_picture_count"] > 0
    assert result["video"]["input_access_units"] == result["video"]["output_vcl_nals"]
    assert result["output"]["streamio_eof_drain"]


def test_offline_soak_reference_bframes_exercise_deeper_reorder_and_decode():
    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg and FFprobe are required for reference B-picture fixtures")
    result = run(1, ffmpeg, ffprobe, 120, 128 << 20, reference_b_frames=True)
    assert result["sps"]["poc_type"] == 0
    assert result["sps"]["max_reorder"] >= 2
    assert result["sps"]["reference_b_vcl_count"] > 0
    assert result["video"]["input_access_units"] == result["video"]["output_vcl_nals"]
    assert result["audio"]["input_adts_frames"] == result["audio"]["output_adts_frames"]
    assert result["output"]["ts_continuity_errors"] == 0
    assert result["output"]["psi_crc_errors"] == 0
    assert result["output"]["pcr_max_gap_seconds"] <= 0.1
    assert result["output"]["streamio_eof_drain"]


def test_offline_soak_poc1_reference_bframes_survive_production_sink_and_decode():
    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    ffprobe = os.environ.get("SOOP_TEST_FFPROBE") or shutil.which("ffprobe")
    if not ffmpeg or not ffprobe:
        pytest.skip("FFmpeg and FFprobe are required for POC Type 1 reference B-picture fixtures")
    result = run(1, ffmpeg, ffprobe, 120, 128 << 20, poc1_reference_b_frames=True)
    assert result["sps"]["poc_type"] == 1
    assert result["sps"]["max_reorder"] >= 2
    assert result["sps"]["reference_b_vcl_count"] > 0
    assert result["sps"]["type1_transform_frame_identity"]
    assert result["sps"]["type1_transform_decoded_frame_count"] == 600
    assert result["video"]["input_access_units"] == result["video"]["output_vcl_nals"]
    assert result["audio"]["input_adts_frames"] == result["audio"]["output_adts_frames"]
    assert result["output"]["ts_continuity_errors"] == 0
    assert result["output"]["psi_crc_errors"] == 0
    assert result["output"]["pcr_max_gap_seconds"] <= 0.1
    assert result["output"]["streamio_eof_drain"]


def test_realtime_pacing_wait_is_cancellable():
    network = SimpleNamespace(stop=threading.Event())
    deadline = time.monotonic() + 2
    errors = []

    def wait_for_media_time():
        try:
            _pace_until(network, time.monotonic(), 50_000_000 + 10_000_000, deadline)
        except BaseException as error:
            errors.append(error)

    worker = threading.Thread(target=wait_for_media_time)
    worker.start()
    time.sleep(0.05)
    network.stop.set()
    worker.join(1)
    assert not worker.is_alive()
    assert len(errors) == 1 and isinstance(errors[0], Cancelled)


def test_realtime_pacing_obeys_global_deadline():
    network = SimpleNamespace(stop=threading.Event())
    with pytest.raises(subprocess.TimeoutExpired):
        _pace_until(
            network,
            time.monotonic(),
            50_000_000 + 10_000_000,
            time.monotonic() + 0.01,
        )
