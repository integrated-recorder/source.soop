# Current offline candidate supplement — 2026-11-03

## Exact-candidate regression rerun — 2026-11-03

* Code under test: source commit `51a5a157a1269c00a2a952d5ad0dacefed35ef7e`; bundle SHA-256 `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`. Later commits in this run were documentation-only; no code or bundle changed.
* Source pytest, excluding preserved untracked `tests/test_suffix_latejoin.py`: **774 passed, 0 skipped** in 57.61 s.
* Bundled parity via `tools/test_bundle.py`, with the same untracked test excluded: **765 passed, 0 skipped** in 52.91 s. The source run also includes the 9 single-file construction/loading tests.
* Environment: Python 3.12.3, pytest 8.4.2, Streamlink 8.6.2, FFmpeg/FFprobe 6.1.1 with libx264. Supplying the FFmpeg/FFprobe paths activated the media fixtures. The first sandboxed run without those paths had 64 skips and 14 local socket `EPERM` failures; the repeat used configured tool paths and permitted local socket tests. No SOOP endpoint was contacted.
* Ruff check and format: PASS (54 tracked project files); compileall: PASS; deterministic bundle `--check`: PASS; `dist/SHA256SUMS`: PASS; module and single-file Streamlink plugin discovery: PASS; `git diff --check`: PASS.
* No fresh live or endurance claim follows from this rerun. 2 h, 6 h and controlled live-failure stages remain **NOT TESTED**.

## Offline NAL-header hardening candidate — 2026-11-03

* Bundle SHA-256: `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
* Added common H.264 NAL-header validation before type-specific handling. A valid libx264 access unit with its initial AUD header changed to set `forbidden_zero_bit`, or an illegal nonzero `nal_ref_idc`, is rejected. The unmodified AUD control passes. The payload is not rewritten.
* Exact-candidate source regression: **773 passed, 0 skipped**. Exact-candidate bundled parity suite: **764 passed, 0 skipped**. Single-file tests: **9 passed**. Ruff check, Ruff format, compileall, deterministic builder check, manifest and Streamlink 8.6.2 discovery passed.
* The first sandboxed full run had 14 loopback/socketpair `EPERM` failures; rerunning outside the network-restricted sandbox passed. One diagnostics allowlist omission and one stale-bundle mismatch were fixed before the final runs.
* No live source was available per user confirmation. 2 h, 6 h and live controlled-failure tests remain **NOT TESTED**; historical live evidence belongs to other bundle hashes. Stable remains **NO-GO**.

## Deterministic parser robustness smoke — 2026-11-03

* Tested source commit: `51a5a157a1269c00a2a952d5ad0dacefed35ef7e`; subsequent changes in this branch are documentation-only, and the production bundle is unchanged.
* Added a fixed-seed test that submits 768 malformed/random byte inputs to `H264Clock.inspect()` and `parse_media()`, including inserted Annex-B start codes. It asserts malformed inputs either return or fail with the documented `GridError` family, never an unexpected Python exception. This is a bounded parser robustness smoke test, not coverage-guided fuzzing or a proof of parser safety.
* The test is source-only; production bundle SHA remains `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
* Latest source suite: **774 passed, 0 skipped**. Bundled parity: **765 passed, 0 skipped**. The untracked suffix experiment remains excluded.

---

* Base commit: `b070755ed1f1593714575c3813ace1bc64da221e` on `fix/grid-startup-readiness`.
* Candidate source commit: `c149834f6ad98cdaac52b6559b5067e09efa4fcf` (pushed to origin).
* Candidate bundle: `dist/soop_grid.py`, SHA-256 `00af27789d671d5230499c551bbd7c49f27727585b3b6b57faabac05ae886cef`.
* Environment: Linux x86_64, Python 3.12.3, Streamlink 8.6.2, FFmpeg/FFprobe 6.1.1 with libx264.
* Source tests: **771 passed, 0 skipped** (`tests/test_suffix_latejoin.py` excluded and preserved). Bundle tests against the final regenerated bundle: **762 passed, 0 skipped** (47.12 s).
* MMCO-5 generated offline fixture: one progressive Baseline/CAVLC, no-B, one-reference stream; exactly one reference P picture at AU 10 carries MMCO-5. Three variants signal POC types 0/1/2. FFmpeg independently decodes each transformed elementary stream with frame hashes matching its source.
* Each variant traverses production `MediaSink` → `SoopGridReader.open/read/close` → MPEG-TS; 60 video AUs and 94 AAC-LC AUs are emitted, VCL NAL bytes match, StreamIO byte accounting and EOF/drain complete, and FFmpeg fully decodes the output TS.
* Ruff check, changed-tracked-file format check, compileall, deterministic bundle `--check`, SHA manifest verification, `git diff --check`, and Streamlink 8.6.2 plugin discovery (`soop` and `soop_grid`) pass. Standalone bundle tests: 9 passed. No new SOOP live session was run, per user availability. This does not alter previous-hash 30-minute evidence. 2 h, 6 h and live controlled-failure endurance remain NOT TESTED.
* This is a narrow synthetic conformance case, not proof of arbitrary MMCO/DPB behavior or current-hash live behavior. Stable remains **NO-GO**.

---

# Exact-candidate endurance result

## Offline-only follow-up — H.264 V16 SEI envelope

No live test source is available, so this follow-up is offline. Six new tests
exercise H.264 V16 SEI payload types 213–215 through the generic bounded parser
and MediaSink's raw AU capture, plus malformed-length rejection. They do not
validate H.274/VSEI payload semantics. Production code and bundle bytes are
unchanged. Source pytest: **780 passed, 0 skipped**; bundle parity: **771
passed, 0 skipped**. The source count includes the 9 single-file construction
tests. Ruff check/format, compileall, deterministic bundle check, manifest,
Streamlink discovery and `git diff --check` passed. The initial sandbox run
failed 14 local socket cases with `EPERM`; the permission-enabled offline rerun
passed. No SOOP endpoint was contacted. The 2 h, 6 h and live controlled-failure
stages remain NOT TESTED.

## Offline-only follow-up — TS scanner mutation smoke

