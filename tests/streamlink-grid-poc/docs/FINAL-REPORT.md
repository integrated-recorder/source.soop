# Current offline compatibility update — 2026-11-03

## ITU-T H.264 V16 SEI boundary review

Reviewed the in-force H.264 V16 (06/2026) public change summary and Annex D
SEI dispatch/processing-order clauses. V16's H.264 layer names payload types
213–215 for processing-order, processing-order-nesting and encoder-optimization
information. The receiver's generic bounded SEI envelope already skips these
non-timing payload bodies; it does not interpret their H.274/VSEI semantics.
Added six source regressions for bounded opaque handling, AU byte preservation
and truncated-envelope rejection. These synthetic payloads test the envelope,
not VSEI semantic conformance. A targeted V15/V16 text comparison of the
frame-number, Type-2 restriction and MMCO-5 clauses exercised by the current
subset found the relevant rules unchanged; it did not cover the full
DPB/reference-list/HRD text or every minor correction. See
`H264_REFERENCE_CONFORMANCE.md`.

* Targeted new tests: **6 passed**.
* A seeded TS-scanner mutation regression now corrupts up to four bytes in each
  of 64 generated transport streams and checks bounded scan results and full
  input hashing. This is a deterministic mutation smoke test, not coverage-
  guided fuzzing.
* A second fixed-seed test mutates 1–4 bytes in each of 1,024 valid synthetic
  SPS/PPS/IDR access units while preserving Annex-B start codes. The H.264
  parser either accepts or returns its documented `GridError`; it produced no
  unexpected exception. This is bounded near-valid mutation testing, not
  coverage-guided fuzzing or bitstream conformance proof.
* A third fixed-seed test mutates 1–4 bytes in 1,024 variants of eight real
  FFmpeg-generated ADTS frames. Accepted parses preserve exact frame
  concatenation, bounded frame count, sample totals and rational duration;
  malformed inputs use `GridError`. This checks framing arithmetic, not AAC
  payload decoding or CRC validity.
* A repeated StreamIO lifecycle test ran 64 synthetic sessions through
  open/read/EOF/drain/close. Every byte was accounted for, all receiver workers
  exited, and Linux FD count returned to baseline. This is a lifecycle smoke,
  not a long-duration RSS or live transport endurance result.
* Changes are tests and documentation only; production source and bundle are
  unchanged. Full source: **784 passed, 0 skipped**; bundled parity: **775
  passed, 0 skipped**. The source count includes the 9 single-file construction
  tests. Bundle SHA-256 remains
  `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
* Ruff check/format (tracked Python sources; generated bundle and preserved
  untracked suffix experiment excluded), compileall, deterministic bundle
  check, SHA manifest, source/single-file Streamlink 8.6.2 discovery and
  `git diff --check` passed. The first sandboxed full run had 14 loopback
  `EPERM` failures; rerunning with local socket permission passed. No SOOP
  endpoint was contacted.
* Campaign remains **PARTIAL**; 2 h, 6 h and live controlled-failure stages
  remain **NOT TESTED**, and Stable remains **NO-GO**.

## Additional parser boundary fix — current candidate

The H.264 AU walker previously validated headers only when it parsed that
NAL's payload syntax. An invalid AUD could therefore pass through beside an
accepted picture. Common header semantics are now validated for each NAL before
type dispatch: forbidden bit, unspecified type 0, and the defined
`nal_ref_idc` constraints for IDR/SPS/PPS/SEI/AUD/end/filler NALs. Valid AUD
controls remain accepted and media bytes are not rewritten.

* Bundle SHA-256: `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
* Tested source commit: `51a5a157a1269c00a2a952d5ad0dacefed35ef7e`; subsequent branch commits recorded in this report are documentation-only.
* Source: **774 passed, 0 skipped**; bundled suite: **765 passed, 0 skipped**;
  standalone single-file tests: **9 passed**.
* A fixed-seed 768-input parser robustness smoke test exercises malformed media and H.264 input; it found no unexpected Python exceptions. This is not coverage-guided fuzzing.
* Ruff check/format, compileall, deterministic build, SHA manifest, Streamlink
  8.6.2 plugin discovery and `git diff --check` pass.
