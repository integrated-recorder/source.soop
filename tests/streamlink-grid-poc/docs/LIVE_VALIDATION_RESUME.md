# Live validation resume point — 2026-11-04

## 2026-11-05 status correction

The user authorized a single 150-second own-broadcast pilot. It was performed
using the then-current predecessor bundle `c75fa14…`. The synthetic publisher
finished; the receiver stopped at 144.867 seconds on a trailing packet with
only the already-active SPS and PPS, reporting `h264_vcl_missing`. The
captured recording passed TS scan, FFmpeg full decode, coded-media identity,
and short-window marker timing, but EOF/drain failed. A narrowly scoped fix
now accepts only a nonempty SPS+PPS-only unit whose definitions exactly match
the active sets, returning no media timestamp. All other no-VCL post-start
cases still fail closed. Offline tests pass on bundle
`12f1fac8ad1ab3e7634ec37ef28ff88fb0c84ee78ae0a9c165ff1b61ac534fe1`;
this fixed bundle has not been live-tested. No further live run was authorized
by the 150-second approval. Historical 2-hour/6-hour runs used `c75fa14…`,
not the fixed bundle.

## Current exact candidate

* Repository branch: `fix/grid-startup-readiness`
* Source HEAD: `98063420327bda52996796e9bb8cb87373eb32ea`
* Bundle: `dist/soop_grid.py`
* Bundle SHA-256: `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`
* Runtime: Linux x86_64, Python 3.12, Streamlink 8.6.2
* FFmpeg/FFprobe: 6.1.1-3ubuntu5, available through the isolated prior-validation wrappers under `private-validation/native-grid-stability-20261031/long-run/toolchain/bin/`.

The worktree had no tracked changes before this note. The pre-existing untracked `tests/test_suffix_latejoin.py` was preserved and excluded from runs and staging.

## Offline checks completed on this candidate

* Source suite: **814 passed, 0 skipped**.
* Single-file bundle parity: **805 passed, 0 skipped**.
* Ruff check and format check: passed for the 57 tracked source Python files; the generated concatenated bundle is excluded from source lint because its module concatenation intentionally violates normal top-level import placement.
* `compileall`, deterministic bundle check, `dist/SHA256SUMS`, `git diff --check`, and Streamlink 8.6.2 plugin discovery: passed.
* FFmpeg/FFprobe generated-media smoke: generated 30-frame 160×96 H.264 and 48 kHz AAC-LC fixtures, probed both, and fully decoded both. This only verifies the local toolchain/fixture path, not Grid reception.
* No production code or bundle bytes changed in this follow-up.

The result is offline regression evidence. It does not satisfy live Grid delivery, current-build source-relative A/V sync, live Parent/Cache recovery, or real-time 2 h/6 h endurance.

## Exact-candidate live Smoke — 2026-11-04

The user subsequently authorized live testing if feasible. A 45-second cutoff
attempt stopped with `media_track_coverage_incomplete`; the receiver fail-closed
because the forced stop left an unmatched A/V endpoint. No integrity check was
weakened. A second run used the existing synchronized 150-second synthetic
H.264/AAC fixture and captured 120 seconds. The test publisher and receiver
both exited 0 on this exact bundle.

* Native Grid profile: quality code 1; SPS 1920×1080, H.264 High, B-frames;
  Grid timing parsed as 60 fps. AAC-LC, 48 kHz, stereo.
* Receive: 120.465 seconds; 7,308 video Grid units, 5,712 AAC AUs; zero Grid
  sequence discontinuities, missing frames, or recovery failures; one Parent.
* Source comparison: SPS/PPS sets equal; all emitted VCL units and AAC AUs
  matched one contiguous interval of the generated source.
* Output gate: TS recording verification passed with >120 seconds of both
  decoded tracks; StreamIO drain completed. Independent timestamp check
  passed 7,231 video PTS/DTS pairs and 238 audio PES checks, with zero DTS
  regressions/mismatches, zero audio PTS mismatches, and 242 valid PSI CRCs.