A fixed-seed regression makes 64 copies of a generated valid TS and mutates
one to four packet bytes in each copy. It verifies bounded scanner result
fields, packet accounting, and hashing of the complete mutated input. This is
a deterministic mutation smoke test, not coverage-guided fuzzing. No production
code or bundle bytes changed. Source pytest: **781 passed, 0 skipped**; bundled
parity: **772 passed, 0 skipped**. The source count includes nine standalone
bundle construction/loading tests. The test used only generated local media;
no SOOP endpoint was contacted. Live, 2 h, 6 h and live controlled-failure
stages remain NOT TESTED.

## Current-HEAD offline recovery rerun — 2026-11-03

On commit `69b2cce2a6f45dbee2b94bfdd95ee7ddf925b2c7`, the focused synthetic
transport suite (`test_recovery.py`, `test_streamio.py`,
`test_live_fault_inject.py`, `test_startup_retry.py`) passed: **114 passed** in
5.71 s. It includes local Parent TCP close/cache-overlap recovery, overlap
rejection, candidate exhaustion, cancellation, output backpressure and reader
shutdown checks. Loopback was permitted for this run; no SOOP service endpoint
was contacted. This is not live failure-injection evidence and does not satisfy
the endurance or Stable gates.

## Near-valid H.264 parser mutation regression — 2026-11-03

Added a fixed-seed, 1,024-case mutation test based on a valid synthetic
progressive POC-2 SPS/PPS/IDR access unit. Each case mutates one to four NAL
header/RBSP bytes while preserving Annex-B start codes, then requires either a
normal parse result or a documented `GridError`. The targeted test passed; the
full source suite passed **782 tests** and the bundled parity suite passed
**773 tests**, with zero skips. This is bounded near-valid mutation smoke, not
coverage-guided fuzzing or semantic conformance proof. Production source and
bundle remain unchanged. The tested tree was based on `ee61fae6884371c247cfeb1ecb431854bfd6ac92`.

## Near-valid ADTS framing mutation regression — 2026-11-03

A fixed-seed, 1,024-case test mutates one to four bytes in eight real
FFmpeg-generated ADTS frames. Every candidate either fails with `GridError` or
has bounded frame count, exact input reconstruction, consistent raw-sample
totals and exact rational duration. The test passed; full source and bundle
regressions now report **783 passed** and **774 passed**, respectively, with no
skips. The source run includes nine standalone bundle tests. This validates
framing arithmetic only; it does not validate AAC CRC values or decode mutated
AAC payloads. Production code and bundle are unchanged; live and endurance
gates remain untested.

## Repeated StreamIO lifecycle smoke — 2026-11-03

Added and ran 64 local synthetic StreamIO sessions through open, complete
read, EOF/drain and close. Each session's bytes match exactly with no discarded
or unaccepted output; receiver worker threads returned to baseline and Linux
FD count was unchanged. Full source and bundled regressions passed **784** and
**775** tests, respectively, with no skips. This checks repeated lifecycle
cleanup, not RSS trend over hours or network/Parent endurance. Production
source and bundle remain unchanged.

## Candidate and environment

* Branch: `fix/grid-startup-readiness`
* Commit: `b070755ed1f1593714575c3813ace1bc64da221e`
* Bundle `dist/soop_grid.py` SHA-256: `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`
* Linux x86_64, Python 3.12.3, Streamlink 8.6.2
* FFmpeg/FFprobe available to this run: 6.1.1 (Ubuntu build), with libx264; not the 9.0.2 documented by earlier validation reports
* Available filesystem space before live tests: approximately 198 GB

## Offline verification performed

| Check | Result |
|---|---|
| Source pytest, excluding preserved untracked `tests/test_suffix_latejoin.py` | Initial run: 764 passed, 2 skipped. Supplemental run after replacing the encoder-specific fixture: **767 passed, 0 skipped, 50.47 s** |
| Bundle pytest, excluding preserved untracked `tests/test_suffix_latejoin.py` | Initial run: 755 passed, 2 skipped. Supplemental run on the same production bundle: **758 passed, 0 skipped, 44.43 s** |
| Former skip 1 | `tests/test_h264clock.py:285`: now runs with a real libx264-generated POC-2 fixture; independently decoded and full TS path passes |
| Former skip 2 | `tests/test_h264clock.py:409`: now runs against the same fixture and passes its malformed B-slice/reordering rejection check |
| Initial sandboxed source run | Not a product failure: 14 local TCP/socketpair tests raised `EPERM`; rerun outside sandbox passed |
| Ruff check | PASS |
| Ruff format check on tracked project paths, excluding preserved untracked suffix test | PASS: 54 files already formatted |
| `compileall` | PASS |
| Deterministic bundle `--check` | PASS; reproduced SHA-256 above |
| `git diff --check` | PASS before report edits; rerun at finalization |
| Streamlink 8.6.2 plugin load | PASS: `streamlink --plugin-dir plugins --plugins` lists both `soop` and `soop_grid` |
| Bundle SHA256SUMS | PASS: verified from `dist/`; `soop_grid.py: OK` |

The project-local alternate FFmpeg executable could not be launched because its isolated runtime dependency set is incomplete (`libpulsecommon-16.1.so`, then `liblapack.so.3` were unavailable on its loader path). No package installation or network download was performed. The system FFmpeg 6.1.1 libx264 encoder now generates the POC-2 no-B fixture; its emitted SPS is checked for `pic_order_cnt_type=2`, zero reorder, and non-fixed VUI timing, and FFmpeg independently decodes it. The two encoder-dependent skips are therefore closed without relaxing assertions.

