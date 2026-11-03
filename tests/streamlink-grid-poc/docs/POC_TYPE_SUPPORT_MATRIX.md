# H.264 POC support matrix

Scope: current production bundle and the bounded progressive/Grid-composition subset. “Production supported” here means the selected test structure passed source parsing, actual Streamlink/StreamIO output, independent TS verification and full decode; it does not mean every syntax combination that can use that POC type.

| POC type | Parser | Offline bitstream | SOOP Native Grid | Production subset | MMCO 5 |
|---:|---|---|---|---|---|
| 0 | VERIFIED | VERIFIED: libx264 B-frame stream; `MediaSink`→StreamIO→TS; decoded frame identity | VERIFIED: short self-broadcast with B pictures; SPS and VCL preserved | SUPPORTED for tested progressive Grid-composition/reorder subset | FAIL-CLOSED / UNVERIFIED |
| 1 | VERIFIED | VERIFIED: constructed valid POC-1 stream, including offline B-picture case and independent decode/hash comparison | VERIFIED: short self-broadcast, no-reorder Type-1 subset; SPS/VCL preserved | SUPPORTED for tested progressive Grid-composition subset; live B-frame Type 1 not verified | FAIL-CLOSED / UNVERIFIED |
| 2 | VERIFIED | VERIFIED: libx264 low-delay stream and `MediaSink`→StreamIO→TS | VERIFIED: short self-broadcast, zero-reorder/no-B subset; SPS/VCL preserved | SUPPORTED for tested progressive zero-reorder subset; adjacent non-reference pictures rejected | FAIL-CLOSED / UNVERIFIED |

Common restrictions: frame-coded progressive SPS only; explicit nonnegative Grid composition required; one supported picture per Grid video chunk; no midstream codec change; unsupported slice/reference structures and low-delay HRD fail closed. Exact community V3/V5/V8 inputs were unavailable, so their reports are not individually marked fixed. See [conformance notes](POC_TYPE_CONFORMANCE.md) and [live evidence](POC_GRID_LIVE_VALIDATION.md).