* Independent raw Grid H.264 decode status was
  `pass_with_measured_exclusions`: the capture began before an IDR, so the
  first 77 non-IDR preroll chunks (492,899 bytes) were not independently
  decodable. Those match the receiver's 77 measured preroll frames and were
  withheld from the TS output. The TS recording gate fully decoded its
  7,231 output video frames and 121.856 seconds of audio; raw Grid decode had
  zero interior/suffix exclusions and zero display-order PTS regressions.
* 46 matched audiovisual markers over 118.466 seconds; added offset p95/max
  0.667 ms and estimated added drift 1.85 ppm. The analyzer reports unmatched
  edge markers because the receiver interval is shorter than the source.

The exact-candidate 2-hour run is now active in the existing user-owned tmux
session `soop-grid-stability-2h-20261104`. The private harness is generating
its 7,320-second synchronized fixture; publishing has not begun yet. Its run
directory is private, and its durable execution log records the exact bundle
hash. Current attempt ID: `20261104T074858Z-2efa4619` (under the private
`runs/` store). Do not start a 6-hour run until this 2-hour candidate completes
and passes all gates.

Still pending: exact-candidate 2-hour run result, 6-hour run, controlled live
Parent/Cache recovery, and any live Type-1 B-picture/MMCO5 case.

## Safe resumption procedure

Resume only after the user confirms an authorized self-broadcast is available. Keep credentials in the existing private configuration or process environment; never copy them into the repository, shell history, logs, or reports. First verify the current HEAD and bundle hash, then run the existing private harness preflight and a 30–60 second Smoke using this exact bundle. Do not start 2 h/6 h runs until Smoke passes all payload, continuity, timestamp, TS, decode, and EOF/drain checks. Use the existing bounded endurance harness and its disk/time limits; stop immediately on a media-integrity error. Run controlled failures only after normal endurance prerequisites pass.

Before live work, verify the candidate identity again:

```sh
git rev-parse HEAD
sha256sum dist/soop_grid.py
```

Expected values for this resume point are the source and bundle identities listed above. If either differs, treat it as a new candidate and rerun the applicable gates. Keep all captures and media private and short-lived; publish only redacted metrics and hashes needed for verification.

## Release gate

Campaign status: **PARTIAL — LIVE SMOKE VERIFIED FOR THIS SUBSET; 2 h RUN IN PROGRESS**. Stable status: **NO-GO** until the exact candidate passes the 2 h, 6 h, source-relative synchronization, and controlled recovery gates. Historical live or endurance results from other bundle hashes do not satisfy these gates.

## Latest status — 2026-11-05 (supersedes earlier availability notes)

The user first requested offline-only work, then authorized one synthetic
150-second self-broadcast. That bounded pilot was performed on bundle
`c75fa14…` and exposed a shutdown-boundary case: a trailing Grid unit repeated
the active SPS and PPS without VCL, and the receiver failed with
`h264_vcl_missing` at 144.867 seconds. The output before that point passed TS
scan, full FFmpeg decode, coded-unit identity and short-window marker checks;
EOF/drain did not pass.

A narrow source fix now ignores only a nonempty SPS+PPS-only unit whose parsed
definitions are already active and identical. It emits no picture/timestamp;
SPS-only, PPS-only, changed definitions, AUD-only and all other post-start
no-VCL cases remain rejected. Targeted regression and full source/bundle
tests pass. The rebuilt bundle is
`12f1fac8ad1ab3e7634ec37ef28ff88fb0c84ee78ae0a9c165ff1b61ac534fe1`.
This fixed bundle has not been live-retested; the approval covered one 150s
pilot, which has already been used.

The prior 2-hour and 6-hour captures belong to bundle `c75fa14…`, not this
candidate. A post-hoc timestamp-only reconciliation of the 6-hour source and
output matched 1,296,034 video and 1,012,584 AAC timestamp pairs; relative
A/V timestamp shift was 0.333 ms at start and end, with zero fitted drift.
This is not a decoded six-hour flash/click perceptual-sync result. The 6-hour
event-marker analysis did not complete. Controlled Parent/Cache fault
recovery remains NOT TESTED.

Current campaign: **PARTIAL**. Stable: **NO-GO**. The next live step is a
separately authorized short retest of the fixed bundle, followed by endurance
only after its EOF/drain and media-integrity gates pass.
