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
