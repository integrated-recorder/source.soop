# Comprehensive compatibility campaign — 2026-11-03 final update

This update applies to code candidate `b070755ed1f1593714575c3813ace1bc64da221e`
and bundle SHA-256
`5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.
Documentation-only commits may advance Git HEAD without changing the tested
bundle.

* Offline: source 764 passed / 2 optional `libopenh264` skips; bundle 755 passed
  / 2 skips. Ruff, format, compileall, deterministic bundle/SHA, Streamlink
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

# H.264 POC types 0/1/2: compatibility result

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

# Existing report history
