# Bounded startup retry: experimental contract

This implementation is disabled by default. Production adoption/default enablement is **NO-GO pending real-world benefit evidence**; local opt-in investigation is supported. Prior Stable Candidate evidence is preserved as historical artifact-specific evidence.

## Ownership and states

Parent → original Continuity → original MediaSink → StartupStage → original StreamIO buffer → consumer. Staging is single-producer on the existing receiver worker. COLLECTING holds generated TS; READY requires validated video output/AAC, existing boundary status consistent, the configured wall-time observation and a common presentation timestamp span; COMMITTED is latched before any attempted external write; ABORTED clears unpublished bytes. This validates an accepted prefix, not a presentation watermark or proof all future frames exist.

Each attempt creates a fresh Config, HTTP session, certificate, Center/node key, Parent, Continuity, MediaSink/H264/AAC/mux and AttemptNetwork. Only cancellation and the owner socket registry are shared. Parent failover stays inside the original receive_media implementation. The resolved BNO is pinned across attempts. Python immutable strings cannot be reliably zeroized; references are cleared at commit/final exit and no secrets are serialized.

Current MediaSink.close() clears pending startup/audio data and computes diagnostics; it does not emit held HRD frames. Staging additionally defends against an emit from a failed attempt's cleanup: readiness is evaluated only on validated media progress, never an emit/EOF alone. A synchronous commit flush cannot interleave new producer data. Concurrent reader close wakes backpressure; no post-commit retry follows a failed/partial flush.

## Limits and eligibility

CLI: --soop-grid-startup-retries N (0..2), --soop-grid-startup-window S (0.5..8, default2). Memory payload cap32MiB; Python allocator/upstream/buffer overhead is additional. Session startup15s, total45s. HTTP requests retain their existing bounded blocking timeouts, so an in-flight HTTP call can unwind after the deadline (up to the existing read timeout); this is not an instantaneous transport abort. No unlimited reconnects or watchdog thread is added.

Only exact frame_sequence_gap_or_reset while initial Cache is active, one Parent connection, no Parent failover and no publication may retry. Authentication, parsing, unsupported codec, identity, timestamp, cancellation, budget or staging failures do not retry. Terminal exhaustion preserves the original frame-gap error. New timeout/unverified errors remain explicit.

Opt-in duration is an overall acquisition budget from orchestration entry including Bootstrap/retries; default-off timing is unchanged. max_bytes is shared across attempts, accounting Parent traffic from failed attempts; control traffic makes this conservatively stricter than the legacy per-attempt media counter. Normal transport=auto/HLS behavior is unchanged; startup failures are not added to HLS fallback eligibility. Raw capture with retry is rejected until per-attempt ownership can be supported safely.

## Metrics

startup_staged_bytes is cumulative retained staging input, startup_aborted_bytes is unpublished staged data discarded, startup_committed_bytes is staged data scheduled for the commit flush, startup_peak_bytes is maximum logical staged payload, and startup_commit_attempt identifies the selected publication attempt. A cancellation during a partial commit may have accepted/discarded/unaccepted bytes: use StreamIO buffer accounting, not planned commit size, for actual delivery. Successful runs require accepted=emitted=consumed, zero discard, natural EOF and drain. These are not disk write/fsync guarantees.

## Evidence and remaining gates

Synthetic real StreamIO tests cover normal start, 1/2 startup failures, exhaustion, nonretryable errors, pre/post-commit cancellation, memory limit, single-track rejection, total budget and credential lifecycle. Generated legal B-frame/AAC output after retry is byte-identical to direct baseline and fully decoded by FFmpeg. An original Parent disconnect/overlap path inside real StreamIO remains byte-identical without startup retry.

Limited public tests include successful first-attempt starts and fail-closed exhaustion with zero publication. Natural first-failure→later-success was not observed. A synthetically injected first error did establish a second full authenticated real Grid session; that session's pre-existing A/V boundary check remained incomplete and staging timed out without publication. This is not a successful retry recording. No public content was stored. No 2h test, perceptual A/V test or new codec support is claimed.

## Readiness audit (local follow-up)

`MediaSink.update_startup_readiness()` now checks validated decoder/audio state, observed cadence, unchanged start-boundary/preroll evidence and a common prefix. It does not require the instantaneous ends of ongoing audio/video to align. `update_coverage()` and `validate_media_output()` still enforce the original whole-recording criteria at close. The final arithmetic and payload/TS output are unchanged in three generated before/after comparisons, including a deliberately incomplete end.

The prior eighteen natural retry failures were actual repeated Cache gaps, not readiness rejections. The historical controlled second session had an unexplained545ms start offset above its510.844ms boundary and must remain blocked. The new separation fixes a distinct ongoing-endpoint gating error; it does not recover missing Cache messages or permit that start mismatch. Deadline-induced stops remain explicit, while concurrent auth/media/protocol errors keep their original error codes with `startup_deadline_reached` recorded separately.

Synthetic real StreamIO verifies earlier safe startup on a delayed-AAC prefix, later normal EOF after AAC catches up, and final failure if it never catches up. Natural server adoption remains unproven; do not transfer historical Stable Candidate2h results to the new artifact.
