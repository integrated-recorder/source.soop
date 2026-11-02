# SPDX-License-Identifier: AGPL-3.0-only
import threading
import pytest
from streamlink import Streamlink
from streamlink.exceptions import StreamError
from soop_grid.bootstrap import Config
from soop_grid.protocol import GridError
from soop_grid.stream import SoopGridReader, SoopGridStream
from soop_grid.startup import receive_startup

PACKET = b"\x47" + b"x" * 187


def setup(
    failures=0, code="frame_sequence_gap_or_reset", post=False, capacity=32 << 20, ready=True, callback=None
):
    calls = []
    configs = []

    def attempt(c, n, emit, report, stats):
        calls.append(n)
        configs.append(c)
        assert c.account == "test" and c.account_password == "secret"
        try:
            stats.update(parent_connections=1, parent_wire_bytes=100)
            report("cache_request_sent")
            emit(PACKET)
            if len(calls) <= failures:
                raise GridError(code)
            if ready:
                stats.update(
                    av_track_span_status="consistent",
                    startup_av_ready=1,
                    video_output_frames=1,
                    audio_output_access_units=1,
                    video_output_first_pts_90k=90000,
                    audio_output_first_pts_90k=90000,
                    video_output_end_pts_90k=450000,
                    audio_output_end_pts_90k=450000,
                )
            report("parent_last_media_received")
            emit(PACKET)
            if post:
                raise GridError("frame_sequence_gap_or_reset")
            stats["stop_reason"] = "duration_limit"
        finally:
            # Adversarial representation of MediaSink.close() emitting held output.
            emit(PACKET)
            c.clear()
            n.close()

    def runner(c, n, emit, report, stats):
        def observed(e):
            if callback:
                callback(e)
            report(e)

        receive_startup(c, n, emit, observed, stats, attempt, retries=2, window=0, capacity=capacity)

    config = Config("test", "12345", account="test", account_password="secret")
    stream = SoopGridStream(Streamlink(), config)
    stream.timeout = 2
    stream.buffer_size = 376
    reader = SoopGridReader(stream, runner=runner)
    return reader, calls, configs


@pytest.mark.parametrize("failures", [0, 1, 2])
def test_real_reader_retries_and_natural_eof(failures):
    r, calls, configs = setup(failures)
    r.open()
    data = bytearray()
    while True:
        b = r.read(188)
        if not b:
            break
        data.extend(b)
    r.close()
    assert bytes(data) == PACKET * 3
    assert len(calls) == failures + 1 and len(set(map(id, calls))) == len(calls)
    assert all(not c.account and not c.account_password for c in configs)
    assert not r.stream.config.account
    assert r.stats["startup_aborted_bytes"] == failures * len(PACKET) * 2
    assert r.stats["startup_commit_attempt"] == failures + 1
    assert (
        r.stats["stream_emit_bytes"] == r.stats["stream_reader_bytes"] == r.buffer.accepted_bytes == len(data)
    )
    assert r.stats["reader_eof_observed"] == r.stats["stream_output_drain_complete"] == 1
    assert not r.thread.is_alive() and not r.network._sockets and not r.buffer.data


@pytest.mark.parametrize(
    "code",
    [
        "frame_identity_conflict",
        "frame_timestamp_regression",
        "media_layout_unconfirmed",
        "gateway_login_denied",
        "h264_poc_type_unsupported",
    ],
)
def test_nonretryable_errors_do_not_publish(code):
    r, calls, configs = setup(3, code)
    with pytest.raises(StreamError):
        r.open()
    assert len(calls) == 1 and r.buffer.accepted_bytes == 0
    assert not r.thread.is_alive() and not r.stream.config.account


def test_all_attempts_fail_with_zero_publication():
    r, calls, _ = setup(3)
    with pytest.raises(StreamError):
        r.open()
    assert len(calls) == 3 and r.failure_code == "frame_sequence_gap_or_reset"
    assert r.buffer.accepted_bytes == 0 and not r.thread.is_alive()


def test_postcommit_gap_never_retries():
    r, calls, _ = setup(post=True)
    data = bytearray()
    try:
        r.open()
        while b := r.read(188):
            data.extend(b)
    except Exception:
        pass
    finally:
        r.close()
    assert len(calls) == 1 and r.failure_code == "frame_sequence_gap_or_reset"
    assert r.stats["startup_commit_attempt"] == 1


def test_capacity_failure_and_unready_av_cannot_publish():
    for kwargs in ({"capacity": 100}, {"ready": False}):
        r, calls, _ = setup(**kwargs)
        with pytest.raises(StreamError):
            r.open()
        assert len(calls) == 1 and r.buffer.accepted_bytes == 0