* Exact-candidate regression was rerun after restoring an isolated Python 3.12
  environment and configuring FFmpeg/FFprobe: source **774 passed, 0 skipped**
  (57.61 s), bundled parity **765 passed, 0 skipped** (52.91 s). Ruff,
  compileall, deterministic bundle, SHA manifest, Streamlink 8.6.2 discovery,
  and diff checks passed. The first sandbox attempt had local-socket EPERM and
  FFmpeg-path skips; the successful rerun allowed local sockets and supplied
  the tool paths. No SOOP endpoint was contacted.
* User confirmed offline-only: no new live, 2 h, 6 h or controlled live-failure
  run. Campaign remains **PARTIAL**; Stable remains **NO-GO**.

---

## Historical MMCO-5 candidate supplement — source `c149834` / bundle `00af277`

This supplement applies to source commit `c149834f6ad98cdaac52b6559b5067e09efa4fcf` and bundle SHA-256 `00af27789d671d5230499c551bbd7c49f27727585b3b6b57faabac05ae886cef`, based on `b070755ed1f1593714575c3813ace1bc64da221e`. The older campaign report below remains artifact-scoped and is not overwritten.

* Corrected H.264 POC Type 0 MMCO-5 state: after the current picture's order counts are normalized, the next picture uses prior `PicOrderCnt` state `(MSB, LSB)=(0,0)`. Types 1/2 reset prior frame-number/offset state. Duplicate MMCO-5 operations in one marking list fail closed.
* Added generated, independently decoded MMCO-5 bitstreams for POC 0/1/2 in a narrow progressive CAVLC/no-B/one-reference subset. All pass production MediaSink/StreamIO/MPEG-TS, preserve VCL NAL bytes, fully decode and drain EOF. This is offline subset evidence only; no live broadcast was available.
* Source suite: **771 passed, 0 skipped**. Bundle suite: **762 passed, 0 skipped** on the final bundle; single-file construction/loading tests: **9 passed**. Ruff check/format, compileall, deterministic bundle check, SHA manifest, `git diff --check`, and Streamlink 8.6.2 discovery of both `soop` and `soop_grid` passed.
* User confirmed there is currently no authorized test broadcast to use. No new live, 2-hour, 6-hour or controlled live-failure test was run. Historical 30-minute evidence applies to bundle `5c1657d5…`, not this candidate.

**Current campaign status: PARTIAL. Stable: NO-GO.** Offline source/bundle regression and artifact checks pass; live/endurance work remains unavailable. See `ENDURANCE_RESULT.md`, `COMPATIBILITY_MATRIX.md`, and `RELEASE_READINESS.md`.

---

# Comprehensive compatibility campaign — 2026-11-03 final update

