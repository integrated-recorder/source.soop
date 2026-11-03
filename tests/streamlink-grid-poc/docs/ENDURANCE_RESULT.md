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

Output VCL and ADTS payload identities matched generated inputs. The 600 s
fixture's FFmpeg coverage-boundary offset change was 21.333 ms; the verifier
labels this as boundary coverage, not source-clock drift or perceptual sync.
The 1,800 s accelerated harness sampled RSS up to 301,156 KiB; the 7,200 s
run peaked at 1,082,268 KiB. The harness retains generated elementary streams
and parsed AUs in memory, so these figures measure the test harness as well as
the receiver and are not receiver leak/trend results. The first smoke run exposed a test-tool
assumption error: libx264 emitted POC Type 2, while the helper expected Type 0
and used the wrong SPS result key. The helper was corrected to assert the
observed `poc_type=2`; production code did not change.

These accelerated runs are not live, real-time, Parent/Cache, network-failure
or 2 h/6 h evidence. The user's latest confirmation makes live tests unavailable
for this continuation. Current-candidate live status remains NOT TESTED; 2 h,
6 h, controlled-failure live endurance and Stable gates remain unpassed.