def test_cancel_at_ready_has_no_leak_or_deadlock():
    waiting = threading.Event()
    resume = threading.Event()
    errors = []

    def callback(e):
        if e == "startup_ready":
            waiting.set()
            resume.wait(2)

    r, calls, _ = setup(callback=callback)

    def open_reader():
        try:
            r.open()
        except BaseException as e:
            errors.append(type(e).__name__)

    t = threading.Thread(target=open_reader)
    t.start()
    assert waiting.wait(2)
    closing = threading.Thread(target=r.close)
    closing.start()
    assert r.network.stop.wait(1)
    resume.set()
    closing.join(3)
    t.join(3)
    assert not closing.is_alive() and not t.is_alive() and not r.thread.is_alive()
    assert r.buffer.accepted_bytes == 0 and len(calls) == 1


@pytest.mark.parametrize(
    "field,value",
    [
        ("startup_retries", -1),
        ("startup_retries", 3),
        ("startup_retries", True),
        ("startup_window", 0),
        ("startup_window", float("nan")),
        ("startup_memory", 33 << 20),
        ("startup_timeout", float("inf")),
    ],
)
def test_startup_option_bounds(field, value):
    c = Config("test", "12345")
    setattr(c, field, value)
    with pytest.raises(GridError, match="startup_configuration_invalid"):
        c.validate()


def test_retry_capture_is_explicitly_rejected():
    c = Config("test", "12345", startup_retries=1, capture_dir="private")
    with pytest.raises(GridError, match="startup_capture_unsupported"):
        c.validate()


