# H.264 compatibility audit

Normative reference: ITU-T H.264 (08/2024), especially clauses 7.4.3, 8.1, 8.2.1, 8.2.5.1, and 8.2.5.2: <https://www.itu.int/rec/dologin_pub.asp?id=T-REC-H.264-202408-I%21%21PDF-E&lang=e&type=items>.

## Findings

* `_validate_frame_num_progress()` in `soop_grid/h264clock.py` compares the current picture to the successor of the previous reference frame number modulo SPS `MaxFrameNum`. With `gaps_in_frame_num_value_allowed_flag == 0`, non-successors fail closed with `h264_frame_num_gap`; with the flag set, the parser leaves normative gap-picture decoding to the downstream H.264 decoder. This receiver does not synthesize or rewrite coded access units.
* The parser only accepts frame-coded (non-interlaced) SPS, so the complementary-field exceptions to frame_num progression do not apply to its accepted subset. IDR requires frame_num 0. MMCO5 is parsed and influences POC/reference bookkeeping, but is rejected by the production timing subset until its complete Grid epoch behavior has independent evidence.
* `119→1` is not ordinary modulo wrap in a 7-bit frame_num domain. 119's successor is 120; wrap is 127→0. A Grid packet sequence that is contiguous is independent evidence and does not establish reference-picture continuity.
* POC type 0 wrap uses the previous reference picture's POC state. POC type 2 uses previous-picture frame_num and FrameNumOffset; the parser requires a proven zero reorder bound. POC type 1 math is parsed, but production currently fails closed with `h264_grid_poc_type_unverified`.
* The former POC type 2 guard rejected every adjacent non-reference pair. H.264 8.2.1.3 NOTE 2 prohibits consecutive non-reference pictures only when they produce duplicate Top/BottomFieldOrderCnt. The guard now rejects only a repeated POC for adjacent non-reference frames; distinct POC values are accepted when the SPS gap flag permits the sequence. Deterministic syntax-level tests cover both paths. These are parser probes, not complete independently decodable streams.

## Timing and order

Production timing remains `DTS = rescale(Grid startTime - origin) + 90000` and `PTS = rescale(Grid startTime + composition - origin) + 90000`. POC is an order cross-check; it is not converted to elapsed time. PTS/DTS regressions, duplicate presentation timestamps, impossible POC/PTS order, reorder-bound violations, IDR epoch violations, unsupported POC type 1, and MMCO5 remain fail-closed.

`h264_reorder_bound_invalid` continues to reject VUI reorder bounds greater than the signaled buffering bound; this is a bitstream constraint, not a generic B-frame rejection. The first release and current implementation both enforce a bound, though the current parser validates more SPS/VUI syntax. HRD/SEI is parsed for validation/diagnostics but does not replace Grid composition timestamps.

## Independent evidence and limits

* Same FFmpeg/libx264 B-frame input: both first-release and current clocks accepted 30 frames, including 18 B pictures. PTS-sorted order matched FFprobe's decoded `pkt_pos` display order and DTS strictly increased.
* Retained 60-second Grid wire: in-memory parser replay after exact overlap duplicate filtering yielded 3,591 current accepted VCL AUs, no current parser errors, and 30 release timing failures followed by missing-parameter-set errors. This does not reproduce the reporter's private V3/V5/V8 input and did not rebuild the historical full mux path.
* Two POC type 2 tests were skipped because the pinned local FFmpeg lacks the `libopenh264` encoder. Other type 2 parser and decode tests ran using available generated inputs.

Unresolved: the reporter's actual SPS/PPS, frame_num width, `gaps_allowed`, reference marking, POC, and exact AU around `119→1` are unavailable. Therefore that report remains **UNVERIFIED**, not fixed. A missing reference AU or nonconforming encoder output must not be “repaired” by resetting frame_num or fabricating coded pictures.