This update applies to code candidate `b070755ed1f1593714575c3813ace1bc64da221e`
and bundle SHA-256
`5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.
Documentation-only commits may advance Git HEAD without changing the tested
bundle.

* Supplemental offline: source 767 passed / 0 skipped; bundle 758 passed /
  0 skipped. The two POC-2 tests formerly skipped for lack of `libopenh264`
  now use a verified libx264 fixture. Ruff, format, compileall, deterministic bundle/SHA, Streamlink
  8.6.2 plugin discovery and diff checks passed. The pre-existing untracked
  `tests/test_suffix_latejoin.py` remains untouched and uncommitted.
* Exact-bundle authorized synthetic self-broadcast: 120 s, 600 s and 1,800 s
  receiver runs exited cleanly. The 30 min receiver and publisher both exited
  0; EOF/drain completed with 590,853,840 emitted/read/accepted bytes and zero
  discarded/unaccepted bytes.
* The 30 min capture contains H.264 High 1920x1080 60 fps, POC type 0, B
  pictures, and AAC-LC 48 kHz stereo. Source/Grid identity has a contiguous
  match for 108,115 VCL NAL units and 84,456 AAC AUs; SPS/PPS sets are equal.
  Grid sequence gaps, duplicates, missing frames, Cache recovery failures,
  Parent failover attempts, and continuity discontinuities are zero.
* Full 3,144,607-packet TS validation passed: 3,602 PSI sections CRC-valid,
  108,035 video PES, 3,519 audio PES, zero TS continuity/PSI CRC/PCR regression,
  zero PTS/DTS mismatch, duplicate video PTS or non-increasing DTS. FFmpeg
  decoded the entire 1,800.62 s video and 1,801.73 s AAC output without errors;
  an independent Grid-wire/TS/PES checker also passed. It measured 80 captured
  pre-IDR video preroll chunks (492,902 bytes) as prefix exclusions; no interior
  or suffix video chunks were excluded.
* Source-relative A/V marker timing over 1,929 common events / 1,799.167 s:
  added offset median 0.333 ms, max and p95 0.667 ms, estimated slope
  −0.002615 ppm. This is an overlap result, not perceptual monitoring. The
  strict full-edge gate remains false: the capture begins after source events
  0–1 (video) / 0 (audio), the finite capture censors the source tail, and the
  onset detector has 11 extra observed audio candidates versus 16 in its
  source-reference baseline. No interior event-ID gap was found in the matched
  overlap. The raw gate was not overwritten or represented as a strict PASS.
* Resource sampling every 5 s for 1,800.24 s (361 samples): RSS peak 59,364 KiB,
  FD peak 13, thread peak 3, CPU 195.58 s. No failover/recovery occurred, so
  this is a clean-run stability result, not recovery proof.
* The user confirmed no additional authorized test broadcast is currently
  available; remaining work is offline-only. 2 h, 6 h, and controlled-failure
  endurance are NOT TESTED. POC 1 live B pictures, MMCO 5, arbitrary broadcast
  compatibility, and the exact V3/V5/V8 inputs remain outside this run.

**Campaign: PARTIAL. Stable: NO-GO.** The 30 min exact-bundle clean run is
substantive evidence, but it cannot replace the unrun 2 h / 6 h / failure
stages. See `ENDURANCE_RESULT.md`, `COMPATIBILITY_MATRIX.md`, and
`RELEASE_READINESS.md`.

## Supplemental offline verification — 2026-11-03

The POC-2 test fixture no longer depends on the unavailable `libopenh264`
encoder. It is generated by FFmpeg 6.1.1/libx264 in Baseline mode with no B
pictures; the emitted SPS is asserted to signal POC type 2, no fixed VUI timing
and a zero-reorder bound, and FFmpeg independently decodes the elementary
stream. The malformed B-slice syntax test also now executes against this
fixture. Source regression is **767 passed, 0 skipped** and bundled production
regression is **758 passed, 0 skipped**. Ruff, format, compileall, plugin
discovery, deterministic bundle regeneration and manifest verification pass.
The production bundle SHA remains
`5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`; no live
or endurance evidence changed. Stable remains **NO-GO** because the 2 h / 6 h
and live fault-injection stages remain untested.

# Historical H.264 POC types 0/1/2 milestone result

The section below records the earlier POC milestone artifact, not the current
comprehensive campaign result above. Its test counts and bundle hash are
historical. The two encoder-dependent skips listed there were subsequently
removed in the supplemental offline run above; the live scope and limitations
remain unchanged.

## Outcome

Production now accepts POC types 0, 1 and 2 for the validated progressive, frame-coded, explicit Grid-composition subset. Each type passed both offline production `MediaSink`→`StreamIO`→MPEG-TS tests and a short synthetic self-broadcast Native Grid trial. Each live result had the same SPS POC type as its source, a contiguous byte-identical VCL/AAC interval, complete TS verification, full decode, and EOF/drain.

**Goal: COMPLETE for the validated progressive/Grid-composition subsets of all three POC types.** Each type has an independently decoded valid bitstream, an own SOOP Native Grid send/receive, production Streamlink output, VCL/AAC identity checks, full output decode and regression coverage. This does not claim universal H.264 support: Type-1 live evidence is no-reorder (Type-1 B-frame handling has offline E2E evidence), Type-2 live evidence is no-reorder, and MMCO 5 remains fail-closed. Broad service compatibility and long-duration behavior remain outside the proven subset. See [the support matrix](POC_TYPE_SUPPORT_MATRIX.md).

## Standards correction

Commit `41309cb` had incorrectly allowed successive non-reference POC-type-2 pictures when their POC values differed. H.264 7.4.2.1 prohibits the pattern at the coded-video-sequence level for the accepted frame-only subset. The condition is restored to reject adjacent non-reference pictures regardless of POC. The former “distinct POC is valid” test is now a negative test. No exception or synthetic picture is used to bypass the rule.

## Issue status

| Issue family | Result | Evidence / remaining limit |
|---|---|---|
| Type-0 B-frame timing / reorder | FIXED FOR TESTED SUBSET | Offline B-frame StreamIO E2E and 15-second live Grid sample pass; VCL/AAC interval identity and independent decode pass. Exact V3 input unavailable. |
| Type-1 POC/timing | FIXED FOR TESTED SUBSET | Production type-1 rejection removed only after an independently decoded Type-1 bitstream and real StreamIO E2E. Live Grid test confirms Type 1 with no reorder. Live Type-1 B-picture Grid test is still unverified. |
| Type-2 adjacent non-reference rule | FIXED | Incorrect acceptance introduced at `41309cb` corrected to the normative 7.4.2.1 rejection; distinct and duplicate POC negative tests pass. |
| Type-2 low-delay reception | FIXED FOR TESTED SUBSET | Offline and live no-B zero-reorder samples pass; prohibited adjacent non-reference sequence remains rejected. |
| MMCO 5 | UNSUPPORTED / FAIL-CLOSED | Still rejected as `h264_grid_mmco5_unverified`; complete Grid epoch interaction is not proven. |
| V5 exact `h264_picture_order_conflict` report | UNVERIFIED AS REPORTED | Synthetic B-frame and paired marker tests pass, but the reporter's input is unavailable. Actual contradictory POC/PTS still fails closed. |
| V8 `frame_num 119→1` | UNVERIFIED AS REPORTED | It is not normal wrap for MaxFrameNum 128; original SPS/reference/AU is unavailable. No state reset or missing-picture fabrication was added. |
| V8 231 ms PCR interval | PARTIAL | Prior synthetic interpolation and current TS checks are valid; no claim about the reporter's real capture or real-time packet pacing. |

## Validation

* Source suite: **736 passed, 2 skipped**.
* Single-file bundle suite: **727 passed, 2 skipped**.
* Single-file construction/loading tests: **9 passed**.
* Ruff check, Ruff format check, compileall, deterministic bundle regeneration/check and `git diff --check`: pass.
* Streamlink 8.6.2 sideload listing found `soop_grid`.
* POC offline E2E: all three types pass actual `MediaSink`/`SoopGridReader.open/read/close`, TS, decode, payload identity and EOF/drain.
* Short synthetic own-broadcast Grid E2E: all three requested POC types received; detailed frame/AU, TS, PCR, event-marker and drain counts are in [POC_GRID_LIVE_VALIDATION.md](POC_GRID_LIVE_VALIDATION.md).
* The two skips require `libopenh264`, absent from local FFmpeg. The new tests use libx264 and validate the emitted SPS type instead of trusting encoder options.

## Bundle and source state at validation

* Branch: `fix/grid-startup-readiness`.
* Base HEAD before this task: `41309cb826e6a673d597a99423526c2369d5cebc`.
* Tested bundle SHA-256: `e1a1433bbcfb67febb37e43b7e92f2761c3f1cd58b4119dfbaa44c5dc0f6029b`.
* No live media, credentials, account/channel identifiers or raw capture is included in the repository.

## Release decision

**Beta: GO for the validated progressive POC 0/1/2 subsets. Stable: NO-GO.** Do not promote MMCO 5, arbitrary reference-state combinations, live Type-1 B frames, long-duration drift, exact V3/V5/V8 cases or universal broadcaster compatibility based on these short synthetic tests. The q=32/1080p profile remains separate and unchanged.
# Comprehensive compatibility campaign — 2026-11-03 update

This update applies to HEAD `b070755ed1f1593714575c3813ace1bc64da221e` and
`dist/soop_grid.py` SHA-256
`5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.
It supplements earlier artifact-scoped results below; it does not rewrite their
test hashes or claim that historical endurance runs exercised this candidate.

