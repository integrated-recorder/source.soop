# H.264 RBSP CPU optimization

## Change

`h264clock.rbsp()` now locates zero-run boundaries with `bytes.find()` and
constructs the RBSP from unchanged byte slices. It retains the prior header,
emulation-prevention-byte (EPB), invalid-sequence, terminal CABAC byte, and
trailing-zero behavior. The production VCL path converts each NAL to RBSP once
and reuses those bytes for PPS-ID extraction and slice-header parsing.

The previous byte-wise implementation is retained only as a test oracle in
`tests/test_h264clock.py`; it is not present in the production bundle.

## Differential evidence

The optimized implementation was compared against the prior implementation:

* 136,717 exhaustive inputs: seven NAL types, payload bytes 0–4, lengths 0–6.
* 100,000 seeded random inputs, each with a supported NAL type and payload up
  to 4 KiB.
* Directed EPB, malformed EPB, forbidden start-code byte, terminal CABAC EPB,
  header, and trailing-zero cases.
* Project tests also compare encoded B-picture VCL NALs against the oracle.

All successful RBSP bytes and all error codes matched. The permanent test suite
keeps 27,342 exhaustive short inputs, 5,000 seeded random inputs up to 8 KiB,
directed boundary cases, and encoded VCL coverage.

## Offline performance sample

Python 3.12, one process, five timed repetitions after warmup. Input was a
locally generated 10-second 1920×1080, 60 fps, nominal 8 Mbit/s H.264 stream
(600 access units; POC type 2; no B-frames). This is an offline CPU benchmark,
not a network-receive or live-stream result.
Input fixture SHA-256:
`3b8f4e358155a479cac49facf7779022df4f8deca79d0977b3d392dcb65f3b7c`.

| Measurement | Before median (p95) | After median (p95) | Speedup |
|---|---:|---:|---:|
| RBSP for all 600 VCL NALs | 0.933 s (0.939 s) | 0.00645 s (0.00649 s) | 144.7× |
| PPS ID plus slice-header parse | 1.873 s (1.898 s) | 0.0207 s (0.0208 s) | 90.5× |
| Full `MediaSink` pass | 2.175 s (2.194 s) | 0.277 s (0.281 s) | 7.85× |

`H264Clock.inspect()` used 2,432 RBSP conversions before and 1,832 after:
600 VCL conversions were removed, saving 10,361,335 repeated input bytes over
the 600-frame sample. Peak RSS was 53,760 KiB in both runs; traced peak
allocation was 383,503 bytes before and 383,456 bytes after.

Ten independent worker processes each processed the same 600-frame sample.
Aggregate CPU time decreased from 22.22 s to 3.09 s (7.2×); wall time
decreased from 6.88 s to 1.02 s. Each worker produced the same TS digest.

## Output integrity

Before and after `MediaSink` output was exactly 10,676,896 bytes and had the
same SHA-256:

`4613749bfaeb6faa2cb476f4d77d381ec064153681938ceb93d6e7955e40db49`

FFmpeg decoded both complete outputs successfully. The benchmark fixture is
video-only; AAC behavior is covered by the unchanged AAC regression suite.

The final single-file bundle SHA-256 is
`ac9b2eb458586ee35c89574dca1867b1e8bd8f0dd928d61dfa09669b86e75d3b`.
Source tests: 806 passed. Bundle parity tests: 797 passed. Sixteen loopback
socket cases were excluded because this execution environment denies local
socket creation; those cases do not exercise the changed H.264 parser.

## Scope and limits

The microbenchmark uses synthetic but genuinely encoded H.264. It isolates
CPU processing from Grid networking. Timing is specific to this host and Python
build. The optimization changes RBSP parsing work only; it does not claim a
live-stream or long-duration CPU measurement.
