# MPEG-TS PCR compatibility audit

Normative reference: ITU-T H.222.0 (08/2023), ISO/IEC 13818-1:2023, clause 2.7.2 requires PCR base fields on a program's PCR PID no more than 100 ms apart; PCR bytes and transport order matter, in addition to the encoded clock values: <https://www.itu.int/rec/dologin_pub.asp?id=T-REC-H.222.0-202308-S%21%21PDF-E&lang=e&type=items>.

## Current behavior

`soop_grid/mpegts.py` uses video DTS as the program media clock and emits PCR on PID `0x100`, which the PMT declares as PCR PID. For a positive DTS delta up to 2 seconds, it inserts PCR-only adaptation-field packets at 9,000 ticks (100 ms) between the previous and next video PES. PCR base is encoded modulo 2^33 with extension zero. Adaptation-only packets use AFC 2, adaptation length 183, PCR flag set, and retain the previous payload continuity counter. PES PTS/DTS and H.264/AAC payload bytes are unchanged. Non-increasing PCR and deltas over two seconds are rejected before mux state mutation.

The initial public version placed PCR on each video PES without bounded interpolation. A timestamp gap therefore yielded the same large PCR gap; it was not covered by a two-second failure bound.

## Deterministic test results

* Exact 100 ms interval: verified at the boundary.
* 101 ms, 231 ms, 500 ms, and 2 seconds: PCR-only packets keep encoded PCR gaps at or below 100 ms.
* 231 ms real encoded-AU test: inserts samples at +100 ms and +200 ms, preserves the original video PES H.264 byte count/SHA-256 and AAC PES payload byte count/SHA-256, has zero TS continuity and PSI CRC errors, and passes the independent recording verifier and full FFmpeg decode.
* PCR 33-bit wrap: encoded values wrap while the internal unwrapped DTS timeline remains increasing.
* Greater than 2 seconds and PCR regression: rejected, with state unchanged.

## Important limit

The inserted PCR-only packets are serialized immediately before the next video PES. They regularize PCR values in the file but do not schedule/pacer-deliver packets across the elapsed wall-clock interval. A 231 ms gap in timestamps may represent a delayed packet, absent video with continuing audio, or actual missing media; PCR interpolation alone cannot distinguish these. It does not prove content continuity or reconstruct missing pictures. Real-time pacing and long-term A/V drift were not measured in this task. No live recording was performed.