* Exact candidate offline tests: source `764 passed, 2 skipped`; bundle
  `755 passed, 2 skipped`. Both skips require `libopenh264`, absent from the
  available FFmpeg 6.1.1 build. Module and bundle used the same exclusions for
  the preserved untracked `tests/test_suffix_latejoin.py`.
* Ruff check, tracked-file format check, compileall, deterministic bundle check,
  Streamlink 8.6.2 plugin discovery and diff checks passed.
* No production media defect was reproduced in this pass. Two stale statements
  were corrected: production timing uses Grid composition (not HRD-derived PTS),
  and verified Grid quality enumeration includes conditional 1080p/q32.
* The exact community V3/V5/V8 inputs remain unavailable. MMCO 5 remains
  fail-closed; Type-1 live B-picture handling remains unverified; the current
  candidate has no fresh live, A/V-marker, memory/FD trend, 2-hour or 6-hour run.
* Current candidate Stable decision: **NO-GO**. Existing Beta use remains
  conditional on the documented subsets and fail-closed boundaries.
* Host GitHub DNS lookup failed in this environment. Remote synchronization is
  not represented as verified here; see the final execution report for the
  eventual push check.

See `COMPATIBILITY_INVENTORY.md`, `H264_REFERENCE_CONFORMANCE.md`,
`AAC_AV_SYNC_CONFORMANCE.md`, `TRANSPORT_RECOVERY_CONFORMANCE.md`,
`ENDURANCE_TEST_PLAN.md`, `ENDURANCE_RESULT.md`, `COMPATIBILITY_MATRIX.md` and
`RELEASE_READINESS.md` for detail. Literal error codes are indexed in
`ERROR_CODE_INVENTORY.md`.

