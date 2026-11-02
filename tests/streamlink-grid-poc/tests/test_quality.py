# SPDX-License-Identifier: AGPL-3.0-only
"""Evidence-gated Native Grid quality enumeration and resolution checks."""

import os
import shutil
import subprocess

import pytest

from soop_grid.bootstrap import Config
from soop_grid.protocol import GridError
from soop_grid.quality import profile_by_name, profiles_from_viewpreset


VIEWPRESET = [
    {"label": "360p", "name": "sd"},
    {"label": "540p", "name": "hd"},
    {"label": "720p", "name": "hd4k"},
    {"label": "1080p", "name": "hd8k"},
    {"label": "1440p", "name": "original"},
    {"label": "auto", "name": "auto"},
]


def encode_profile_idr(tmp_path, width, height):
    """Generate one real, independently configured IDR at a supported height."""
    ffmpeg = os.environ.get("SOOP_TEST_FFMPEG") or shutil.which("ffmpeg")
    if not ffmpeg:
        pytest.skip("FFmpeg required to generate resolution-verification H.264 fixtures")
    path = tmp_path / f"profile-{width}x{height}.h264"
    result = subprocess.run(
        [
            ffmpeg,
            "-v",
            "error",
            "-nostdin",
            "-f",
            "lavfi",
            "-i",
            f"testsrc2=size={width}x{height}:rate=30",
            "-frames:v",
            "1",
            "-an",
            "-c:v",
            "libx264",
            "-preset",
            "ultrafast",
            "-b:v",
            "800k",
            "-minrate",
            "800k",
            "-maxrate",
            "800k",
            "-bufsize",
            "1600k",
            "-x264-params",
            "bframes=0:keyint=1:min-keyint=1:scenecut=0:aud=1:repeat-headers=1:force-cfr=1:nal-hrd=cbr",
            "-f",
            "h264",
            str(path),
        ],
        capture_output=True,
        timeout=30,
    )
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")
    return path.read_bytes()


def test_measured_native_grid_profiles_require_exact_live_preset_evidence():
    profiles = profiles_from_viewpreset(VIEWPRESET)
    assert [(p.name, p.allocation_quality, p.expected_height) for p in profiles] == [
        ("original", 1, 1440),
        ("720p", 2, 720),
        ("540p", 4, 540),
        ("360p", 8, 360),
    ]
    assert [p.hls_label for p in profiles] == ["1440p", "720p", "540p", "360p"]
    assert (profiles[-1].join_quality, profiles[-1].join_is_auto) == ("low", True)


def test_1080_original_exposes_only_measured_lower_grid_profiles():
    profiles = profiles_from_viewpreset(
        [
            {"label": "360p", "name": "sd"},
            {"label": "540p", "name": "hd"},
            {"label": "720p", "name": "hd4k"},
            {"label": "1080p", "name": "original"},
        ]
    )
    assert [(p.name, p.expected_height) for p in profiles] == [
        ("original", 1080),
        ("720p", 720),
        ("540p", 540),
        ("360p", 360),
    ]


def test_2160_original_does_not_invent_unmeasured_1080_grid_profile():
    profiles = profiles_from_viewpreset(
        [
            {"label": "1080p", "name": "hd8k"},
            {"label": "2160p", "name": "original"},
        ]
    )
    assert [(p.name, p.expected_height) for p in profiles] == [("original", 2160)]


@pytest.mark.parametrize(
    "viewpreset",
    [
        None,
        [],
        [{"label": "720p", "name": "unknown"}, {"label": "540p", "name": "unknown"}],
        [{"label": "1080p", "name": "hd8k"}],
    ],
)
def test_unverified_or_unavailable_modes_are_not_exposed(viewpreset):
    profiles = profiles_from_viewpreset(viewpreset)
    assert [p.name for p in profiles] == ["original"]


def test_single_measured_downscale_is_exposed_without_other_presets():
    profiles = profiles_from_viewpreset([{"label": "720p", "name": "hd4k"}])
    assert [(p.name, p.expected_height) for p in profiles] == [("original", None), ("720p", 720)]


