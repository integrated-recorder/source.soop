# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""Empirically verified Native Grid profile requests."""

from dataclasses import dataclass
import re

from .protocol import GridError


@dataclass(frozen=True)
class GridProfile:
    name: str
    allocation_quality: int
    expected_height: int | None
    hls_label: str | None = None
    original_label: str | None = None
    join_quality: str = "ori"
    join_is_auto: bool = False


# These mappings are backed by bounded, same-broadcast Grid receives. The
# requested Center allocation values and JOIN selectors are empirical protocol
# values; they are deliberately not inferred from HLS VIEWPRESET names alone.
_GRID_PROFILES = {
    "original": (1, None, None, "ori", False),
    "720p": (2, 720, "hd4k", "ori", False),
    "540p": (4, 540, "hd", "ori", False),
    "360p": (8, 360, "sd", "low", True),
}
_LABEL = re.compile(r"([0-9]{3,4})p\Z", re.IGNORECASE)


def profile_by_name(name, *, original_height=None, original_label=None):
    if not isinstance(name, str) or name not in _GRID_PROFILES:
        raise GridError("grid_quality_unsupported")
    quality, fixed_height, hls_name, join_quality, join_is_auto = _GRID_PROFILES[name]
    if name == "original":
        if original_height is not None and (
            type(original_height) is not int or not 144 <= original_height <= 4320
        ):
            raise GridError("grid_quality_metadata_invalid")
        if original_label is not None and not isinstance(original_label, str):
            raise GridError("grid_quality_metadata_invalid")
        return GridProfile(
            name, quality, original_height, original_label, original_label, join_quality, join_is_auto
        )
    return GridProfile(name, quality, fixed_height, hls_name, None, join_quality, join_is_auto)


def profiles_from_viewpreset(viewpreset):
    """Return Grid modes only when their matching HLS labels are advertised.

    VIEWPRESET is an availability hint, not proof that Grid supports the same
    profile. Each lower Grid mode also requires an exact, empirically observed
    preset name and is gated against the received SPS height.
    """
    entries = {}
    if isinstance(viewpreset, list):
        for item in viewpreset:
            if not isinstance(item, dict):
                continue
            label, name = item.get("label"), item.get("name")
            if not isinstance(label, str) or not isinstance(name, str):
                continue
            match = _LABEL.fullmatch(label)
            if match:
                entries.setdefault((int(match.group(1)), name), label)

    original_entries = [(height, label) for (height, name), label in entries.items() if name == "original"]
    original = original_entries[0] if len(original_entries) == 1 else (None, None)
    original_ambiguous = len(original_entries) > 1
    result = [profile_by_name("original", original_height=original[0], original_label=original[1])]
    for stream_name, (quality, height, preset_name, join_quality, join_is_auto) in _GRID_PROFILES.items():
        if stream_name == "original":
            continue
        label = entries.get((height, preset_name))
        if label is not None and not original_ambiguous and height != original[0]:
            result.append(GridProfile(stream_name, quality, height, label, None, join_quality, join_is_auto))
    return tuple(result)