@pytest.fixture
def legal_startup_media(encoded_bframes, tmp_path):
    import os
    import shutil
    import subprocess
    from conftest import media_body
    from soop_grid.media import MediaSink
    from soop_grid.protocol import Frame
    from soop_grid.stream import validate_media_output

    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg required for independently decoded legal startup fixture")
    audio = tmp_path / "own-fixture.aac"
    subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-f",
            "lavfi",
            "-i",
            "anullsrc=r=48000:cl=stereo",
            "-t",
            "1",
            "-c:a",
            "aac",
            "-f",
            "adts",
            str(audio),
        ],
        check=True,
        capture_output=True,
    )
    samples = [(i * 333333, payload, kind) for i, (payload, kind) in enumerate(encoded_bframes)]
    raw = audio.read_bytes()
    offset = index = 0
    while offset < len(raw):
        size = ((raw[offset + 3] & 3) << 11) | (raw[offset + 4] << 3) | (raw[offset + 5] >> 5)
        samples.append(
            (2 * 10000000 // 30 + index * 1024 * 10000000 // 48000, raw[offset : offset + size], "A")
        )
        index += 1
        offset += size
    samples.sort(key=lambda x: x[0])
    frames = [Frame(0xC748, media_body(p, k, i + 1, 50000000 + t)) for i, (t, p, k) in enumerate(samples)]
    baseline = []
    sink = MediaSink(baseline.append, synchronize_startup=True)
    for f in frames:
        sink.add(f)
    sink.close()
    validate_media_output(sink.stats)
    return frames, b"".join(baseline), ffmpeg


def test_actual_generated_media_reader_retry_matches_baseline_and_decodes(legal_startup_media, tmp_path):
    import subprocess
    import time
    from soop_grid.media import MediaSink, parse_media
    from soop_grid.recovery import Continuity
    from soop_grid.stream import validate_media_output

    frames, baseline, ffmpeg = legal_startup_media
    attempts = []

    def attempt(config, network, emit, report, stats):
        attempts.append(network)
        local_sink = MediaSink(emit, synchronize_startup=True)
        stats.update(local_sink.stats)
        local_sink.stats = stats
        stats["parent_connections"] = 1
        cont = Continuity(stats, report)
        report("cache_request_sent")
        try:
            for i, f in enumerate(frames):
                if len(attempts) == 1 and i == 5:
                    raise GridError("frame_sequence_gap_or_reset")
                cont.accept(parse_media(f.body))
                local_sink.add(f)
                local_sink.update_startup_readiness()
                report("parent_last_media_received")
                cont.committed()
                time.sleep(0.015)
            stats["stop_reason"] = "duration_limit"
        finally:
            local_sink.close()
            config.clear()
            network.close()
        validate_media_output(stats)

    def runner(config, network, emit, report, stats):
        receive_startup(config, network, emit, report, stats, attempt, retries=2, window=0.5)

    r = SoopGridReader(SoopGridStream(Streamlink(), Config("test", "12345")), runner=runner).open()
    output = bytearray()
    while b := r.read(8192):
        output.extend(b)
    r.close()
    assert len(attempts) == 2
    assert bytes(output) == baseline
    assert len(output) % 188 == 0
    assert r.stats["startup_commit_attempt"] == 2 and r.stats["startup_aborted_bytes"] > 0
    assert r.stats["reader_eof_observed"] == r.stats["stream_output_drain_complete"] == 1
    assert r.buffer.accepted_bytes == r.stats["stream_reader_bytes"] == len(output)
    ts = tmp_path / "legal-retried.ts"
    ts.write_bytes(output)
    subprocess.run(
        [ffmpeg, "-v", "error", "-xerror", "-err_detect", "explode", "-i", str(ts), "-f", "null", "-"],
        check=True,
        capture_output=True,
    )


@pytest.mark.parametrize("phase", ["live_push_transition_requested", "parent_failover_started"])
def test_preoutput_gap_outside_initial_cache_is_not_retried(phase):
    calls = []

    def attempt(c, n, emit, report, stats):
        calls.append(c)
        stats["parent_connections"] = 1
        report("cache_request_sent")
        report(phase)
        emit(PACKET)
        raise GridError("frame_sequence_gap_or_reset")

    from soop_grid.protocol import Network

    config = Config("test", "12345")
    with pytest.raises(GridError, match="frame_sequence_gap_or_reset"):
        receive_startup(
            config,
            Network(),
            lambda _: pytest.fail("published"),
            lambda _: None,
            {},
            attempt,
            retries=2,
            window=0.5,
        )
    assert len(calls) == 1


def test_total_byte_budget_does_not_reset_on_retry():
    r, calls, configs = setup(3)
    r.stream.config.max_bytes = 200
    with pytest.raises(StreamError):
        r.open()
    assert len(calls) == 2
    assert [c.max_bytes for c in configs] == [200, 100]
    assert r.failure_code == "startup_byte_limit" and r.buffer.accepted_bytes == 0


def test_watchdog_and_credentials_clear_on_blocked_startup():
    import time
    from soop_grid.protocol import Network

    config = Config("test", "12345", account="test", account_password="secret")
    calls = []

    def attempt(c, n, emit, report, stats):
        calls.append(c)
        stats["parent_connections"] = 1
        report("cache_request_sent")
        time.sleep(0.03)
        raise GridError("frame_sequence_gap_or_reset")

    with pytest.raises(GridError, match="frame_sequence_gap_or_reset"):
        receive_startup(
            config,
            Network(),
            lambda _: pytest.fail("published"),
            lambda _: None,
            {},
            attempt,
            retries=2,
            window=0.5,
            total_timeout=0.01,
        )
    assert len(calls) == 1 and not calls[0].account and not config.account


@pytest.mark.parametrize("missing", ["video_output_frames", "audio_output_access_units"])
def test_uninitialized_single_track_cannot_commit(missing):
    from soop_grid.protocol import Network

    def attempt(c, n, emit, report, stats):
        stats.update(
            parent_connections=1,
            av_track_span_status="consistent",
            startup_av_ready=1,
            video_output_frames=1,
            audio_output_access_units=1,
            video_output_first_pts_90k=90000,
            audio_output_first_pts_90k=90000,
            video_output_end_pts_90k=450000,
            audio_output_end_pts_90k=450000,
        )
        stats[missing] = 0
        report("cache_request_sent")
        emit(PACKET)
        report("parent_last_media_received")

    with pytest.raises(GridError, match="startup_unverified"):
        receive_startup(
            Config("test", "12345"),
            Network(),
            lambda _: pytest.fail("published"),
            lambda _: None,
            {},
            attempt,
            window=0,
        )


def test_aborted_attempt_statistics_do_not_leak_into_successful_attempt():
    from soop_grid.protocol import Network

    stats = {}
    number = 0

    def attempt(c, n, emit, report, local):
        nonlocal number
        number += 1
        local.update(parent_connections=1, parent_wire_bytes=100, bootstrap_bno=12345)
        report("cache_request_sent")
        if number == 1:
            local["recovery_failure_code"] = "frame_sequence_gap_or_reset"
            raise GridError("frame_sequence_gap_or_reset")
        assert c.bno == "12345"
        local.update(
            av_track_span_status="consistent",
            startup_av_ready=1,
            video_output_frames=1,
            audio_output_access_units=1,
            video_output_first_pts_90k=90000,
            audio_output_first_pts_90k=90000,
            video_output_end_pts_90k=450000,
            audio_output_end_pts_90k=450000,
        )
        emit(PACKET)
        report("parent_last_media_received")

    receive_startup(Config("test"), Network(), lambda _: None, lambda _: None, stats, attempt, window=0)
    assert "recovery_failure_code" not in stats and stats["startup_commit_attempt"] == 2


def test_real_reader_parent_overlap_during_committed_startup(monkeypatch, legal_startup_media):
    from types import SimpleNamespace
    from test_recovery import SyntheticNetwork, controls
    from soop_grid.media import MediaSink
    from soop_grid.parent import Parent, receive_media
    from soop_grid.protocol import parent_packet
    from soop_grid.stream import validate_media_output
    import soop_grid.parent as parent_module

    frames, baseline, _ = legal_startup_media
    clock = [0]
    monkeypatch.setattr(parent_module, "time", SimpleNamespace(monotonic=lambda: clock[0]))
    wires = [parent_packet(0xC748, f.body) for f in frames]
    peers = []
    calls = []

    def attempt(config, network, emit, report, stats):
        calls.append(config)
        fake_network = SyntheticNetwork(
            [(controls() + b"".join(wires[:20]), "reset"), (controls() + b"".join(wires[17:]), "deadline")],
            clock,
        )
        peers.append(fake_network)
        sink = MediaSink(emit, synchronize_startup=True)
        stats.update(sink.stats)
        sink.stats = stats

        def progress(e):
            if e == "parent_last_media_received":
                sink.update_startup_readiness()
            report(e)

        try:
            receive_media(
                fake_network,
                [Parent(("8.8.8.8", 10000), 1, 0), Parent(("8.8.4.4", 10000), 1, 0)],
                12345,
                42,
                sink,
                progress,
                duration=35,
            )
        finally:
            sink.close()
        validate_media_output(stats)

    def runner(c, n, emit, report, stats):
        receive_startup(c, n, emit, report, stats, attempt, window=0)

    r = SoopGridReader(SoopGridStream(Streamlink(), Config("test", "12345")), runner=runner).open()
    out = bytearray()
    while b := r.read(8192):
        out.extend(b)
    r.close()
    assert bytes(out) == baseline and len(calls) == 1
    assert r.stats["failover_successes"] == 1 and r.stats["duplicate_frames_excluded"] == 3
    assert r.stats["startup_retries"] == 0 and r.stats["reader_eof_observed"] == 1
    assert r.stats["stream_output_drain_complete"] == 1
    assert all(s.closed for network in peers for s in network.sockets)


def test_close_during_partial_commit_is_bounded_and_accounted():
    from soop_grid.protocol import Cancelled

    calls = []

    def attempt(c, n, emit, report, stats):
        calls.append(c)
        stats.update(
            parent_connections=1,
            av_track_span_status="consistent",
            startup_av_ready=1,
            video_output_frames=1,
            audio_output_access_units=1,
            video_output_first_pts_90k=90000,
            audio_output_first_pts_90k=90000,
            video_output_end_pts_90k=450000,
            audio_output_end_pts_90k=450000,
        )
        report("cache_request_sent")
        emit(PACKET * 1000)
        try:
            report("parent_last_media_received")
        except (Cancelled, GridError):
            raise

    def runner(c, n, emit, report, stats):
        receive_startup(c, n, emit, report, stats, attempt, window=0)

    stream = SoopGridStream(Streamlink(), Config("test", "12345"))
    stream.buffer_size = 376
    r = SoopGridReader(stream, runner=runner).open()
    consumed = len(r.read(188))
    r.close()
    assert len(calls) == 1 and not r.thread.is_alive() and not r.network._sockets
    assert r.buffer.accepted_bytes == consumed + r.buffer.discarded_bytes
    assert r.buffer.unaccepted_bytes > 0 and r.stats["stream_output_drain_complete"] == 0


@pytest.mark.parametrize("transport", ["grid", "auto"])
def test_actual_plugin_optin_configuration(transport):
    from pathlib import Path

    session = Streamlink()
    session.plugins.load_path(str(Path(__file__).resolve().parents[1] / "plugins"))
    url = "https://play.sooplive.com/fixture_channel/12345"
    cls = session.resolve_url(url)[1]
    stream = cls(
        session, url, options={"transport": transport, "grid-startup-retries": 2, "grid-startup-window": 4.0}
    ).streams()["original"]
    cfg = stream.grid.config if transport == "auto" else stream.config
    assert cfg.startup_retries == 2 and cfg.startup_window == 4


@pytest.mark.parametrize(
    "code", ["startup_timeout", "startup_staging_limit", "startup_unverified", "frame_sequence_gap_or_reset"]
)
def test_auto_does_not_hide_startup_failure_with_hls(code):
    from test_transport import FakeStream
    from soop_grid.stream import SoopAutoStream

    error = StreamError("fixed stage error")
    error.grid_error_code = code
    grid = FakeStream(error=error)
    hls = FakeStream(result="must-not-open")
    with pytest.raises(StreamError):
        SoopAutoStream(Streamlink(), grid, hls).open()
    assert grid.opened == 1 and hls.opened == 0 and hls.cleared
