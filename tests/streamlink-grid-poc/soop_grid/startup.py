# SPDX-License-Identifier: AGPL-3.0-only
# Copyright (c) 2026 source.soop contributors
"""Opt-in bounded startup staging; committed recordings never restart epochs."""

import threading
import time
from dataclasses import replace
from soop_grid.protocol import GridError, Cancelled, Network


class AttemptStop:
    def __init__(self, owner, deadline):
        self.owner = owner
        self.deadline = deadline
        self.local = threading.Event()

    def is_set(self):
        return (
            self.local.is_set()
            or self.owner.is_set()
            or (self.deadline is not None and time.monotonic() >= self.deadline)
        )

    def set(self):
        self.local.set()

    def wait(self, timeout=None):
        end = None if timeout is None else time.monotonic() + timeout
        while not self.is_set():
            if end is not None and time.monotonic() >= end:
                return False
            self.local.wait(min(0.05, max(0, end - time.monotonic())) if end else 0.05)
        return True


class AttemptNetwork(Network):
    def __init__(self, owner, deadline):
        super().__init__()
        self.owner = owner
        self.stop = AttemptStop(owner.stop, deadline)
        self.budget_deadline = deadline

    def connect(self, address):
        sock = super().connect(address)
        with self.owner._lock:
            cancelled = self.owner.stop.is_set()
            if not cancelled:
                self.owner._sockets.add(sock)
        if cancelled:
            self.release(sock)
            raise Cancelled("receiver_closed")
        return sock

    def release(self, sock):
        with self.owner._lock:
            self.owner._sockets.discard(sock)
        super().release(sock)

    def close(self):
        self.stop.set()
        with self._lock:
            sockets = list(self._sockets)
        for sock in sockets:
            self.release(sock)


class StartupStage:
    def __init__(self, emit, stop, stats, capacity):
        self.emit = emit
        self.stop = stop
        self.stats = stats
        self.capacity = capacity
        self.data = bytearray()
        self.state = "COLLECTING"

    def write(self, data):
        if self.stop.is_set():
            raise Cancelled("receiver_closed")
        if self.state == "ABORTED":
            self.stats["startup_aborted_bytes"] += len(data)
            return
        if self.state == "COMMITTED":
            self.emit(data)
            return
        if len(self.data) + len(data) > self.capacity:
            raise GridError("startup_staging_limit")
        self.data.extend(data)
        self.stats["startup_staged_bytes"] += len(data)
        self.stats["startup_peak_bytes"] = max(self.stats["startup_peak_bytes"], len(self.data))

    def commit(self):
        if self.state != "COLLECTING" or self.stop.is_set():
            raise Cancelled("receiver_closed")
        self.state = "READY"
        # A failed/partial external write must never be retried as an unpublished attempt.
        self.state = "COMMITTED"
        self.stats["startup_committed_bytes"] += len(self.data)
        self.emit(self.data)
        self.data.clear()

    def abort(self):
        if self.state == "COMMITTED":
            raise GridError("startup_already_committed")
        self.stats["startup_aborted_bytes"] += len(self.data)
        self.data.clear()
        self.state = "ABORTED"


