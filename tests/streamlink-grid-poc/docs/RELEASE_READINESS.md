# Release readiness

## Latest offline candidate — 2026-11-03

H.264 V16 SEI envelope regressions were added for opaque payload types 213–215
and malformed lengths. These test common framing and byte preservation only;
the new H.274/VSEI metadata semantics are not interpreted. No production
source or bundle change results. See `H264_REFERENCE_CONFORMANCE.md`.

* Bundle SHA-256: `c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
* Production code candidate: `51a5a157a1269c00a2a952d5ad0dacefed35ef7e`; latest offline test run was on the working tree based on `ee61fae6884371c247cfeb1ecb431854bfd6ac92`.
* Latest source tests: 784 passed, 0 skipped; bundled parity: 775 passed, 0 skipped. The source count includes the 9 standalone single-file tests.
* All NAL headers, including opaque pass-through units, now receive common H.264 header validation. The malformed-AUD regression and valid control pass.
* A deterministic 768-input malformed-parser smoke test produces no unexpected exceptions; broader coverage-guided fuzzing is not claimed.
* A fixed-seed TS scanner mutation smoke test processes 64 generated TS variants with 1–4 mutated bytes each; it verifies bounded scan results and input hashes, not coverage-guided fuzzing.
* A fixed-seed near-valid H.264 parser mutation test covers 1,024 variants of a synthetic SPS/PPS/IDR access unit and found no unexpected exception; it is not a conformance proof or coverage-guided fuzzing.
* A fixed-seed ADTS framing mutation test covers 1,024 variants of eight real encoded frames and checks frame-boundary, sample-count, duration and reconstruction invariants. It does not validate mutated AAC decoding or CRC values.
* A 64-session local StreamIO lifecycle smoke completed with exact byte accounting, no receiver worker left behind, and no Linux FD delta; this does not establish hours-long memory trends.
* Ruff, format, compileall, deterministic builder, manifest and Streamlink 8.6.2 plugin discovery pass.
* No live source is currently available. 2 h, 6 h, live controlled-recovery and current-hash live verification remain NOT TESTED.

### Latest test-only follow-up

After adding six bounded H.264 V16 SEI-envelope tests (payload types 213–215),
source pytest is **784 passed, 0 skipped** and bundled parity is **775 passed,
0 skipped**. The source count includes nine single-file construction tests.
The production bundle remains SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
VSEI payload semantics are not interpreted. No live or endurance evidence was
added; Stable remains **NO-GO**.

The subsequent deterministic TS-scanner, near-valid H.264 and ADTS mutation
regressions, plus the repeated StreamIO lifecycle smoke, are included in the
latest counts above. They are bounded checks, not a fuzzing campaign or
long-duration test.

**Campaign: PARTIAL. Stable: NO-GO.** This is an offline hardening candidate; it does not replace current-build live or endurance gates.

The generated-media soak was subsequently extended to 1,800 media seconds and
passed VCL/AAC identity, full decode, TS integrity and StreamIO drain. It ran in
89.335 wall seconds and is an accelerated POC-2 synthetic test, not 30-minute
real-time endurance or evidence of a stable six-hour process. The campaign and
Stable decisions do not change.

## Offline timeline-soak follow-up — 2026-11-03

Current branch HEAD: `b1adbfc419ce834315ddab3ea864ca3a1cc2d0f6`. The production
bundle is unchanged at SHA-256
`c75fa14b537582f91cf64527a68d21d0914562ae07e60002a637ec7dfd519297`.
Offline source/bundle regressions pass 784/775 with zero skips. A separate
generated 10-minute POC Type-2/AAC timeline passed StreamIO drain, payload
identity, full FFmpeg decode, TS continuity/PSI/PCR checks and unchanged FD
count. This is not a real-time or live soak. The user currently cannot provide
an authorized test broadcast, so exact-current-build live, 2-hour, 6-hour and
controlled-failure stages remain NOT TESTED. **Campaign PARTIAL; Stable NO-GO.**

Additional accelerated 1,800-second synthetic media timeline: PASS for the
tested POC-2/no-reorder fixture. This is not 30-minute real-time endurance and
does not establish six-hour process stability.

An accelerated 7,200-second synthetic POC-2/AAC timeline also passed the full
TS and decode gates. It took 356.393 wall seconds; its harness peak RSS was
1,082,268 KiB while retaining generated media and parsed AUs. This is not a
two-hour wall-clock receiver run or a product-only memory measurement.

## Historical MMCO-5 candidate — superseded

* Base commit: `b070755ed1f1593714575c3813ace1bc64da221e` on `fix/grid-startup-readiness`.
* Candidate source commit: `c149834f6ad98cdaac52b6559b5067e09efa4fcf` (pushed; historical).
* Bundle SHA-256: `00af27789d671d5230499c551bbd7c49f27727585b3b6b57faabac05ae886cef`.
* This candidate fixes the MMCO-5 POC reset state for the tested frame-coded subset and adds independent synthetic POC 0/1/2 StreamIO, TS, payload identity and decode tests.

| Gate | Status | Evidence / gap |
|---|---|---|
| Source full regression | Historical PASS | 771 passed, 0 skipped; preserved untracked suffix test excluded |
| Bundle full regression | Historical PASS | Candidate bundle: 762 passed, 0 skipped; standalone bundle tests: 9 passed |
| Ruff / format / compileall / deterministic build | PASS | Changed tracked files formatted; deterministic SHA check and manifest pass; untracked suffix file untouched |
| MMCO-5 offline | PASS for narrow subset | POC 0/1/2, one progressive no-B/one-reference fixture; independent decode/hash, StreamIO/TS, VCL identity, EOF/drain |
| MMCO-5 live / arbitrary DPB | NOT TESTED | User confirmed offline-only; no arbitrary reference-list proof |
| Previous 30-minute live run | Historical PASS WITH MEASURED EDGE LIMITS | It was performed on bundle `5c1657d5…`, not this candidate; strict A/V full-edge gate was false |
| 2 h / 6 h exact-candidate endurance | NOT TESTED | User cannot provide a test broadcast; offline-only |
| Controlled live recovery | NOT TESTED | Requires an authorized broadcast session |

## Decision

This section records an earlier candidate and its evidence; the latest candidate is documented above. Do not use these counts or bundle hash as current-candidate validation.

**Stable: NO-GO.** This historical candidate had offline MMCO-5 evidence but no matching live or endurance evidence. The previous 30-minute run is on another bundle, its strict full-edge A/V gate remained false, and 2-hour, 6-hour and controlled live recovery stages were unrun.

**Beta: CONDITIONAL** for the previously validated bounded subset. Do not imply live MMCO-5 support, arbitrary H.264/DPB support, or long-run stability from the new synthetic fixture.

Reconsider Stable only after 2-hour and 6-hour tests on one immutable candidate, full decode and integrity checks, source-relative sync, resource trend, EOF/drain and controlled recovery.

## Offline-only six-hour timeline follow-up — 2026-11-03

The latest bounded offline helper processed 21,600 seconds of generated POC-2
H.264/AAC media in 1,079.679 seconds wall time through one continuous
StreamIO/MediaSink run. Payload identity, full TS checks, FFmpeg decode and
EOF/drain passed (details in `ENDURANCE_RESULT.md`). This is not six hours of
wall-clock operation and does not satisfy live, pacing, sync, recovery, or
receiver-only resource-trend gates. The user confirmed no authorized test
broadcast is currently available. Campaign remains PARTIAL and Stable remains
NO-GO.

The corrected helper lowers fixture working-set pressure by parsing one
continuous AAC source and processing 10-minute video chunks; its 21,600-second
synthetic run passed with 467,568 KiB sampled process RSS. This remains a
harness-inclusive offline measurement, not product-only memory trend evidence.

The corrected run completed 21,600 media seconds in 1,067.107 wall seconds,
with 216,000 VCL NALs and 1,012,501 AAC AUs identical across input/output and
full TS/decode/EOF checks passing. Current source/bundle regressions are
789/780 passed, zero skipped. The offline suite also covers a 44.1 kHz stereo
AAC end-to-end fixture and confirms the soak timeout terminates its child
process. This does not satisfy live or wall-clock
endurance. Stable remains NO-GO.
