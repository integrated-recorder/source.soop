# Six-hour validation recovery — 2026-11-05

## Verdict

**Historical six-hour endurance gate: PASS** for source HEAD
`98063420327bda52996796e9bb8cb87373eb32ea` and bundle SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
This verdict uses the preserved run and new offline re-analysis. It does not
apply to the current source HEAD `3b8e40741e3c2780a7a983875f631005b68b439e`
or current bundle `361b63eb6969e9a8fc2f21506294041a356d03d94e1353084fcdfe58ad195794`.
No new SOOP broadcast or recording was performed.

The separate Parent/Cache fault-recovery gate remains **NOT TESTED**. Current
bundle six-hour endurance also remains **NOT TESTED**. Stable release remains
**NO-GO** because the six-hour run is an older bundle and controlled recovery
is not evidenced.

## Preserved evidence and run identity

The private run identity, file inventory, sizes and SHA-256 values are recorded
in the private file `SIX_HOUR_EVIDENCE_INVENTORY.md` beside the recovery tools.
The run manifest identifies capture `full-20261104T141541Z`; its candidate
source/bundle pair matches the preserved plugin copy. The recorded TS and
reference hashes match the full recording-verification report. The receiver
and publisher both exited 0. The private inventory contains media hashes but
no media contents or credentials are included in this repository.

The bounded diagnostics stream ended at its configured 6,070-line limit and
does not contain `reader_closed`. This is reported as
`DIAGNOSTIC_EVENT_TRUNCATED`; event-level close sequencing is therefore
incomplete. The final summary independently records `reader_state=closed`,
EOF observed, drain complete, no error/protocol failure, zero discarded and
unaccepted bytes, and matching reader/accepted/emitted/mux totals of
366,801,160 bytes. The receiver and harness process exit codes are both zero,
and the output file size is the same. The summary is tied to the run by the
run directory/manifest and tested bundle identity. Reader closure is thus
**VERIFIED_FROM_FINAL_STATE_AND_PROCESS_EXIT**, without claiming the missing
event was observed.

The old independent validator's `reader_closed_not_seen` was a validator
false negative. Its later raw-H.264 `ffprobe show_frames` subprocess exceeded
its 900-second limit, so that combined report did not produce its transport
stream section. This is not a failed TS decode: the separately preserved
whole-recording TS verifier completed full video and audio decoding and is
bound to the recording SHA-256.

## Validator corrections and tests

* Close evidence is separated into event-log evidence and final-state/process
  evidence. Truncation can explain an absent terminal event, but cannot
  override a missing summary, mismatched run identity, nonzero exit, byte
  accounting discrepancy, media-integrity failure, or non-clean close.
* The timestamp checker was run against a fresh input-only directory exposing
  only raw Grid wire, the TS recording, and final summary. It did not consume
  or require a previous `transport_streams` report.
* The indexed A/V analyzer's two-hour positive control reproduced the prior
  analyzer exactly for all 721 common events: video event time, audio event
  time, and added-offset differences were each 0 ms. Ten terminal fixture
  events were right-censored, with no interior ID gaps.
* A validation assertion that incorrectly compared the number of detected
  click events with the total number of AAC packets was corrected. The proper
  relationship is between decoded PCM frame metadata rows and source AAC
  packet timestamps; 2-hour and 6-hour counts agree exactly (343,126 and
  1,018,126, respectively).
* Private unit tests cover observed close, truncated event log with clean
  summary, missing summary, mismatched identity/accounting, nonzero exits,
  media-gap independence, DTS regression, duplicate PTS, audio timestamp
  discontinuity, Grid-composition mismatch, PCR regression/wrap, fake close
  with crash exit, and malformed middle JSONL. Result: **9 unittest methods
  passed** (case matrices included).

## Independent timestamp verification

The checker directly parsed 1,338,300 Grid media units and the TS output:

* 1,296,034 Grid-composition-derived video DTS/PTS pairs compared; mismatch 0.
* 42,191 audio PES timestamps compared; mismatch 0.
* Duplicate video PTS: 0; non-increasing video DTS: 0.
* Audio AU PTS progression is monotonic; audio sample-clock/TS mapping has no
  mismatch.
* The preserved verifier reports **1,951,070** TS packets; sync, continuity,
  PSI CRC, PCR regression,
  explicit discontinuity, transport/adaptation error, and decoder error
  counts are all zero. Maximum PCR value delta is 17 ms.

