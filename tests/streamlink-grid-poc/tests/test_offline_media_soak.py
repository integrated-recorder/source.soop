# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
import subprocess

import pytest

from tools.offline_media_soak import MAX_SEGMENT_MINUTES, _remaining_timeout


def test_offline_soak_uses_one_global_subprocess_deadline():
    assert _remaining_timeout(100, now=90) == 10
    assert _remaining_timeout(900, now=0) == 900
    assert _remaining_timeout(100, now=99.25) == 0.75


def test_offline_soak_expired_deadline_fails_closed():
    with pytest.raises(subprocess.TimeoutExpired):
        _remaining_timeout(10, now=10)


def test_offline_soak_chunks_fixture_to_bound_peak_input_working_set():
    assert MAX_SEGMENT_MINUTES == 10