The supplemental test-fixture change does not alter production sources. The deterministic single-file bundle remains SHA-256 `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.

## Live and endurance stages

The first environment check looked only for process environment variables and incorrectly concluded that no test credentials were configured. A later permissions-safe check found the user's existing mode-0600 test configuration outside the repository; it was used only by the private harness, with values kept out of logs and reports. The user also confirmed an authorized test broadcast. The exact bundle hash above was copied into the isolated receiver plugin for the following tests.

| Stage | Outcome | Evidence / scope |
|---|---|---|
| Offline smoke | PASS | Source and bundle suites listed above; synthetic cases only. |
| Live 120 s pilot | PASS | Self-owned synthetic broadcast; exact bundle; 7,457 VCL / 5,808 AAC AUs form contiguous byte-identical source intervals; SPS/PPS identical; 7,371 pictures fully decoded; B pictures present; TS and timestamp checks pass. Source continued beyond receiver cutoff; event misses are proven right-censored tail only. |
| 10 min | PASS — receiver capture; publisher cleanup disclosed | Exact bundle; receiver exit 0 at 600 s; H.264 High, 1920×1080, POC type 0, B pictures; 36,284 VCL / 28,344 AAC AUs match contiguous source intervals; SPS/PPS identical; full TS/FFmpeg validation pass. 1,052,629 TS packets, continuity/PSI CRC/PCR regression errors 0, max PCR delta 17 ms, DTS regression 0. A/V 240 common events, added offset median 0.333 ms, max/p95 0.667 ms, measured drift 0.224 ppm over 602.3 s. |
| Looped-source seam smoke | REJECTED as an endurance fixture | RTMP input loop had a 4 ms audio timestamp overlap in the local reference and a 20.667 ms A/V offset jump at the seam despite Grid sequence continuity. Not attributed to the receiver. |
| 30 min | PASS WITH MEASURED EDGE LIMITS | Exact bundle; authorized self-owned non-looping 1080p60 H.264 B-frame + AAC-LC 48 kHz stereo broadcast; receiver and publisher exit 0; 1,800.24 s, StreamIO drain complete, emitted/read/accepted bytes equal (590,853,840), discarded/unaccepted 0. Grid sequence gaps/discontinuities 0; one Parent, no failover/recovery. Source/Grid contiguous identity: 108,115 VCL and 84,456 AAC AUs; SPS/PPS equal. Output TS: 3,144,607 packets, 3,602 valid PSI sections; 108,035 video PES / 3,519 audio PES; TS continuity, PSI CRC, PCR regressions, DTS regressions, duplicate PTS and PTS/DTS mismatches 0. Full FFmpeg H.264/AAC decode passes for 1,800.62 s video and 1,801.73 s audio. Independent TS/PES checker passes. First 80 captured video preroll chunks (492,902 bytes, before decodable IDR) are excluded; no interior/suffix coded video bytes are excluded. |
| 30 min A/V event sync | PASS FOR COMMON OVERLAP; strict full-edge gate not met | 1,929 common controlled flash/click events across 1,799.167 s; added offset median 0.333 ms, max/p95 0.667 ms; fitted drift −0.002615 ppm (−0.00157 ms per 600 s). Matched event IDs are contiguous over captured overlap; initial source event IDs 0–1 (video) / 0 (audio) precede receiver coverage and the finite source has a censored tail. Audio onset detector found 11 unmatched observed onsets versus 16 in the source/reference detector baseline; treated as detector artifacts, not hidden media loss, because AAC AUs are byte-identical. The original strict `validation-gate.json` remains `passed=false` due edge/detector coverage conditions; overlap timing metrics meet limits. |
| 2 h | NOT_TESTED — unavailable | User confirmed no test broadcast is currently available; remaining work is offline-only. |
| 6 h | NOT_TESTED — unavailable | User confirmed no test broadcast is currently available; remaining work is offline-only. |
| Endurance with controlled failures | NOT_TESTED | Clean 10 min run had no failover/recovery event, so recovery is not evidenced. |
| Source-relative sync/resource trend | VERIFIED_FOR_30_MIN_CLEAN_RUN | 361 samples / 5 s: RSS peak 59,364 KiB; FD peak 13; threads peak 3; 195.58 CPU seconds over 1,800.24 s. No recovery/failover event occurred in this clean run. |

Prior long-run and 30-minute reports concern other bundle hashes. They are useful historical evidence but do not pass the exact-candidate release gate.

## Result

This candidate passes the executed offline regression gates and has passed 120 s, 600 s, and 1,800 s authorized synthetic self-broadcast captures on the exact bundle. The 30 min receiver and publisher both exited cleanly. Coded media identity, TS/PES, independent timestamps, full decoding, EOF/drain, and source-relative A/V timing over the common event interval passed. Startup/finite-capture event edges remain measured exclusions; the strict full-coverage A/V gate is not green. No production code changed. The user has since confirmed no further test broadcast is currently available, so 2 h, 6 h, and controlled-failure live endurance remain untested. Stable remains **NO-GO**.

## Offline generated-media timeline soak — 2026-11-03

After the user confirmed that no authorized live test source is currently
available, ran `tools/offline_media_soak.py` on the code at HEAD
`b1adbfc419ce834315ddab3ea864ca3a1cc2d0f6`. No SOOP endpoint was contacted.
Environment: Linux 6.8.0-147-generic x86_64, Python 3.12.3, Streamlink 8.6.2,
FFmpeg/FFprobe 6.1.1-3ubuntu5; production bundle SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
The generated SPS was parsed; this FFmpeg/libx264 build emitted 320x180
progressive Baseline, POC Type 2, zero reorder.

| Synthetic media timeline | Wall time | Result |
|---|---:|---|
| 60 s | 3.856 s | PASS; 600 video AUs/VCL NALs and 2,814 AAC AUs preserved; 20,384 TS packets; continuity errors 0; PSI CRC errors 0; max PCR value gap 100 ms; EOF/drain and full FFmpeg decode passed; FD count 4 before/after; StreamIO peak buffer 42,112 bytes. |
| 600 s | 30.401 s | PASS; 6,000 video AUs/VCL NALs and 28,126 AAC AUs preserved; 203,076 TS packets; continuity errors 0; PSI CRC errors 0; max PCR value gap 100 ms; EOF/drain and full FFmpeg decode passed; FD count 4 before/after; StreamIO peak buffer 38,164 bytes. |
| 1,800 s | 89.335 s | PASS; 18,000 video AUs/VCL NALs and 84,376 AAC AUs preserved; 609,196 TS packets; continuity errors 0; PSI CRC errors 0; max PCR value gap 100 ms; EOF/drain and full FFmpeg decode passed; FD count 4 before/after; StreamIO peak buffer 48,880 bytes. |
| 7,200 s | 356.393 s | PASS; 72,000 video AUs/VCL NALs and 337,501 AAC AUs preserved; generated elementary inputs 404,199,257 bytes; output 458,091,516 bytes / 2,436,657 TS packets; continuity errors 0; PSI CRC errors 0; max PCR value gap 100 ms; EOF/drain and full FFmpeg decode passed; FD count 4 before/after; StreamIO peak buffer 49,444 bytes. |
| 21,600 s (first helper version) | 1,079.679 s | Historical PASS; see corrected bounded-helper run below. |
| 21,600 s (corrected helper) | 1,067.107 s | PASS; 216,000 video AUs/VCL NALs and 1,012,501 AAC AUs preserved; generated inputs 1,213,152,070 bytes; output 1,374,398,628 bytes / 7,310,631 TS packets; continuity errors 0; PSI CRC errors 0; max PCR value gap 100 ms; EOF/drain and full FFmpeg decode passed; FD count 4 before/after; StreamIO peak buffer 89,488 bytes. |

Output VCL and ADTS payload identities matched generated inputs. The 600 s
fixture's FFmpeg coverage-boundary offset change was 21.333 ms; the verifier
labels this as boundary coverage, not source-clock drift or perceptual sync.
The 1,800 s accelerated harness sampled RSS up to 301,156 KiB; the 7,200 s
run peaked at 1,082,268 KiB, the first 21,600 s helper peaked at 1,397,572 KiB,
and the corrected 21,600 s run peaked at 467,568 KiB. RSS includes the test
harness and generated data handling; it is not receiver-only leak/trend
evidence. The first smoke run exposed a test-tool
assumption error: libx264 emitted POC Type 2, while the helper expected Type 0
and used the wrong SPS result key. The helper was corrected to assert the
observed `poc_type=2`; production code did not change.

The corrected 21,600-second row is a six-hour *media timeline* processed in
1,067.107 seconds of wall time. It is not a six-hour live or wall-clock run. None of
these accelerated runs exercises SOOP, real-time pacing, Parent/Cache, network
failure, or source-relative sync. The user confirmed live tests are unavailable
for this continuation. Current-candidate live status remains NOT TESTED; 2 h,
6 h wall-clock, controlled-failure live endurance and Stable gates remain
unpassed.

The corrected helper now processes video fixtures in 10-minute chunks while
encoding AAC once for the continuous timeline, partitions ADTS only at frame
boundaries, and applies one wall-clock deadline to generation, StreamIO, and
verification. An attempted independently encoded AAC file per video chunk
accumulated encoder tail padding and correctly failed the track-coverage gate;
that fixture construction was replaced. A subsequent 300-second child timeout
was too short for the single six-hour AAC encode; the fixed per-child cap was
removed in favor of the overall 3,600-second limit. The corrected run above
then passed. These were offline harness defects, not production receiver
failures.

## Six-hour synthetic timeline and final offline regression — 2026-11-03

The original entry in this section was superseded by the corrected bounded
helper run below; retain the old source/bundle suite counts as historical.

The extended helper and six-hour synthetic run were performed from the
`0a981c3a28916d38221d0a4379f2ce714ca844c3` checkout with the worktree-only
helper change; production bundle SHA-256 remained
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`. The
21,600-second generated timeline passed in 1,079.679 wall seconds (details
above). It is accelerated offline media-time coverage, not wall-clock or live
endurance.

