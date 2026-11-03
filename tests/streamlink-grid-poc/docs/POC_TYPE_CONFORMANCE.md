# H.264 POC type conformance and supported subset

Status checked 2026-11-02 against the production source and the short synthetic SOOP Grid runs recorded in [POC_GRID_LIVE_VALIDATION.md](POC_GRID_LIVE_VALIDATION.md).

Normative reference: [ITU-T H.264 (08/2024)](https://www.itu.int/rec/T-REC-H.264-202408-S), in particular clauses 7.4.2.1, 7.4.3, 8.2.1, 8.2.1.3, 8.2.5.1 and 8.2.5.2.

## Timeline model

For all three POC types, POC checks decoded-picture/display order; it is not converted to elapsed time. Production DTS is taken from the accepted Grid decode timestamp and PTS from that timestamp plus the validated Grid composition offset, rescaled from the common media origin. HRD/SEI delay does not replace this Grid composition clock. PTS uniqueness/order, increasing DTS, IDR epoch rules and the SPS reorder bound remain checked.

The receiver accepts progressive, frame-coded Annex-B H.264 only, with one supported picture per Grid video chunk, supported slice syntax, nonnegative bounded Grid composition and unchanged coded payload. A successful POC-type result does not imply support for every profile, reference structure, HRD mode or parameter-set transition.

## Type-specific rules

* **Type 0:** POC LSB/MSB wrap is derived from the previous reference picture as required by the SPS and slice syntax. The short live fixture included B pictures; the output retained the same SPS and VCL NALs for the observed contiguous interval. POC/PTS disagreement and invalid reference state still fail closed.
* **Type 1:** `FrameNumOffset`, `AbsFrameNum`, the reference-picture cycle offsets, non-reference offset and slice `delta_pic_order_cnt` contribute to expected order. A generated B-frame Type-1 stream passed offline through the production `MediaSink`/`StreamIO` path and independently decoded to the same frame hashes as its Type-0 source. The live Grid fixture was a valid no-reorder Type-1 sequence derived by rewriting a generated low-delay stream's SPS to a one-entry `+2` cycle; it was independently decoded before broadcast and the Grid output SPS remained Type 1. This proves the tested subset, not all Type-1 cycles or arbitrary B-frame Grid timing.
* **Type 2:** POC follows `FrameNumOffset` and `frame_num` and requires a proven zero-reorder bound in this implementation. For the accepted frame-only SPS subset, H.264 clause 7.4.2.1 prohibits a non-reference frame immediately followed by another non-reference picture in a coded video sequence. The check applies even when their computed POC values differ. The earlier relaxation in commit `41309cb` was incorrect and has been reverted. The live fixture was low-delay/no-B; offline tests separately verify permitted progression and reject adjacent non-reference pictures.

## Type-2 correction

POC duplicate-field-order discussion in clause 8.2.1.3 does not relax the syntax-level coded-video-sequence restriction in 7.4.2.1. Since this parser rejects interlaced SPS and field pictures, field-pair exceptions are outside its accepted subset. The positive test that previously accepted distinct-POC adjacent non-reference pictures was invalid as a positive fixture and is now a negative test. No source payload is repaired or rewritten to make such a sequence pass.

## MMCO 5 and gaps

MMCO 5 is parsed and affects internal POC/reference bookkeeping, but production Grid output remains fail-closed with `h264_grid_mmco5_unverified`. The complete interaction between MMCO 5, the Grid composition epoch and output PTS has not been proven. Likewise, `gaps_in_frame_num_value_allowed_flag` is not evidence that missing coded pictures were received or can be reconstructed. When a required reference transition is not modeled or proven, the receiver rejects it; it never fabricates an access unit.

## Support claim

POC types 0, 1 and 2 are enabled on the production path for the validated progressive/Grid-composition subsets. A short self-broadcast and complete StreamIO/TS/decode test was completed for each type. Type 0 live evidence includes B pictures; Type 1's live sample is no-reorder while a separate offline Type-1 B-frame sample passes. Type 2 live evidence is no-reorder. MMCO 5, interlace, low-delay HRD, unsupported slice layouts, unmodeled reference state and the exact community V3/V5/V8 samples remain unsupported or unverified.