The exact direct-check result is stored privately as
`independent-timestamps.json`. Historical packet-timeline reconciliation also
reports an initial and final relative A/V timestamp shift of 0.333 ms and
0 ppm change. These are timestamp-mapping results, separate from event-based
sync and from coverage-edge offsets.

## Source-relative flash/click analysis

The previous analyzer tried to decode every 1080p output frame to rediscover
generated white-flash markers and timed out. The recovered run contains a
trusted event schedule and a unique contiguous, byte-identical VCL/AAC source
interval. The optimized analysis indexes flash frames by scheduled display
time and exact VCL identity, decodes source AAC once, and maps identical AAC
AUs to output packet timestamps. It does not substitute duration similarity
for event matching.

* Source flash/click events: 2,165.
* Matched source-relative events: 2,155 across 21,595.95 seconds.
* Interior unmatched IDs: 0. The final 10 events are beyond captured output
  coverage and are classified as right-censored tail, not as passed matches.
* Added A/V offset: median 0.333 ms; p95 0.667 ms; maximum absolute 0.667 ms.
* Fitted added-offset drift: −0.000344 ppm over the matched interval.
* The 2-hour positive control agrees exactly with the previous event analyzer
  for all 721 common events.

This verifies source-relative coded-event timing for the common captured
interval. It does not measure physical display/speaker latency or human
perception. The 6-hour marker analysis completed under the 15-minute execution
budget. The audio-metadata output timestamp to final JSON interval was 147.6
seconds; the complete command wall time was not separately instrumented, so
147.6 seconds is not presented as total runtime. Its detailed private output
is `six-hour/indexed-av-reconciliation.json`.

## Media identity, decode and resources

The preserved source/Grid identity report finds one unique contiguous match
for VCL and AAC data, equal SPS/PPS sets, and no unexplained interior loss.
The receiver withheld 75 measured pre-IDR video preroll frames; these were not
counted as output. The remaining 1,296,034 H.264 frames and 1,012,584 AAC-LC
48 kHz stereo access units are byte-identical to the corresponding source
interval. The full TS verifier reports 1,951,070 packets, zero TS continuity
and PSI CRC errors, 0 PCR regressions, 0 DTS regressions, and full decoding of
all frames/AUs. Video duration is 21,600.617 s; audio duration is 21,601.792 s.

Resource monitoring contains 359 samples over 21,680.8 seconds. The receiver
process remained at 13 file descriptors and 3 threads in sampled intervals;
its RSS peaked at 59,264 KiB and declined from about 59 MiB after startup to
about 10 MiB near the end. Process-tree peaks were 150,176 KiB RSS, 30 file
descriptors, and 9 threads; process composition changed during the run. This
is evidence against unbounded growth in this run, not a universal leak proof.

## Per-gate result

| Gate | Result | Evidence / limitation |
|---|---|---|
| Capture | PASS | 21,600.552 s; receiver and publisher exit 0 |
| Media identity | PASS | Unique contiguous VCL/AAC identity; SPS/PPS match; measured preroll only |
| TS integrity and full decode | PASS | Full recording verifier passed; zero listed integrity/decode errors |
| Timestamp | PASS | Direct Grid-wire-to-TS comparison; no previous report dependency |
| A/V event sync | PASS for common interval | 2,155/2,165 matched; 10 tail events censored; no interior gaps |
| Reader close | PASS from final state | Summary, process exit, file size and byte accounting agree; close event was truncated |
| EOF/drain | PASS | EOF observed and drain complete; all byte counts equal; zero discarded/unaccepted |
| Resource stability | PASS for observed run | Bounded sampled RSS/FD/thread counts; not a general leak proof |
| Parent/Cache recovery | NOT TESTED | No fault was injected in this clean endurance run |

**Historical six-hour endurance verdict: PASS.** This supersedes the earlier
`PARTIAL` verdict for the same preserved run only. It does not change any
current-bundle, recovery, or release gate.

## Repository checks for this recovery change

Only documentation was changed in the tracked project; production source and
distribution bundle were not modified. The deterministic bundle check passed,
`dist/SHA256SUMS` verified, `compileall` passed, and `git diff --check` passed.
The current bundle remains SHA-256
`361b63eb6969e9a8fc2f21506294041a356d03d94e1353084fcdfe58ad195794`. The
private evidence-gate suite passed 9 unittest methods. The full repository
pytest suites could not run in this execution environment because `pytest` is
not installed; the direct bundle test runner also could not import its
`Crypto` dependency. Ruff is unavailable. These omissions do not affect the
offline re-analysis of the historical artifacts, but they are not reported as
passes.
