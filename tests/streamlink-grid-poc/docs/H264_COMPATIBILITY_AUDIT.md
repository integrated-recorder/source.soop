# H.264 compatibility audit

Normative reference: [ITU-T H.264 (08/2024)](https://www.itu.int/rec/T-REC-H.264-202408-S), especially clauses 7.4.2.1, 7.4.3, 8.1, 8.2.1, 8.2.1.3, 8.2.5.1 and 8.2.5.2.

## Findings

* `_validate_frame_num_progress()` compares a picture to the successor of the previous reference `frame_num` modulo SPS `MaxFrameNum`. With `gaps_in_frame_num_value_allowed_flag == 0`, a non-successor fails closed as `h264_frame_num_gap`. With the flag set, this receiver does not synthesize missing coded pictures; support remains bounded by the implemented reference-state model.
* Only frame-coded progressive SPS is accepted. IDR requires `frame_num == 0`. MMCO 5 is parsed and affects POC/reference bookkeeping, but the production Grid timing subset still rejects it as `h264_grid_mmco5_unverified`.
* `119→1` is not normal modulo wrap when `MaxFrameNum == 128`; successor is 120 and wrap is 127→0. Grid packet continuity is independent and does not prove H.264 reference-picture continuity. The reporter's actual SPS/PPS/AU and reference marking remain unavailable, so that exact report remains UNVERIFIED.
* POC 0 uses prior-reference POC state for LSB/MSB wrap. POC 1 computes cycle-based order including `FrameNumOffset`, reference/non-reference offsets and slice deltas. POC 2 computes order from `FrameNumOffset`/`frame_num` and is accepted only with a proven zero-reorder bound.
* Type 2 rule correction to commit `41309cb`: H.264 7.4.2.1 prohibits a POC-type-2 coded video sequence containing a non-reference frame immediately followed by a non-reference picture. For this frame-only parser subset, the former test that allowed distinct POC values was not a conforming positive case. Production now rejects this pattern regardless of POC; tests distinguish it from allowed progression and reject it explicitly.

## Production timing and offline/live evidence

Production timing is `DTS = rescale(Grid startTime - origin) + 90000` and `PTS = rescale(Grid startTime + composition - origin) + 90000`. POC validates order; it is not turned into elapsed time. PTS uniqueness/order, increasing DTS, IDR epoch rules, reorder bounds and Grid composition checks remain enabled.

POC types 0, 1 and 2 are now enabled for validated progressive Grid-composition subsets. New offline E2E tests pass each generated type through the real `MediaSink`, `SoopGridReader.open/read/close`, buffer, TS mux and EOF/drain. FFmpeg independently decodes all output; VCL NAL and AAC AU payloads match the generated input. An offline Type-1 B-frame stream also decodes to the same frame hashes as its Type-0 source.

Short self-broadcast Grid tests additionally verified:

* Type 0 with B pictures: source, RTMP-reference and Grid SPS type 0; 468/468 captured VCL NALs and 792/792 AAC AUs matched a contiguous source interval.
* Type 1 with zero reorder: source, RTMP-reference and Grid SPS type 1; 466/466 VCL NALs and 792/792 AAC AUs matched a contiguous interval. This live result does not cover Type-1 B pictures.
* Type 2 zero-reorder: source, RTMP-reference and Grid SPS type 2; 466/466 VCL NALs and 792/792 AAC AUs matched a contiguous interval.

Each TS passed the independent structural/timestamp verifier and full FFmpeg decode; exact per-run metrics and the clipped capture bounds are in [POC_GRID_LIVE_VALIDATION.md](POC_GRID_LIVE_VALIDATION.md). This is short synthetic evidence, not broad encoder/service compatibility evidence.

The former two encoder-dependent skips have been removed. Their POC-2 no-B fixture now uses the available libx264 Baseline encoder; tests inspect the emitted SPS and independently decode the bitstream before checking the production path. The follow-up source and bundle suites both ran with zero skips.

## Remaining limits

MMCO 5 remains fail-closed. Arbitrary reference-DPB transitions, interlace, low-delay HRD, unsupported slice structures, midstream codec changes, and the exact reporter V3/V5/V8 media remain unverified or unsupported. PCR-only interpolation is a bounded file-timeline operation, not real-time packet pacing. The short Grid trials do not establish long-duration drift, subjective A/V synchronization or all SOOP encoder variants.
