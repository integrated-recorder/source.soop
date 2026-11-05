# Live validation resume point — 2026-11-04

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

## Latest status — 2026-11-05 (supersedes the pending-run notes above)

The user currently cannot provide a test broadcast and directed offline-only
work. Do not start another live capture unless availability/authorization is
later changed.

* The 2-hour exact-candidate own-broadcast run completed on the same bundle
  hash and passed all five post-validation checks. Its A/V marker result covers
  common overlap and has censored edges; it is not a perceptual-latency test.
* The 6-hour exact-candidate capture already completed before the offline-only
  instruction. Its 21,600-second output passed the recording TS scan and full
  FFmpeg H.264/AAC decode; VCL/AAC comparison matched exact contiguous source
  intervals and SPS/PPS sets. The independent raw Grid validator failed at
  `reader_closed_not_seen` because the bounded diagnostics event log reached
  its cap. Its timestamp-dependent check then failed because the report was
  absent. The final `diagnostics/summary.json` does verify closed state, EOF,
  duration-limit stop, no error, complete drain, and equal accepted/read/
  emitted/mux byte totals with zero discarded/unaccepted bytes. The offline
  6-hour marker analysis did not finish within 15 minutes and was stopped; do
  not mark 6-hour source-relative A/V sync or the independent timestamp
  comparison as verified.
* No Parent/Cache fault was injected in these clean runs. Controlled recovery
  remains NOT TESTED.

Current campaign: **PARTIAL**. Stable: **NO-GO**. Further work is offline-only:
repair or replace the private bounded-log completion evidence path and, if
feasible, complete source-relative marker analysis on the already captured
files. Production source and bundle remain unchanged at the candidate identity
listed above.
