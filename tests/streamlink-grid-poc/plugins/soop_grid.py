# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""
$description Experimental native TCP Grid receiver for authorized SOOP live streams.
$url play.sooplive.com
$url play.sooplive.co.kr
$url play.afreecatv.com
$type live
"""

import os
import re
import logging

from streamlink.exceptions import PluginError
from streamlink.plugin import Plugin, pluginargument, pluginmatcher
from streamlink.plugin.plugin import stream_sorting_filter

from soop_grid.bootstrap import Config
from soop_grid.protocol import GridError
from soop_grid.stream import (
    OfficialHLSFallback,
    SoopAutoStream,
    SoopGridStream,
    official_grid_profiles,
    official_hls_plugin,
)


log = logging.getLogger("streamlink.plugins.soop_grid")

# Streamlink ranks quality aliases by their names. Keep the Grid source at a
# rank above every supported resolution alias, then remove this private alias
# from the user-visible mapping after Plugin.streams() has built best/worst.
_GRID_ORIGINAL_RANK_ALIAS = "9999p"


def official_hls_streams(session, url, account, password, stream_password, purge_credentials=False):
    # Keep HLS behavior in Streamlink's maintained SOOP plugin. This sideloaded
    # plugin uses a separate ID and priority, so the built-in `soop` remains
    # loaded and is delegated to through the public plugin/session APIs.
    plugin = official_hls_plugin(
        session,
        url,
        account,
        password,
        stream_password,
        purge_credentials,
    )
    return plugin.streams()


@pluginmatcher(
    re.compile(
        r"https?://play\.(?:sooplive\.com|sooplive\.co\.kr|afreecatv\.com)/(?P<channel>[A-Za-z0-9_-]+)(?:/(?P<bno>\d+))?/?(?:[?#].*)?$"
    ),
    priority=30,
)
@pluginargument(
    "transport",
    choices=("auto", "grid", "hls"),
    default="auto",
    argument_name="soop-grid-transport",
    help="Transport: Grid, official SOOP HLS, or Grid-first with initial HLS fallback.",
)
@pluginargument(
    "grid-startup-retries",
    type=int,
    default=0,
    argument_name="soop-grid-startup-retries",
    help="Opt-in full startup session retries (0..2); no retries after first output.",
)
@pluginargument(
    "grid-startup-window",
    type=float,
    default=2.0,
    argument_name="soop-grid-startup-window",
    help="Startup validation window in seconds (0.5..8), with retries enabled.",
)
@pluginargument(
    "grid-account",
    sensitive=True,
    argument_name="soop-grid-account",
    help="Legacy alias for --soop-grid-username.",
)
@pluginargument(
    "grid-username",
    sensitive=True,
    argument_name="soop-grid-username",
    help="SOOP account ID for Native Grid and HLS fallback.",
)
@pluginargument(
    "grid-password",
    sensitive=True,
    argument_name="soop-grid-password",
    help="SOOP account password for Native Grid and HLS fallback.",
)
@pluginargument(
    "grid-require-adult",
    action="store_true",
    argument_name="soop-grid-require-adult",
    help="Require the authenticated live API adult check.",
)
@pluginargument(
    "grid-duration",
    type=int,
    argument_name="soop-grid-duration",
    help="Optional Grid capture limit in seconds; omit to record until stopped.",
)
@pluginargument(
    "grid-max-bytes",
    type=int,
    argument_name="soop-grid-max-bytes",
    help="Optional maximum Grid wire bytes; omit for no lifetime byte cap.",
)
@pluginargument(
    "grid-diagnostics",
    argument_name="soop-grid-diagnostics",
    help="Create a new private directory for redacted diagnostics and atomic summary.",
)
@pluginargument(
    "grid-stream-password",
    sensitive=True,
    argument_name="soop-grid-stream-password",
    help="Broadcast password for Native Grid and HLS fallback.",
)
@pluginargument(
    "grid-purge-credentials",
    action="store_true",
    argument_name="soop-grid-purge-credentials",
    help="Ask the built-in SOOP plugin to purge its saved credentials in HLS mode.",
)
class SoopGridPlugin(Plugin):
    @staticmethod
    def _credential_value(option_value, primary_env, compatibility_env=None):
        """Resolve an explicit plugin option before the canonical and legacy env vars."""
        if option_value is not None:
            return option_value
        if primary_env in os.environ:
            return os.environ[primary_env]
        if compatibility_env and compatibility_env in os.environ:
            return os.environ[compatibility_env]
        return ""

    def streams(self, stream_types=None, sorting_excludes=None):
        self._grid_original_sort_name = None
        effective_sorting_excludes = sorting_excludes
        if isinstance(sorting_excludes, list):
            # The hidden rank alias must inherit the public original profile's
            # weight for filters; its synthetic 9999p weight would bypass names
            # and invert range filters. Unknown height maps to unweighted original.
            filters = tuple(stream_sorting_filter(expr, self.stream_weight) for expr in sorting_excludes)

            def filter_grid_quality(name):
                candidates = (
                    (self._grid_original_sort_name or "original",)
                    if name == _GRID_ORIGINAL_RANK_ALIAS
                    else (name,)
                )
                return all(filter_func(candidate) for candidate in candidates for filter_func in filters)

            effective_sorting_excludes = filter_grid_quality
        elif callable(sorting_excludes):

            def filter_grid_quality(name):
                if name == _GRID_ORIGINAL_RANK_ALIAS:
                    name = self._grid_original_sort_name or "original"
                return sorting_excludes(name)

            effective_sorting_excludes = filter_grid_quality

        streams = super().streams(stream_types, effective_sorting_excludes)
        if (self.get_option("transport") or "auto") == "hls":
            return streams

        # The synthetic ranking alias points at the exact original Grid stream.
        # Streamlink has already applied stream_types/sorting_excludes and built
        # its synonyms, so removing the private name preserves its normal API.
        original = streams.pop(_GRID_ORIGINAL_RANK_ALIAS, None)
        if original is not None:
            streams["original"] = original
        return streams

    def _get_streams(self):
        transport = self.get_option("transport") or "auto"
        account_option = self.get_option("grid-username")
        legacy_account_option = self.get_option("grid-account")
        if account_option is not None and legacy_account_option is not None:
            raise PluginError("Specify only one of --soop-grid-username and --soop-grid-account")
        account = self._credential_value(
            account_option if account_option is not None else legacy_account_option,
            "SOOP_GRID_USERNAME",
            "SOOP_ACCOUNT_ID",
        )
        account_password = self._credential_value(
            self.get_option("grid-password"), "SOOP_GRID_PASSWORD", "SOOP_ACCOUNT_PASSWORD"
        )
        stream_password = self._credential_value(
            self.get_option("grid-stream-password"),
            "SOOP_GRID_STREAM_PASSWORD",
            "SOOP_STREAM_PASSWORD",
        )
        purge_credentials = bool(self.get_option("grid-purge-credentials"))
        if bool(account) != bool(account_password):
            raise PluginError("account_credentials_required")
        if transport == "hls":
            try:
                hls_streams = official_hls_streams(
                    self.session,
                    self.url,
                    account,
                    account_password,
                    stream_password,
                    purge_credentials,
                )
            except Exception:
                raise PluginError("Official SOOP HLS stream enumeration failed") from None
            if not hls_streams:
                raise PluginError("The official SOOP plugin returned no HLS streams")
            yield from hls_streams.items()
            return
        if stream_password and not account:
            raise PluginError("grid_stream_password_requires_account; use --soop-grid-transport hls")

        channel, bno = self.match["channel"], self.match["bno"]
        profiles = official_grid_profiles(
            self.session,
            self.url,
            channel,
            bno,
        )
        referer = "https://play.sooplive.com/" + channel + ("/" + bno if bno else "")
        for profile in profiles:
            config = Config(
                broadcaster=channel,
                bno=bno,
                account=account,
                account_password=account_password,
                stream_password=stream_password,
                require_adult=bool(self.get_option("grid-require-adult")),
                duration=self.get_option("grid-duration"),
                startup_retries=self.get_option("grid-startup-retries") or 0,
                startup_window=self.get_option("grid-startup-window")
                if self.get_option("grid-startup-window") is not None
                else 2.0,
                max_bytes=self.get_option("grid-max-bytes"),
                capture_dir=os.environ.get("SOOP_GRID_CAPTURE_DIR") or None,
                diagnostics_dir=self.get_option("grid-diagnostics")
                or os.environ.get("SOOP_GRID_DIAGNOSTICS_DIR")
                or None,
                referer=referer,
                user_agent=self.session.http.headers.get("User-Agent"),
                grid_quality=profile.name,
                expected_grid_height=profile.expected_height,
            )
            try:
                config.validate()
            except GridError as exc:
                config.clear()
                raise PluginError(str(exc)) from None
            grid = SoopGridStream(self.session, config)
            if transport == "auto":
                fallback = OfficialHLSFallback(
                    self.session,
                    self.url,
                    account,
                    account_password,
                    stream_password,
                    purge_credentials=purge_credentials,
                    quality_key=profile.hls_label,
                )
                selected = SoopAutoStream(self.session, grid, fallback)
            else:
                selected = grid
            if profile.name == "original":
                self._grid_original_sort_name = (
                    profile.original_label.lower() if profile.original_label else "original"
                )
                yield _GRID_ORIGINAL_RANK_ALIAS, selected
            yield profile.name, selected
            if profile.name == "original" and profile.original_label:
                yield profile.original_label.lower(), selected


__plugin__ = SoopGridPlugin