After that run, using the isolated FFmpeg 6.1.1-3ubuntu5 toolchain, Streamlink
8.6.2, and the permitted local loopback test environment:

* Source suite: **784 passed, 0 skipped**; untracked
  `tests/test_suffix_latejoin.py` explicitly excluded and untouched.
* Bundled parity suite: **775 passed, 0 skipped**; same exclusion.
* Ruff check passed; Ruff format check passed for 55 tracked source/test Python
  files (generated single-file distribution excluded); compileall, deterministic
  bundle check, manifest validation, and `git diff --check` passed.

No SOOP endpoint was contacted. This adds offline synthetic evidence only.
Live 2 h/6 h wall-clock runs, source-relative long-run sync, and live controlled
recovery remain NOT_TESTED; Stable remains **NO-GO**.

## Corrected soak tool and final offline regression — 2026-11-03

The earlier 21,600-second entry above is superseded by the corrected tool
result below. Code was run from the worktree based on commit
`93e53147f3cf2a43c9a08133c0c416d478dfb3c5`; only the offline helper/tests/docs
changed, and production bundle SHA-256 remains
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

* Six-hour synthetic media timeline: **21,600 s in 1,067.107 wall seconds**.
  POC-2 zero-reorder 320x180 Baseline video; AAC-LC 48 kHz.
* Input/output identity: 216,000 VCL NALs, 1,012,501 ADTS AUs;
  VCL SHA-256 `fe2c226b284a8695c5d586e8ea7363ba186d014835da2f252f98eec8ca812cc9`;
  AAC SHA-256 `af7003b104b201918ba2740a62fe1c30aeb39c07d8147e6fc4db392284421062`.
* Output: 1,374,398,628 bytes, SHA-256
  `eb7393bb04bf0902a06af4d0a98cfeaa73d89d9d86914aba2cbc6cf5955852fb`,
  7,310,631 TS packets; continuity errors 0, PSI CRC errors 0, max PCR value
  gap 100 ms. Full FFmpeg decode, StreamIO accounting, EOF/drain passed; FD
  count 4 before/after; peak StreamIO buffer 89,488 bytes.
* Sampled process RSS peak: 467,568 KiB, including the runner and fixture
  handling; not receiver-only or leak-trend evidence. Decoded A/V boundary
  coverage change was 21.333 ms, not source-clock drift/perceptual sync.
* Final source tests before the deadline child-termination assertion: **787
  passed, 0 skipped**. Bundled parity: **778 passed, 0 skipped**. A separate
  focused rerun after adding that assertion passed 4 soak-helper tests.

The timeout regression creates a slow local child fixture, verifies the
expected `TimeoutExpired`, and confirms it terminates in under two seconds.
Before the additional AAC E2E fixture, full offline source tests were **788
passed, 0 skipped**; bundled parity was **779 passed, 0 skipped**. The
preserved untracked suffix test was excluded and untouched.

The focused offline recovery/StreamIO/startup-retry/Parent-fault/transport
group then passed **139 tests in 7.99 s**, with the isolated FFmpeg fixture
environment enabled (zero skips). It includes synthetic and local loopback
fault tests; it is not evidence for remote SOOP failure timing.