## Latest offline-only continuation — 2026-11-03

The user confirmed no authorized test broadcast is currently available;
verification continued offline without contacting SOOP. On HEAD
`b1adbfc419ce834315ddab3ea864ca3a1cc2d0f6`, source tests pass **784/784** and
bundle parity tests pass **775/775**, with zero skips. Streamlink 8.6.2
discovers and loads `soop_grid`; Ruff, format, compileall, deterministic bundle
check and manifest validation pass. Bundle SHA-256 remains
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.

A new bounded local synthetic-media runner passed 60-second and 600-second
media timelines through production MediaSink, StreamIO and MPEG-TS, with VCL
and ADTS payload identity, FFmpeg full decode, no TS continuity or PSI CRC
errors, a 100 ms maximum PCR value gap, exact StreamIO byte accounting, EOF and
drain. These accelerated synthetic runs do not establish real-time pacing,
live server compatibility, multi-hour resource trends, or Parent/Cache
recovery. Current-build live, 2-hour, 6-hour and controlled-failure endurance
remain NOT TESTED. Campaign status is **PARTIAL** and Stable is **NO-GO**.

An additional 1,800-second synthetic media timeline completed in 89.335 wall
seconds. It preserved 18,000 input/output VCL NALs and 84,376 input/output AAC
AUs; 609,196 TS packets had zero continuity/PSI CRC errors and a 100 ms maximum
PCR value gap. Full FFmpeg decode, EOF/drain, output accounting and unchanged
FD count passed. RSS peaked at 301,156 KiB for the harness that retains and
parses all generated input media; this is not product-only or long-run leak
evidence. Live, real-time and 2/6-hour gates are still untested.

The same bounded helper also passed a 7,200-second synthetic timeline in
356.393 wall seconds: 72,000 VCL NALs and 337,501 AAC AUs matched; full decode,
TS integrity, PCR spacing, EOF/drain and byte accounting passed. Its
1,082,268 KiB RSS peak includes the helper's retained source media and parsed
AU lists. This supplies long media-timestamp coverage only; it is not live or
wall-clock endurance evidence and does not change the release gate.

# Existing report history