def test_ambiguous_original_preset_does_not_enable_downscales():
    profiles = profiles_from_viewpreset(
        [
            {"label": "1080p", "name": "original"},
            {"label": "1440p", "name": "original"},
            {"label": "720p", "name": "hd4k"},
            {"label": "540p", "name": "hd"},
        ]
    )
    assert [(p.name, p.expected_height, p.original_label) for p in profiles] == [("original", None, None)]


def test_grid_lower_profile_is_not_duplicated_when_it_matches_original_resolution():
    profiles = profiles_from_viewpreset(
        [{"label": "720p", "name": "original"}, {"label": "720p", "name": "hd4k"}]
    )
    assert [(p.name, p.allocation_quality, p.expected_height) for p in profiles] == [("original", 1, 720)]


@pytest.mark.parametrize("name", ["original", "720p", "540p", "360p"])
def test_grid_profile_configuration_preserves_verified_request(name):
    profile = profile_by_name(name, original_height=1080 if name == "original" else None)
    config = Config(
        "fixture_channel",
        "12345",
        grid_quality=name,
        expected_grid_height=profile.expected_height,
    )
    config.validate()
    assert config.grid_quality == name


def test_2160_source_exposes_measured_360p_but_not_unverified_1080p():
    profiles = profiles_from_viewpreset(
        [
            {"label": "2160p", "name": "original"},
            {"label": "1080p", "name": "hd8k"},
            {"label": "360p", "name": "sd"},
        ]
    )
    assert [(p.name, p.expected_height) for p in profiles] == [("original", 2160), ("360p", 360)]


@pytest.mark.parametrize(("name", "height"), [("720p", None), ("720p", 540), ("540p", 720), ("original", 0)])
def test_grid_profile_configuration_rejects_unknown_height_contract(name, height):
    with pytest.raises(GridError):
        Config("fixture_channel", "12345", grid_quality=name, expected_grid_height=height).validate()


def test_unknown_grid_profile_is_rejected():
    with pytest.raises(GridError, match="grid_quality_unsupported"):
        profile_by_name("1080p")


def test_metadata_failure_keeps_only_legacy_original():
    import soop_grid.stream as stream_module

    class Plugins:
        def load_builtin(self):
            return True

        def get_loaded(self):
            return {"soop": Builtin}

    class Http:
        headers = {}

        class Cookies:
            @staticmethod
            def get_dict(**_kwargs):
                return {}

        cookies = Cookies()

    class Session:
        plugins = Plugins()
        http = Http()

    class Builtin:
        CHANNEL_RESULT_OK = 1

        def __init__(self, *_args, **_kwargs):
            self.session = Session()

        def _get_channel_info(self, *_args):
            raise OSError("fixture metadata unavailable")

        def set_option(self, *_args):
            pass

    assert [
        p.name
        for p in stream_module.official_grid_profiles(
            Session(), "https://play.sooplive.com/channel/12345", "channel", "12345"
        )
    ] == ["original"]


def test_optional_quality_metadata_never_starts_a_new_login():
    import soop_grid.stream as stream_module

    class Http:
        headers = {}

    class Session:
        http = Http()
        plugins = None

    class Builtin:
        CHANNEL_RESULT_OK = 1

        def __init__(self, *_args, **_kwargs):
            self.session = Session()

        def _get_channel_info(self, channel, bno):
            assert (channel, bno) == ("channel", "12345")
            return 1, "12345", "author", "title", "rmd", "cdn", "", VIEWPRESET

        def _login(self, *_args):
            raise AssertionError("optional profile discovery must not initiate login")

        def set_option(self, *_args):
            pass

    class Plugins:
        def load_builtin(self):
            pass

        def get_loaded(self):
            return {"soop": Builtin}

    Session.plugins = Plugins()
    profiles = stream_module.official_grid_profiles(
        Session(), "https://play.sooplive.com/channel/12345", "channel", "12345"
    )
    assert [profile.name for profile in profiles] == ["original", "720p", "540p", "360p"]