An additional `test_poc_type_streamio_44100_stereo_aac_identity_and_decode`
fixture now covers 30-frame video for POC 0/1/2 with 43 AAC-LC 44.1 kHz stereo
access units, packet-interleaved by media timestamp. Type 0/1 composition
follows FFprobe display order and the parsed reorder bound; Type 2 uses decode
order. Demuxed VCL and AAC payloads
matched, FFprobe confirmed 320x180 video and 44.1 kHz stereo audio, full
FFmpeg decode and EOF/drain passed. The first single-Type fixture attempt was
initially too short and correctly failed the track-coverage gate; the final
43-AU duration matched the video timeline. Full source/bundle regressions then
passed **791/782**, zero skipped. Production bundle bytes remain unchanged.

Ruff, tracked-file format, compileall, deterministic bundle check, SHA256
manifest verification, Streamlink plugin discovery, and `git diff --check`
passed for the final test changes. Live and wall-clock endurance remain
NOT_TESTED.

This is accelerated synthetic media-time validation, not live or six-hour
wall-clock endurance. Live 2 h/6 h, real-time sync, Parent/Cache network
recovery and controlled live failures remain NOT_TESTED; Stable remains
**NO-GO**.

## Wall-clock-paced offline smoke — 2026-11-03

The soak helper gained an opt-in `--realtime` mode. It waits against the
synthetic Grid timestamps through the existing receiver cancellation event;
the output remains offline-generated media and exercises no SOOP or Parent
network. A 60-second POC-2/no-reorder 320x180 Baseline + AAC-LC 48 kHz mono
smoke completed in **62.798 s**. It preserved 600/600 video AUs and
2,814/2,814 AAC AUs, produced 20,384 TS packets, had zero TS continuity and
PSI CRC errors, maximum PCR value gap 100 ms, and passed full FFmpeg decode,
StreamIO byte accounting, EOF and drain. Peak StreamIO buffer was 13,536 B.
The sampled process RSS was 53,248 / 52,708 / 53,248 KiB (first/last/peak);
sampled FD count was 7 / 4 / 7 with process FD count 4 before and after; and
sampled thread count was 2 / 1 / 2. These process samples include the test
harness and transient file/worker activity and are only a one-minute smoke,
not evidence of long-term leak stability. The synthetic decoded boundary
coverage delta was 32 ms; the validator classifies it as boundary coverage,
not source-clock drift or perceptual synchronization.

The 60-second run verified pacing and cancellation wiring only. It does not
upgrade the earlier accelerated six-hour media timeline to wall-clock
endurance and does not replace live Grid tests. Current-source 2 h/6 h
wall-clock runs, live A/V marker sync, Parent/Cache recovery over SOOP, and
live controlled-failure endurance remain **NOT TESTED** because the user
confirmed no test broadcast is available. Stable remains **NO-GO**.

The paced-runner follow-up was tested from base commit
`8ee10fc427f33b4f90aca4dd09638cb77cc8cbed`; only the offline soak helper,
its helper tests, and this report/plan changed. Source pytest: **793 passed,
0 skipped**; static-bundle parity: **784 passed, 0 skipped**. Ruff check,
tracked project Python Ruff format, compileall, deterministic bundle check,
manifest verification, and `git diff --check` passed. Production bundle bytes
remain unchanged at SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
`tests/test_suffix_latejoin.py` was excluded, left untouched, and unstaged.

## Two-hour wall-clock-paced offline soak — 2026-11-03

Ran the committed tool from source HEAD `2e88360eebe860c7208e86e99845b938dbe005c4`;
production bundle SHA-256 was
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
Environment remained Linux x86_64, Python 3.12.3, Streamlink 8.6.2 and
FFmpeg/FFprobe 6.1.1-3ubuntu5. A 7,200-second generated POC-2 zero-reorder,
320x180 Baseline video + AAC-LC 48 kHz mono timeline was fed through the
production MediaSink/StreamIO/MPEG-TS path paced to wall-clock timestamps. It
completed in **7,426.947 s** including generation and verification.

* Input/output identity: 72,000/72,000 VCL AUs and 337,501/337,501 AAC AUs;
  VCL SHA-256 `b50b5e3384b07a81891f6c689a3b63f0efc14075603d0edd16376a44cf2b5e59`;
  AAC SHA-256 `fd32f6c8ad9d695e82093d3869262cd23dc76c31c7c46ce736754be5fc82b18d`.
* Output: 458,133,252 bytes, 2,436,879 TS packets; continuity errors 0,
  PSI CRC errors 0, maximum PCR value gap 100 ms; full FFmpeg decode passed.
  StreamIO byte accounting, EOF and drain passed; peak buffer 27,636 bytes.
* 241 resource samples: process RSS first/last/peak 213,464/202,620/293,488
  KiB; FDs 7/4/7, with process count 4 before and after; threads 2/1/2.
  These are harness-inclusive samples. The 21.333 ms decoded coverage-boundary
  delta is not source-clock drift or perceptual sync.

This verifies a two-hour **local generated-media paced pipeline** on the
current production bundle. It has no SOOP network, Parent/Cache, source-side
clock or sync markers, broadcast quality negotiation, or injected failures;
it does not pass the campaign's two-hour live gate. The preserved untracked
suffix experiment remained untouched.

## Six-hour wall-clock-paced offline soak — 2026-11-03