def receive_startup(
    config,
    owner,
    emit,
    report,
    stats,
    attempt,
    *,
    retries=2,
    window=2,
    capacity=32 << 20,
    attempt_timeout=15,
    total_timeout=45,
):
    started = time.monotonic()
    duration_deadline = None if config.duration is None else started + config.duration
    startup_deadline = started + total_timeout
    byte_budget = config.max_bytes
    input_bytes = 0
    pin_bno = config.bno
    mirrored = set()
    stats.update(
        startup_attempts=0,
        startup_retries=0,
        startup_staged_bytes=0,
        startup_aborted_bytes=0,
        startup_committed_bytes=0,
        startup_peak_bytes=0,
        startup_commit_attempt=0,
        startup_deadline_reached=0,
        stream_emit_bytes=0,
    )
    try:
        for number in range(1, retries + 2):
            if owner.stop.is_set():
                raise Cancelled("receiver_closed")
            now = time.monotonic()
            deadline = min(
                startup_deadline,
                now + attempt_timeout,
                duration_deadline if duration_deadline is not None else float("inf"),
            )
            if now >= deadline:
                raise GridError("startup_timeout")
            if byte_budget is not None and input_bytes >= byte_budget:
                raise GridError("startup_byte_limit")
            for key in mirrored:
                stats.pop(key, None)
            mirrored.clear()
            child = AttemptNetwork(owner, deadline)
            child.acquisition_deadline = duration_deadline
            local = {}
            copied = replace(
                config,
                bno=pin_bno,
                duration=None if duration_deadline is None else duration_deadline - now,
                max_bytes=None if byte_budget is None else byte_budget - input_bytes,
            )
            stats["startup_attempts"] = number
            stats["startup_retries"] = number - 1
            report("startup_attempt_started")
            cache = False
            first_media = None
            committed = False

            def forward(data):
                emit(data)
                stats["stream_emit_bytes"] += len(data)

            stage = StartupStage(forward, owner.stop, stats, capacity)

            def event(
                name,
                local=local,
                deadline=deadline,
                used_bytes=input_bytes,
                stage=stage,
                number=number,
                child=child,
            ):
                nonlocal cache, first_media, committed
                if name == "cache_request_sent":
                    cache = True
                if name in ("live_push_transition_requested", "recovery_started", "parent_failover_started"):
                    cache = False
                mirrored.update(k for k in local if k != "stream_emit_bytes")
                stats.update({k: v for k, v in local.items() if k != "stream_emit_bytes"})
                if name == "parent_last_media_received":
                    if not committed and time.monotonic() >= deadline:
                        raise GridError("startup_timeout")
                    if (
                        byte_budget is not None
                        and used_bytes + local.get("parent_wire_bytes", 0) > byte_budget
                    ):
                        raise GridError("startup_byte_limit")
                    if first_media is None:
                        first_media = time.monotonic()
                    common_start = max(
                        local.get("video_output_first_pts_90k", 0), local.get("audio_output_first_pts_90k", 0)
                    )
                    common_end = min(
                        local.get("video_output_end_pts_90k", 0), local.get("audio_output_end_pts_90k", 0)
                    )
                    if (
                        not committed
                        and stage.data
                        and time.monotonic() - first_media >= window
                        and common_end - common_start >= window * 90000
                        and local.get("video_output_frames", 0) > 0
                        and local.get("audio_output_access_units", 0) > 0
                        and local.get("startup_av_ready") == 1
                    ):
                        if owner.stop.is_set():
                            raise Cancelled("receiver_closed")
                        committed = True
                        stats["startup_commit_attempt"] = number
                        stats["startup_first_output_ms"] = (time.monotonic() - started) * 1000
                        config.clear()
                        # Bootstrap/staging deadlines no longer constrain established recording.
                        child.stop.deadline = None
                        child.budget_deadline = None
                        report("startup_ready")
                        stage.commit()
                        report("startup_committed")
                report(name)

            try:
                attempt(copied, child, stage.write, event, local)
                if not committed:
                    raise GridError("startup_unverified")
                return
            except BaseException as exc:
                # COMMITTED is set before any attempted write, including a partial cancelled flush.
                if committed or stage.state == "COMMITTED":
                    if stage.state != "COMMITTED":
                        stage.abort()
                    raise
                stage.abort()
                expired = time.monotonic() >= deadline
                stats["startup_deadline_reached"] = int(expired)
                report("startup_attempt_aborted")
                if owner.stop.is_set():
                    raise Cancelled("receiver_closed") from None
                if expired:
                    # Preserve an actual validation/auth/protocol error even when the
                    # deadline expired concurrently; only deadline-induced stops map.
                    if isinstance(exc, GridError) and str(exc) in (
                        "receiver_closed",
                        "capture_deadline_reached",
                        "startup_unverified",
                        "startup_timeout",
                    ):
                        raise GridError("startup_timeout") from None
                    raise
                if (
                    not isinstance(exc, GridError)
                    or str(exc) != "frame_sequence_gap_or_reset"
                    or not cache
                    or local.get("failover_attempts", 0)
                    or local.get("parent_connections", 0) != 1
                    or number > retries
                ):
                    raise
            finally:
                input_bytes += local.get("parent_wire_bytes", local.get("wire_bytes", 0))
                stats["startup_total_input_bytes"] = input_bytes
                pin_bno = pin_bno or (str(local["bootstrap_bno"]) if local.get("bootstrap_bno") else None)
                mirrored.update(k for k in local if k != "stream_emit_bytes")
                stats.update({k: v for k, v in local.items() if k != "stream_emit_bytes"})
                copied.clear()
                child.close()
    finally:
        config.clear()
