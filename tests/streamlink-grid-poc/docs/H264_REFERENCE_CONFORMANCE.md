# H.264 reference, POC, DPB and timing conformance

Audited source: `soop_grid/h264clock.py`, `soop_grid/media.py`. The state-machine clause review below was based on [ITU-T H.264 (08/2024)](https://www.itu.int/rec/T-REC-H.264-202408-S). The in-force [H.264 (06/2026), V16](https://www.itu.int/rec/T-REC-H.264-202606-I) delta was then reviewed for its published changes and the SEI interface clauses relevant to this parser. This is not a complete V15-to-V16 clause-by-clause diff; any effect of V16's miscellaneous defect corrections on unreviewed syntax remains **UNVERIFIED**. This is an implementation-subset assessment, not full decoder conformance.

## H.264 V16 (06/2026) delta review

The ITU recommendation database describes V16 as adding interfaces for eleven VSEI messages, extended film-grain and neural-network post-filter activation interfaces, a future-extension mechanism, and corrections to minor defects in prior text. In the H.264 Annex D payload dispatch, V16 explicitly adds payload types 213 (`sei_processing_order`), 214 (`processing_order_nesting`) and 215 (`encoder_optimization_info`); clauses D.3.6–D.3.8 define interpretation constraints for processing order/nesting and encoder optimization information. VSEI owns the application-specific payload syntax. The normative H.264 references for the V16 delta are [the in-force edition](https://www.itu.int/rec/T-REC-H.264-202606-I) and the [ITU recommendation database/history](https://www.itu.int/ITU-T/recommendations/rec.aspx?rec=H.264).

The inspected official V16 PDF artifact was 15,530,891 bytes, SHA-256 `028cf2cfefd6083ced98d3acb0b586d9328e1631c13d6f21057ad54c569b1b79`.

The receiver parses and bounds the generic SEI payloadType/payloadSize envelope, semantically interprets only buffering-period, picture-timing and recovery-point messages, and skips other SEI payload bodies as opaque bytes. New payload types 213–215 therefore do not affect coded-sample reconstruction or the Grid-composition clock in this implementation; their VSEI semantics are **not interpreted**. The AU bytes remain unchanged on the raw `video.h264` path. New source tests cover these three envelope paths, bounded opaque handling, input-AU preservation, and truncated-envelope rejection. Their synthetic opaque payloads are not valid VSEI semantic fixtures and do not claim VSEI conformance.

### Targeted V15-to-V16 core-clause comparison

A targeted text comparison was made for the rules most directly exercised by this receiver and its recent regressions: SPS `pic_order_cnt_type` constraints and MaxFrameNum (clause 7.4.2.1), `PrevRefFrameNum`/`gaps_in_frame_num_value_allowed_flag` and frame-number gap constraints (clause 7.4.3.1), and the POC/MMCO-5 reset path in clause 8.2.1 and its type-specific derivations. The inspected V16 text retains the V15 rules relevant to the accepted progressive-frame subset: Type 2 forbids the listed consecutive non-reference-picture patterns; `gaps_in_frame_num_value_allowed_flag` controls the normative gap process and does not authorize fabricated coded pictures; MMCO-5 normalizes the current picture order counts and resets subsequent frame-number/POC derivations as described by the type-specific process. The V15 passages are available in the [official V15 PDF](https://www.itu.int/rec/dologin_pub.asp?id=T-REC-H.264-202408-I%21%21PDF-E&lang=e&type=items); corresponding text was checked in the official V16 PDF whose hash is recorded above.

This targeted comparison found no change requiring a production-code adjustment in those paths. It is not a full V15/V16 diff of all DPB marking, reference-list, HRD, profile, extension-NAL or minor-correction clauses. Those remain outside this comparison; no blanket current-edition conformance claim follows.

## Production invariants

* Input is bounded Annex-B H.264. Parsed syntax is validated before an AU is committed; `H264Clock.inspect()` snapshots and rolls back mutable state after rejection.
* Production DTS is rescaled Grid `startTime`; PTS is rescaled `startTime + composition`, with a common origin. POC is used to check picture/display order, never converted to an assumed frame duration.
* VCL payload is carried unchanged. Startup may prepend active SPS/PPS to make the output independently decodable; this is parameter-set framing, not VCL rewriting.
* Each accepted Grid video chunk must describe one supported picture. DTS must increase; PTS must be unique and agree with POC order within the bounded reorder window.

## NAL header validation

Every Annex-B NAL header is checked before the clock classifies or skips the
unit. The receiver rejects a nonzero `forbidden_zero_bit`, `nal_unit_type=0`,
and `nal_ref_idc` values that violate the base-profile header constraints:
types 5/7/8 require a nonzero reference indicator, while types 6/9/10/11/12
require zero. This closes a pass-through gap where an otherwise unparsed AUD
could carry an invalid header and still accompany an accepted VCL picture.
The AUD remains in the preserved input; this check does not rewrite media.
Deterministic regressions use a valid libx264 AU and alter only its AUD header.
The clauses on NAL unit header semantics and Table 7-1 of [ITU-T H.264
(08/2024)](https://www.itu.int/rec/T-REC-H.264-202408-S) define these
constraints. Other NAL payload syntax that the receiver does not parse remains
outside the claimed support subset.

A separate review of NAL type 14 did not add a blanket rejection: Table 7-1
classifies it as non-VCL for Annex A, and Annex A decoders ignore its contents.
Extension-profile association rules are outside this receiver's declared
profile subset; the supported Annex A path continues to preserve the NAL and
clock the base VCL units as specified. This avoids turning an unproven concern
into an unnecessary rejection.

## POC types and boundaries

| Type | Implemented order state | Evidence level on documented subset | Remaining boundary |
|---:|---|---|---|
| 0 | Previous-reference POC LSB/MSB wrap; IDR epoch; reference marking; bounded reorder; MMCO-5 resets prior POC state to normalized zero | Parser + offline StreamIO/TS/decode + historical short self-broadcast with B pictures; new MMCO-5 fixture | Tested MMCO-5 subset is progressive/no-B/one-reference; live MMCO-5 and unusual DPB transitions unverified |
| 1 | `FrameNumOffset`, `AbsFrameNum`, cycle offsets, non-reference offset and slice deltas; MMCO-5 resets previous frame number/offset | Parser + offline valid B-picture and MMCO-5 streams + historical short live no-reorder self-broadcast | Live B-picture/MMCO-5, arbitrary cycles/deltas unverified |
| 2 | `FrameNumOffset` and `frame_num`; zero-reorder subset; MMCO-5 reset | Parser + offline decode + historical short low-delay/no-B self-broadcast; new MMCO-5 fixture | Reorder unsupported; adjacent non-reference picture sequence forbidden by SPS type-2 constraints; live MMCO-5 unverified |

`gaps_in_frame_num_value_allowed_flag=1` permits the decoder's normative non-existing reference-picture process; it is not proof that the transport delivered those coded pictures. This receiver does not invent VCL AUs. When gaps are disallowed, a reference-state successor mismatch fails with `h264_frame_num_gap`. For `MaxFrameNum=128`, 119→1 is not a modulo wrap; normal wrap is 127→0. Exact source SPS, slice/reference state and AU bytes from the community report are unavailable.

## MMCO 5

For frame-coded pictures, clauses 8.2.1 and 8.2.1.1–8.2.1.3 normalize the current MMCO-5 picture's field order counts by subtracting `PicOrderCnt(CurrPic)`. Subsequent uses of that picture therefore use normalized POC 0. Type 0 also seeds the next reference POC state from the normalized top-field order count (0 for this frame-only subset); Types 1/2 use the post-MMCO frame-number state. Production now applies those resets, starts a new POC comparison epoch at the next picture, and still derives output PTS exclusively from Grid composition. Duplicate MMCO-5 operations in one marking list are rejected under the standard's at-most-one constraint. These POC/MMCO clauses were included in the targeted V15-to-V16 comparison above and no change affecting this accepted subset was found. This is not a complete V16 audit of DPB marking, reference lists, HRD, extensions, or all minor corrections.

Evidence is limited to a generated progressive, CAVLC, no-B, one-reference stream with one MMCO-5 reference P picture. Type 0/1/2 variants independently decode to the same frame hashes as the source. Each passes production `MediaSink`→`StreamIO`→MPEG-TS, preserves every VCL NAL, fully decodes with FFmpeg, and drains EOF. This verifies a narrow syntax/state subset, not full DPB/list-management conformance or live Grid behavior. MMCO-5 outside this tested subset, arbitrary reference-management combinations, and live MMCO-5 remain unverified.

## Other explicit limits

Interlace/field pictures, FMO, unsupported slice/reference syntax, unsupported profiles, midstream codec changes, low-delay HRD and nonzero `pic_struct` are not in the supported subset. VUI reorder limits are checked against level/DPB bounds. HRD/SEI syntax is validated where implemented, but HRD delay does not supply production timestamps. POC/composition conflict, duplicate PTS, invalid reorder bounds and missing required parameter sets fail closed.

## Evidence scope

The historical self-broadcast evidence in `POC_GRID_LIVE_VALIDATION.md` belongs to bundle SHA `e1a1433bbcfb67febb37e43b7e92f2761c3f1cd58b4119dfbaa44c5dc0f6029b`, not the current `5c1657…` bundle. It establishes short captured intervals only. The exact V3/V5/V8 user inputs remain unverified. Current exact-bundle unit and bundle results are in `ENDURANCE_RESULT.md`.