Ran the same committed harness and production bundle as the two-hour offline
run: source HEAD `2e88360eebe860c7208e86e99845b938dbe005c4`, bundle SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`, Linux
x86_64, Python 3.12.3, Streamlink 8.6.2, FFmpeg/FFprobe 6.1.1-3ubuntu5. The
21,600-second generated POC-2 zero-reorder 320x180 Baseline + AAC-LC 48 kHz
mono timeline completed in **22,273.389 s** (6 h 11 min 13 s), including
fixture generation and full-file verification.

* Input/output identity: 216,000/216,000 VCL AUs and 1,012,501/1,012,501 AAC
  AUs. VCL SHA-256 `fe2c226b284a8695c5d586e8ea7363ba186d014835da2f252f98eec8ca812cc9`;
  AAC SHA-256 `af7003b104b201918ba2740a62fe1c30aeb39c07d8147e6fc4db392284421062`.
* Output: 1,374,398,628 bytes, SHA-256
  `eb7393bb04bf0902a06af4d0a98cfeaa73d89d9d86914aba2cbc6cf5955852fb`,
  7,310,631 TS packets. Continuity errors 0, PSI CRC errors 0, max PCR value
  gap 100 ms; FFprobe, full FFmpeg decode, payload identity, byte accounting,
  EOF/drain all passed. Peak StreamIO buffer: 62,604 bytes.
* 721 resource samples: RSS first/last/peak 213,572/114,000/295,924 KiB;
  sampled FD first/last/peak 7/4/7, process FD count 4 before and after;
  sampled thread first/last/peak 2/1/2. Samples include the Python harness,
  fixture processing and transient worker/file activity, not receiver-only
  memory. Decoded A/V coverage-boundary delta was 21.333 ms; this is not
  source-clock drift or perceptual synchronization.

This is six hours of **local synthetic wall-clock-paced MediaSink/StreamIO
pipeline** operation. It does not exercise the SOOP protocol, authentication,
Parent/Cache/failover, production Streamlink capture from a real stream,
source-relative sync markers, quality negotiation or controlled failures.
Therefore the six-hour live/Grid Stable gate remains NOT TESTED even though
the local paced soak passed. No SOOP endpoint was contacted.

## Current-HEAD offline regression and local fault checks — 2026-11-03

After documentation commit `55c2031f4f204f168e61df4d76f70cf3eacb7e92`,
the full tracked source suite passed **793 tests, zero skipped** and static
bundle parity passed **784 tests, zero skipped**. The preserved untracked
`tests/test_suffix_latejoin.py` was excluded and not modified. The source run
included loopback protocol framing, identity-probe and Parent recovery cases;
the isolated real loopback Parent disconnect/Cache overlap recovery test also
passed on its own. These tests use local synthetic peers and do not contact
SOOP.

An initial sandboxed attempt reported 14 `EPERM` failures because this
environment blocks local socket creation. The same full suite was rerun with
permission for local test sockets and passed. Ruff check, Ruff format check
for tracked Python files, compileall, deterministic bundle `--check`, bundle
SHA manifest, `git diff --check`, and Streamlink 8.6.2 version/plugin test
coverage passed. Production bundle SHA remains
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

This strengthens current-HEAD offline regression and local fault-injection
evidence. It does not establish SOOP live/Parent behavior, current-build
source-relative synchronization, or live 2 h/6 h endurance. Stable remains
**NO-GO**.

## Packaging build compatibility — 2026-11-03

A clean wheel-build check exposed a metadata/backend mismatch: `pyproject.toml`
used PEP 639 `project.license` SPDX syntax and `project.license-files`, while
the declared backend floor was setuptools 68. The environment's pinned 68.1.2
rejected both fields. [Setuptools' PEP 639 migration guide](https://setuptools.pypa.io/en/stable/userguide/license_migration.html)
documents support starting at 77.0.0;
the build requirement was raised to `setuptools>=77` in commit
`62e365f`.

With build isolation, wheel creation and installation into a temporary target
passed. The installed `soop_grid` package imported from that target, and
Streamlink 8.6.2 loaded the sideloaded plugin with `plugins.load_path()`,
resolved a fixture SOOP URL and enumerated its Grid stream. Wheel metadata
contained `License-Expression: AGPL-3.0-only` and the packaged `LICENSE`.
After the packaging change, source tests passed **793/0 skipped** and bundle
parity passed **784/0 skipped**. Ruff, format, compileall, deterministic
single-file bundle check and manifest passed. Production bundle SHA remained
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

This fixes clean build/install compatibility. It does not change runtime
compatibility or any SOOP live/endurance gate; those remain separately
classified in the matrix.

## Offline-only continuation — 2026-11-03

The user confirmed that no authorized test broadcast is currently available;
only offline verification can continue. A stdlib-only packaging regression
test now guards the `setuptools>=77` floor required by the project's PEP 639
SPDX/license-file metadata. The test initially caught its own version-tuple
normalization bug, which was corrected before the final run.

At source HEAD `f45c25e751107bdaeb5d1ddeaa94238b057b81ec`, source pytest passed
**794 tests, 0 skipped** and static bundle parity passed **785 tests, 0
skipped**, excluding the preserved untracked `tests/test_suffix_latejoin.py`.
Ruff check/format, compileall, deterministic bundle `--check`, manifest
verification, and `git diff --check` passed. Bundle SHA-256 remains
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`; the
new test and report do not alter production bundle bytes.

This adds offline regression evidence only. No SOOP/Grid session, source-
relative A/V test, live fault recovery, or exact-candidate live 2 h/6 h run
was possible. Campaign remains **PARTIAL** and Stable remains **NO-GO**.

## Local Parent-wire POC integration — 2026-11-03

The POC Type 0/1/2 synthetic fixture test now feeds its independently decoded
H.264/AAC media through a local fake Parent socket using the real Parent frame
parser and `receive_media()` control flow before `MediaSink`/`StreamIO`/TS.
The exercised request sequence is `CB2E`, `CB2F`, `CB30`, `CB2B`; server
responses are fragmented to exercise `read_frame()`. All 9 POC E2E cases
passed, including TS probing, complete FFmpeg decode, and H.264 VCL/AAC AU
payload identity. The complete source suite passed **794/0 skipped** and
bundle parity passed **785/0 skipped**. This is a local protocol fixture, not
a SOOP connection or Native Grid service validation. Production bundle SHA
remains `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

## Parent-wire malformed-AU fault injection — 2026-11-03

The POC 0/1/2 E2E now has valid and malformed cases through a local fake
Parent socket, production frame parsing and `receive_media()`, `MediaSink`,
`StreamIO`, and TS output. The malformed case sets `forbidden_zero_bit` on
VCL AU 6. All three POC types fail closed with `h264_nal_header_invalid`;
the malformed AU is absent from the emitted VCL prefix, EOF/drain is not
reported complete, `CB2B` is not sent, and the local socket is closed. Valid
cases retain full decode and coded-media identity checks. This is local
protocol fault injection, not an SOOP service or live recovery test.

The POC E2E module passed **12 tests**. FFprobe packet checks also confirmed
increasing video DTS, unique video PTS, increasing AAC PTS, and the first
displayed-video/AAC PTS aligned to the constructed shared start within one
90 kHz tick for each type. The separate 44.1 kHz stereo path has the same
checks across POC 0/1/2 and checks all 43 AAC packet PTS values against the
rational sample clock within one 90 kHz tick; those targeted tests passed
3/3. This is timestamp mapping evidence, not perceptual sync or drift
measurement. At that earlier run, source pytest passed **797/0 skipped** and
static bundle parity passed **788/0 skipped**. The follow-up run below includes
one additional harness regression test. Production bundle SHA-256 remains
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
No authorized SOOP test broadcast is available, so campaign status remains
**PARTIAL** and Stable remains **NO-GO**; current-build live and live 2 h/6 h
gates remain NOT TESTED.

## POC-0 B-picture generated-media timeline soak — 2026-11-03

The offline soak helper gained an opt-in `--b-frames` path. It requests
libx264 Main with B pictures, then checks the emitted SPS is POC Type 0, uses
FFprobe coded/display order to derive nonnegative Grid composition offsets,
and requires actual B-picture frames before running the unchanged production
MediaSink/StreamIO/TS path. The default remains the original no-B POC-2 mode.
The helper serializes those offsets in the same Parent media-body field; an
offline unit test covers that field.

Runs on worktree based at `e7a1044450ed0d1552261bc639bfbbd1d2dc6779` with
production bundle SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`:

