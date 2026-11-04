# H.264 POC support matrix

Scope: current production bundle and the bounded progressive/Grid-composition subset. “Production supported” here means the selected test structure passed source parsing, actual Streamlink/StreamIO output, independent TS verification and full decode; it does not mean every syntax combination that can use that POC type.

| POC type | Parser | Offline bitstream | SOOP Native Grid | Production subset | MMCO 5 |
|---:|---|---|---|---|---|
| 0 | VERIFIED | VERIFIED: libx264 B-frame and MMCO-5 streams; `MediaSink`→StreamIO→TS; decoded frame identity | VERIFIED: historical short self-broadcast with B pictures; SPS and VCL preserved | SUPPORTED for tested progressive Grid-composition/reorder subset | VERIFIED_OFFLINE for one progressive, no-B, one-reference fixture; live untested |
| 1 | VERIFIED | VERIFIED: constructed valid POC-1 B-frame and MMCO-5 streams, zero-delta flag, bottom-POC/delta1, and empty-cycle/negative-nonref-offset variants; independent decode/hash and StreamIO output | VERIFIED: historical short self-broadcast, no-reorder subset; SPS/VCL preserved | SUPPORTED for tested progressive Grid-composition subset; live B-frame Type 1 not verified | VERIFIED_OFFLINE for one progressive, no-B, one-reference fixture; live untested |
| 2 | VERIFIED | VERIFIED: libx264 low-delay and MMCO-5 streams; `MediaSink`→StreamIO→TS; decoded frame identity | VERIFIED: historical short self-broadcast, zero-reorder/no-B subset; SPS/VCL preserved | SUPPORTED for tested progressive zero-reorder subset; adjacent non-reference pictures rejected | VERIFIED_OFFLINE for one progressive, no-B, one-reference fixture; live untested |

MMCO-5 offline evidence is limited to a generated progressive, CAVLC, no-B, one-reference stream with one MMCO-5 reference P picture. The fixture is independently decoded and frame-hash compared, then sent through the production MediaSink/StreamIO/TS path for each POC type with VCL identity, full decode, and EOF/drain checks. No live MMCO-5 test was run. Common restrictions remain: frame-coded progressive SPS only; explicit nonnegative Grid composition required; one supported picture per Grid video chunk; no midstream codec change; unsupported slice/reference structures and low-delay HRD fail closed. Exact community V3/V5/V8 inputs were unavailable, so their reports are not individually marked fixed. See [conformance notes](POC_TYPE_CONFORMANCE.md) and [live evidence](POC_GRID_LIVE_VALIDATION.md).

Latest offline Type-1 reference-B follow-up: a transformed POC-0 B-pyramid
fixture with reorder bound 2 passed a 21,600-second synthetic media timeline
through the production sink. Decoded-frame identity matched across all 216,000
frames; VCL/AAC payload identity, TS checks, full FFmpeg decode and StreamIO
drain passed. This strengthens only the transformed offline subset. Native
Type-1 encoder output, live Grid Type-1 B pictures, and source-relative
synchronization remain unverified. Details: `ENDURANCE_RESULT.md`.

Offline syntax/E2E coverage also includes the Type-1
`delta_pic_order_always_zero_flag=1` branch. A progressive no-B POC-2 libx264
stream was transformed by changing only SPS POC syntax to a one-entry +2
reference cycle; slice syntax remained unchanged. FFmpeg decoded source and
derived streams to identical frame hashes. The derived SPS was parsed as Type
1 with the flag set, and the production clock, MediaSink, StreamIO, TS mux,
VCL and AAC identity checks, full TS decode, and EOF/drain passed. This is a constructed
valid bitstream subset, not native Type-1 encoder output or live Grid evidence.

The production E2E matrix also runs a Type-1 B-picture stream with PPS bottom
POC syntax enabled and `delta_pic_order_cnt[1]=0`. Independent decoding,
frame-order fields, VCL/AAC identity, full TS decode and EOF/drain pass. This
is additional constructed syntax coverage, not live Type-1 B-picture support.

The same E2E matrix also covers a Type-1 empty POC cycle with
`offset_for_non_ref_pic=-1`. Picture POC matches the source sequence for both
reference and non-reference pictures; decode, payload identity and drain pass.
This is a constructed offline case only.