def test_media_sink_rejects_wrong_sps_before_emitting_ts(encoded_bframes):
    from conftest import media_body
    from soop_grid.media import MediaSink
    from soop_grid.protocol import Frame

    payload = next(payload for payload, kind in encoded_bframes if kind == "I")
    emitted = []
    sink = MediaSink(lambda data: emitted.append(data), expected_grid_height=720, grid_quality_code=2)
    frame = Frame(0xC748, media_body(payload, "I", 1, 50000000))
    with pytest.raises(GridError) as caught:
        sink.add(frame)
    assert str(caught.value) == "grid_quality_resolution_mismatch"
    assert caught.value.safe_facts == {
        "grid_quality_code": 2,
        "expected_grid_height": 720,
        "received_grid_height": 96,
    }
    assert emitted == []
    assert sink.stats.get("mux_output_bytes", 0) == sink.stats.get("stream_emit_bytes", 0) == 0
    sink.close()


@pytest.mark.parametrize(("quality", "width", "height"), [(1, 1280, 720), (8, 640, 360)])
def test_media_sink_confirms_expected_resolution_from_sps(tmp_path, quality, width, height):
    from conftest import media_body
    from soop_grid.media import MediaSink, sps_info
    from soop_grid.mpegts import nals
    from soop_grid.protocol import Frame

    payload = encode_profile_idr(tmp_path, width, height)
    assert sps_info(payload)["height"] == height
    assert {7, 8, 5}.issubset({nal[0] & 31 for nal in nals(payload)})
    sink = MediaSink(lambda _data: None, expected_grid_height=height, grid_quality_code=quality)
    sink.add(Frame(0xC748, media_body(payload, "I", 1, 50000000)))
    assert sink.stats["received_grid_height"] == height
    assert sink.stats["grid_quality_code"] == quality
    assert sink.stats["grid_quality_verified"] == 1
    sink.close()


def test_media_sink_rejects_expected_height_below_supported_floor():
    from soop_grid.media import MediaSink

    with pytest.raises(GridError, match="grid_quality_metadata_invalid"):
        MediaSink(lambda _data: None, expected_grid_height=96, grid_quality_code=1)


def test_media_sink_rejects_wrong_supported_sps_before_emitting_ts(tmp_path):
    from conftest import media_body
    from soop_grid.media import MediaSink, sps_info
    from soop_grid.protocol import Frame

    payload = encode_profile_idr(tmp_path, 640, 360)
    assert sps_info(payload)["height"] == 360
    emitted = []
    sink = MediaSink(emitted.append, expected_grid_height=720, grid_quality_code=2)
    with pytest.raises(GridError, match="grid_quality_resolution_mismatch") as caught:
        sink.add(Frame(0xC748, media_body(payload, "I", 1, 50000000)))
    assert caught.value.safe_facts == {
        "grid_quality_code": 2,
        "expected_grid_height": 720,
        "received_grid_height": 360,
    }
    assert emitted == []
    assert sink.stats.get("mux_output_bytes", 0) == sink.stats.get("stream_emit_bytes", 0) == 0
    sink.close()


def test_streamio_quality_mismatch_ends_without_publication(encoded_bframes):
    from conftest import media_body
    from streamlink import Streamlink
    from streamlink.exceptions import StreamError
    from soop_grid.media import MediaSink
    from soop_grid.protocol import Frame, GridError
    from soop_grid.stream import SoopGridReader, SoopGridStream

    payload = next(payload for payload, kind in encoded_bframes if kind == "I")
    frame = Frame(0xC748, media_body(payload, "I", 1, 50000000))

    def runner(config, network, emit, _report, stats):
        sink = MediaSink(emit, expected_grid_height=720, grid_quality_code=2)
        stats.update(sink.stats)
        sink.stats = stats
        try:
            sink.add(frame)
        except GridError:
            raise
        finally:
            sink.close()

    reader = SoopGridReader(SoopGridStream(Streamlink(), Config("fixture_channel", "12345")), runner)
    with pytest.raises(StreamError, match="grid_quality_resolution_mismatch"):
        reader.open()
    assert reader.buffer.accepted_bytes == 0
    assert reader.stats["grid_quality_verified"] == 0
    assert not reader.thread.is_alive()
    assert not reader.network._sockets