| Synthetic media timeline | Wall time | Verified input/output | TS / decode / drain | Resource sample scope |
|---|---:|---|---|---|
| 10 min | 32.546 s | POC 0, reorder 1, 3,960 B pictures; 6,000/6,000 VCL AUs; 28,126/28,126 AAC AUs | 203,186 TS packets; continuity/PSI errors 0; PCR max gap 100 ms; full decode and EOF/drain | RSS first/last/peak 165,076/149,184/165,076 KiB; FDs 4/4; threads 2/1 |
| 30 min | 95.423 s | POC 0, reorder 1, 11,880 B pictures; 18,000/18,000 VCL AUs; 84,376/84,376 AAC AUs | 609,552 TS packets; continuity/PSI errors 0; PCR max gap 100 ms; full decode and EOF/drain | RSS first/last/peak 217,044/204,176/231,808 KiB; FDs 4/4; threads 2/1 |
| 2 h | 377.871 s | POC 0, reorder 1, 47,520 B pictures; 72,000/72,000 VCL AUs; 337,501/337,501 AAC AUs | 2,438,199 TS packets; continuity/PSI errors 0; PCR max gap 100 ms; full decode and EOF/drain | RSS first/last/peak 218,452/204,624/291,300 KiB; FDs 4/4; threads 2/1 |
| 6 h | 1,139.226 s | POC 0, reorder 1, 142,560 B pictures; 216,000/216,000 VCL AUs; 1,012,501/1,012,501 AAC AUs | 7,314,591 TS packets; continuity/PSI errors 0; PCR max gap 100 ms; full decode and EOF/drain | RSS first/last/peak 221,704/207,996/468,660 KiB; FDs 4/4; threads 2/1 |

All four were accelerated generated-media timelines (`realtime_paced=false`),
not wall-clock runs or SOOP/Grid reception. Sampled resources include the
harness and fixture generation; they are not receiver-only leak measurements.
The verifier's 21.333 ms decoded coverage-boundary difference is a finite
track-span metric, not source-clock drift or perceptual synchronization. The
six-hour result adds long POC-0 B-frame composition/segment-boundary and coded
payload identity evidence, but does not satisfy the live 6 h release gate.

Final offline validation for this follow-up: source pytest **798 passed, 0
skipped**; bundle parity **789 passed, 0 skipped**; Ruff check and format,
compileall, deterministic bundle check, SHA-256 manifest, and `git diff
--check` passed. The bundle is unchanged at
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

### Wall-clock-paced 10-minute POC-0 B-frame run

After the accelerated runs, the same generated POC-0 B-frame mode completed a
600 s **wall-clock-paced offline** timeline in 621.127 s. This adds scheduler
and timestamp pacing coverage, but it still uses generated Parent-media
bodies on the local production sink path and is not a SOOP session.

* SPS: 320x180, POC 0, `max_num_reorder_frames=1`; 3,960 decoded B pictures.
* H.264: 6,000 input and output VCL AUs; input/output identity verified.
* AAC: 28,126 input/output ADTS frames at 48 kHz; identity verified.
* TS: 203,186 packets, zero continuity and PSI CRC errors, maximum PCR value
  gap 100 ms; full FFmpeg decode and StreamIO EOF/drain passed.
* Output: 38,198,968 bytes; peak bounded buffer 23,124 bytes.
* Resource samples: RSS first/last/peak 165,012/149,156/165,016 KiB; FD
  first/last/peak 7/4/7; threads 2/1/2.
* Decoded track-coverage boundary difference: 21.333 ms. This is not
  source-clock drift or perceptual A/V synchronization.

This evidence is stronger than an accelerated media-time run for local pacing,
but it does not exercise SOOP network timing, Parent recovery, long-running
receiver-only resource behavior, or the live release gates.

## POC-1 B-picture timeline — 2026-11-04

The soak harness now has a separate `--poc1-b-frames` mode. It generates a
POC-0 x264 B-picture stream, applies the repository's test-only SPS/slice POC
header transform to Type 1, validates the resulting SPS and FFprobe display
order, then feeds that transformed file through the production sink. The
fixture is derived, not emitted by a Type-1-capable encoder; FFmpeg independently
decodes the resulting stream. This validates the Type-1 state/timeline path on
that constrained progressive subset, not arbitrary Type-1 encoder output.

A first run exposed that the harness read the original Type-0 path rather than
the transformed Type-1 path. The exact VCL identity assertion caught the error;
the chunk now retains the transformed path. The regression test verifies the
actual Type-1 SPS, presence of B pictures, full output AU counts, and drain.

