# Compatibility regression matrix

| Input / condition | First public release | Current before this change | Current after this change | Independent check |
|---|---|---|---|---|
| 30-frame libx264 B-frame fixture, 18 B pictures | 30/30 accepted | 30/30 accepted | 30/30 accepted | FFprobe `pkt_pos` display order matched PTS order; DTS strictly increased. |
| Retained 60-second Grid wire capture, exact adjacent overlap duplicates filtered | SPS with missing/non-fixed timing rejected; after the rejected configuration the parser reports missing parameter set | 3,591 accepted VCL AUs; no error on unique frames | Same | Payload remained in memory. Parser-level comparison only; not a full historical mux replay. |
| 119→1 with MaxFrameNum 128 and gaps forbidden | No explicit reference-frame progression check in release parser | `h264_frame_num_gap` | Same | Deterministic parser test confirms this is not modulo wrap. |
| 127→0 with MaxFrameNum 128 | No explicit progression check | Accepted by progression validator | Same | Deterministic unit test. |
| POC type 2 adjacent nonref pictures with gaps allowed, distinct frame_num / POC | Type 2 unsupported | Incorrectly accepted after commit `41309cb` | Rejected regardless of distinct POC | Normative H.264 7.4.2.1; deterministic negative parser probe. |
| POC type 2 adjacent nonref pictures with duplicate POC | Type 2 unsupported | Rejected | Rejected | Deterministic negative parser probe. |
| POC type 1 in production Grid timeline | Unsupported | Parsed but `h264_grid_poc_type_unverified` | Accepted for tested progressive/Grid-composition subset | Offline B-frame StreamIO E2E and short live no-reorder Grid sample; see POC docs. |
| POC types 0/1/2 full production StreamIO | Type 0-only subset | Type 0/2 subset; Type 1 rejected | All three tested subsets pass | Offline full TS/decode/payload check and short live self-broadcast per type; MMCO5 excluded. |
| MMCO5 in production Grid timeline | Not parsed | `h264_grid_mmco5_unverified` | Same | Parser/state unit coverage; production still fail-closed. |
| 231 ms DTS/PCR gap | No interpolation | Bounded interpolation up to 2 s | Same | Independent PSI/PES/PCR verifier, payload SHA comparisons, FFmpeg full decode. |
| >2 s PCR time gap / PCR regression | No equivalent two-second guard | Rejected | Rejected | State remains unchanged on rejection. |
| Grid duplicate and sequence identity | Older path | Identity/overlap filtering before H.264 clock | Same | Three exact duplicates skipped in the retained capture; no identity conflict. |

The V3/V5/V8 patch sources and original failing media are unavailable. Their private error names and fixes are not treated as official release behavior or as reproduced current defects. The skipped encoder-dependent tests are recorded in the final report.
