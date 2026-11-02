# SPDX-License-Identifier: AGPL-3.0-only
"""Ongoing-prefix readiness is distinct from final whole-recording validation."""

import struct
import time
import subprocess

import pytest
from streamlink import Streamlink
from streamlink.exceptions import StreamError
from soop_grid.bootstrap import Config
from soop_grid.media import MediaSink, parse_media
from soop_grid.protocol import Frame, GridError, parent_packet
from soop_grid.recovery import Continuity
from soop_grid.startup import receive_startup
from soop_grid.stream import SoopGridReader, SoopGridStream, validate_media_output
from test_startup_retry import legal_startup_media as legal_fixture


@pytest.fixture
def readiness_media(encoded_bframes, tmp_path):
    return legal_fixture.__wrapped__(encoded_bframes, tmp_path)


def delayed_audio_frames(frames):
    audio = [f for f in frames if parse_media(f.body).kind == "A"]
    early = set(id(f) for f in audio[:25])
    prefix = [f for f in frames if parse_media(f.body).kind != "A" or id(f) in early]
    sequence = prefix + audio[25:]
    numbered = []
    for i, f in enumerate(sequence):
        b = bytearray(f.body)
        struct.pack_into("<Q", b, 12, i + 1)
        b = bytes(b)
        numbered.append(Frame(0xC748, b, wire=parent_packet(0xC748, b)))
    return numbered, len(prefix)


def feed(sink, frames):
    for f in frames:
        sink.add(f)


def test_valid_ongoing_prefix_can_be_ready_while_final_endpoint_is_incomplete(readiness_media):
    frames, _, _ = readiness_media
    frames, cut = delayed_audio_frames(frames)
    sink = MediaSink(lambda _: None, synchronize_startup=True)
    feed(sink, frames[:cut])
    sink.update_coverage()
    assert sink.stats["av_track_span_status"] == "incomplete"
    assert sink.update_startup_readiness()
    assert sink.stats["startup_common_span_90k"] >= 45000
    sink.close()
    with pytest.raises(GridError, match="media_track_coverage_incomplete"):
        validate_media_output(sink.stats)


def test_late_audio_catches_up_without_changing_final_validation(readiness_media):
    frames, _, _ = readiness_media
    frames, cut = delayed_audio_frames(frames)
    sink = MediaSink(lambda _: None, synchronize_startup=True)
    feed(sink, frames[:cut])
    assert sink.update_startup_readiness()
    feed(sink, frames[cut:])
    sink.close()
    validate_media_output(sink.stats)
    assert sink.stats["av_track_span_status"] == "consistent"


def test_actual_unexplained_start_boundary_is_still_blocked(readiness_media):
    frames, _, _ = readiness_media
    sink = MediaSink(lambda _: None, synchronize_startup=True)
    shifted = []
    for f in frames:
        b = bytearray(f.body)
        if parse_media(f.body).kind != "A":
            struct.pack_into("<Q", b, 41, struct.unpack_from("<Q", b, 41)[0] + 5450000)
        shifted.append(Frame(0xC748, bytes(b)))
    shifted.sort(key=lambda f: parse_media(f.body).timestamp)
    feed(sink, shifted)
    assert not sink.update_startup_readiness()
    assert sink.stats["startup_video_ready"] == sink.stats["startup_audio_ready"] == 1
    assert sink.stats["startup_start_boundary_valid"] == 0
    sink.close()
    with pytest.raises(GridError, match="media_track_coverage_incomplete"):
        validate_media_output(sink.stats)


def test_counts_alone_cannot_replace_idr_or_aac_configuration():
    sink = MediaSink(lambda _: None, synchronize_startup=True)
    sink.stats.update(
        video_output_frames=20,
        audio_output_access_units=20,
        video_output_first_pts_90k=90000,
        audio_output_first_pts_90k=90000,
        video_output_end_pts_90k=270000,
        audio_output_end_pts_90k=270000,
    )
    assert not sink.update_startup_readiness()
    assert sink.stats["startup_video_ready"] == sink.stats["startup_audio_ready"] == 0
    sink.close()


@pytest.mark.parametrize("audio_catches_up", [True, False])
def test_real_streamio_readiness_and_final_validation_remain_separate(
    readiness_media, tmp_path, audio_catches_up
):
    frames, _, ffmpeg = readiness_media
    frames, cut = delayed_audio_frames(frames)
    chosen = frames if audio_catches_up else frames[:cut]
    baseline = []
    reference = MediaSink(baseline.append, synchronize_startup=True)
    feed(reference, chosen)
    reference.close()
    number = []
    commit_snapshots = []

    def attempt(c, n, emit, report, stats):
        number.append(c)
        sink = MediaSink(emit, synchronize_startup=True)
        stats.update(sink.stats)
        sink.stats = stats
        stats["parent_connections"] = 1
        report("cache_request_sent")
        cont = Continuity(stats, report)
        try:
            for f in chosen:
                cont.accept(parse_media(f.body))
                sink.add(f)
                cont.committed()
                sink.update_coverage()  # Test-only snapshot of the OLD, final gate.
                sink.update_startup_readiness()
                report("parent_last_media_received")
                time.sleep(0.02)
            stats["stop_reason"] = "duration_limit"
        finally:
            sink.close()
            c.clear()
            n.close()
        validate_media_output(stats)

    def runner(c, n, emit, report, stats):
        def event(e):
            if e == "startup_ready":
                commit_snapshots.append(stats.get("av_track_span_status"))
            report(e)

        receive_startup(c, n, emit, event, stats, attempt, window=0.5)

    r = SoopGridReader(SoopGridStream(Streamlink(), Config("test", "12345")), runner=runner)
    output = bytearray()
    error = None
    try:
        r.open()
        while b := r.read(8192):
            output.extend(b)
    except (OSError, StreamError) as e:
        error = e
    finally:
        r.close()
    assert len(number) == 1 and commit_snapshots == ["incomplete"]
    assert bytes(output) == b"".join(baseline)
    assert not r.thread.is_alive() and not r.network._sockets
    if audio_catches_up:
        assert (
            error is None and r.stats["reader_eof_observed"] == r.stats["stream_output_drain_complete"] == 1
        )
        assert (
            r.stats["stream_emit_bytes"]
            == r.buffer.accepted_bytes
            == r.stats["stream_reader_bytes"]
            == len(output)
        )
        ts = tmp_path / "legal-delayed-audio.ts"
        ts.write_bytes(output)
        subprocess.run(
            [ffmpeg, "-v", "error", "-xerror", "-err_detect", "explode", "-i", str(ts), "-f", "null", "-"],
            check=True,
            capture_output=True,
        )
    else:
        assert error is not None and r.failure_code == "media_track_coverage_incomplete"
        assert r.stats["stream_output_drain_complete"] == 0


@pytest.mark.parametrize(
    "code,expected",
    [
        ("media_track_coverage_incomplete", "media_track_coverage_incomplete"),
        ("gateway_login_denied", "gateway_login_denied"),
        ("receiver_closed", "startup_timeout"),
    ],
)
def test_real_failure_is_not_hidden_by_concurrent_watchdog(code, expected):
    from soop_grid.protocol import Network

    stats = {}

    def attempt(c, n, emit, report, local):
        time.sleep(0.02)
        raise GridError(code)

    with pytest.raises(GridError, match=expected):
        receive_startup(
            Config("test", "12345"),
            Network(),
            lambda _: pytest.fail("published"),
            lambda _: None,
            stats,
            attempt,
            total_timeout=0.001,
        )
    assert stats["startup_attempts"] == 1 and stats["startup_deadline_reached"] == 1