On bundle SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`, the
10-minute wall-clock-paced synthetic Type-1 run completed in 681.603 s:

* SPS: 320x180, POC 1, reorder bound 1; 3,960 B pictures.
* H.264: 6,000/6,000 VCL AUs input/output; coded payload identity passed.
* AAC: 28,126/28,126 ADTS frames at 48 kHz; identity passed.
* TS: 203,218 packets; continuity/PSI errors 0; max PCR value gap 100 ms.
* FFmpeg full decode and StreamIO EOF/drain passed; output 38,204,984 bytes.
* Bounded buffer peak 20,680 bytes; RSS first/last/peak 190,788/175,944/
  190,792 KiB; FD 7/4/7; threads 2/1/2.
* Decoded coverage boundary difference 21.333 ms is not source-relative drift
  or perceptual synchronization.

This is a paced local generated-media test, not SOOP/Grid E2E or a live
endurance result. The complete source and bundle suites subsequently passed
800 and 791 tests respectively, with zero skips.

## POC-0 reference B-picture timeline — 2026-11-04

The bounded soak now includes `--reference-b-frames`, generating an x264 Main
stream with `b-pyramid=normal`. Before sending it through the sink, the helper
parses every VCL slice and requires reference B slices; it also verifies SPS
POC Type 0 and `max_num_reorder_frames >= 2`. The one-minute fixture test
passed independently.

The 10-minute wall-clock-paced run completed in 623.812 s:

* SPS: 320x180, POC 0, reorder bound 2; 4,440 B pictures and 1,500 reference-B
  VCL slices observed.
* H.264: 6,000/6,000 VCL AUs input/output; identity passed.
* AAC: 28,126/28,126 ADTS frames at 48 kHz; identity passed.
* TS: 203,573 packets; continuity/PSI errors 0; max PCR value gap 100 ms.
* Full FFmpeg decode and StreamIO EOF/drain passed; output 38,271,724 bytes.
* Bounded buffer peak 23,876 bytes; RSS first/last/peak
  189,568/175,452/189,572 KiB; FD 7/4/7; threads 2/1/2.
* Decoded coverage boundary difference 21.333 ms is not source-clock drift or
  perceptual sync.

This adds paced local coverage for a deeper reorder/reference-B subset. It is
not SOOP reception, source-relative A/V synchronization, network recovery, or
receiver-only resource trending.

## POC-1 reference B-picture timeline — 2026-11-04

Added a separate `--poc1-reference-b-frames` mode. It generates an x264
POC-0 B-pyramid stream, transforms its POC syntax to Type 1 using the existing
test-only fixture transform, and verifies the transformed SPS and every VCL
slice before feeding it to the production sink. The fixture has reorder bound
2 and reference-B slices. FFmpeg independently decodes the transformed input
and output. This is a constrained transformed Type-1 fixture, not a native
Type-1 encoder output or SOOP transmission.

The targeted one-minute sink regression passed, followed by a 600-second
wall-clock-paced offline timeline on the then-current source HEAD
`f7776b263722fa748244727f30ae8094bd4f48bf` and production bundle SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`:

* SPS: 320x180, POC 1, reorder bound 2; 4,440 B pictures and 1,500
  reference-B VCL slices.
* H.264: 6,000 input/output VCL NALs, exact coded-payload identity.
* AAC: 28,126 input/output ADTS frames at 48 kHz, exact identity.
* TS: 203,597 packets; continuity and PSI CRC errors 0; maximum PCR value
  gap 100 ms. Full FFmpeg decode and StreamIO EOF/drain passed.
* Output: 38,276,236 bytes; peak bounded buffer 20,680 bytes.
* Resource samples: RSS first/last/peak 190,648/177,444/190,652 KiB;
  FD first/last/peak 7/4/7; threads 2/1/2.
* Decoded coverage-boundary difference 21.333 ms is not source-relative drift
  or perceptual A/V synchronization.

This adds a paced local sink-path result for transformed Type-1 reference-B
syntax. It does not validate native Type-1 encoder output, SOOP Grid delivery,
network recovery, source-relative sync, or live 2 h/6 h endurance.

After adding per-segment FFmpeg decoded-frame identity checks between each
POC-0 source and POC-1 transformed stream, source commit `1ee8729` completed
an accelerated 7,200-second synthetic timeline in 1,139.537 wall seconds on
the unchanged production bundle SHA above. All 12 segments (72,000 frames
total) passed source/transformed decoded-frame hash identity before the
transformed stream entered the sink:

* SPS: 320x180, POC 1, reorder bound 2; 53,280 B pictures and 18,000
  reference-B VCL slices.
* H.264: 72,000/72,000 input/output VCL NALs, identity passed.
* AAC: 337,501/337,501 ADTS frames at 48 kHz, identity passed.
* TS: 2,443,131 packets; continuity/PSI CRC errors 0; maximum PCR value gap
  100 ms. Full FFmpeg decode and StreamIO EOF/drain passed.
* Output: 459,308,628 bytes; peak bounded buffer 55,272 bytes.
* Harness-inclusive RSS first/last/peak 167,180/155,324/240,000 KiB;
  FD first/last/peak 7/4/7; threads 2/1/2.
* Peak bounded StreamIO buffer: 97,572 bytes.
* Decoded coverage-boundary difference 21.333 ms is not source-relative drift
  or perceptual sync.

This is an accelerated media-time test. POC-1 reference-B 2-hour wall-clock
operation, 6-hour operation, native Type-1 encoder output and SOOP/Grid
reception remain untested.

### Offline regression after adding the Type-1 reference-B mode

With the local FFmpeg/FFprobe toolchain explicitly configured and the preserved
untracked `tests/test_suffix_latejoin.py` excluded, the complete source suite
at commit `42c0969` passed **803 tests** and bundled parity passed **794 tests**, both with zero
skips. The first sandboxed source run failed 14 socketpair/loopback tests due
to sandbox `Operation not permitted`; the same full suite passed after running
its synthetic local-socket tests in the authorized environment. A first bundle
run without FFmpeg environment variables had 75 fixture-related skips; the
configured rerun above passed with zero skips.

Ruff lint passed for `tests`, `tools`, and `plugins`; Ruff format check passed
for the two changed Python files. A repository-wide format check reports only
the pre-existing untracked `tests/test_suffix_latejoin.py` as unformatted, and
that user-owned file was left untouched. `compileall`, deterministic bundle
check, bundle SHA manifest, and `git diff --check` passed. Streamlink 8.6.2
listed `soop_grid` when run with the project root on `PYTHONPATH`; without that
path, the uninstalled checkout could not resolve the package. Production
source and bundle were not changed by this harness-only addition; bundle SHA-256
remains `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

The user confirmed that no authorized test broadcast is currently available.
Therefore current-candidate SOOP/Grid E2E, source-relative A/V sync, controlled
live recovery, and 2 h/6 h live endurance remain **NOT TESTED**. Stable remains
**NO-GO**.
