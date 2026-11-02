# V3/V5/V8 Compatibility Findings

## H.264 `frame_num` report

The current receiver checks each non-IDR picture against the preceding reference
picture's `frame_num`, using the active SPS `MaxFrameNum`. With
`gaps_in_frame_num_value_allowed_flag == 0`, the next value is exactly
`(PrevRefFrameNum + 1) % MaxFrameNum`. `MaxFrameNum` is a power of two. Thus
119 → 1 is not a normal modulo wrap for MaxFrameNum 128 or 256: the expected
successor is 120. A preceding MMCO5 changes the value used for subsequent
reference-number checks to zero, in which case 0 → 1 is valid. IDR and SPS/PPS
state boundaries also matter. The report does not include the SPS, slice
`nal_ref_idc`, intervening access units, or MMCO5 state, so its particular
119 → 1 transition cannot be classified from the report alone.

`gaps_in_frame_num_value_allowed_flag == 1` permits the decoder's specified
non-existing reference-picture process; it does not authorize the recorder to
invent media or silently repair a damaged reference chain. POC types 0, 1, and
2 change picture-order state, not the SPS successor rule. This implementation
continues to preserve POC/display-order checks and rejects unsupported or
contradictory states. Continuous Grid message numbering establishes continuity
of the observed Grid wrapper sequence, not completeness of H.264 pictures
inside those messages.

**Result: UNVERIFIED for the reported V8 case; no compatibility relaxation.**
The modulo rule is factored into a directly tested helper. Regressions verify
that 119 → 1 is rejected for MaxFrameNum 128, 127 → 0 is accepted, and the
successor after MMCO5 uses zero state. These are syntax-state tests, not a
reproduction of the reporter's unavailable bitstream. No H.264 payload,
timestamp, reference state, or POC validation is altered to make the report
pass.

## PCR interval report

The muxer emits PCR on the video PID (`0x0100`) from its existing unwrapped
90 kHz video DTS clock. For a positive DTS interval up to 180,000 ticks (2 s),
it now inserts at most 19 PCR-only packets at 9,000-tick steps before the next
video PES. The PCR-only packets use adaptation-field-only control, length 183,
PCR flag set, 33-bit base modulo wrap, extension zero, and the prior payload
continuity counter (adaptation-only packets do not increment it). The following
video packet carries the actual DTS as PCR. PTS/DTS and H.264/AAC elementary
payloads remain unchanged. Backward/equal clocks and intervals over 2 s remain
errors; the two-second value is a bounded recovery policy, not a general
standard limit.

The deterministic 231 ms case inserts PCR values at 100 ms and 200 ms, then
the original 231 ms DTS. Tests also cover 101 ms, 500 ms, the 100 ms boundary,
2 s, 2 s + 1 tick, 33-bit wrap, adaptation-field layout and continuity
counters. A locally encoded H.264/AAC fixture traverses the muxer, passes the
independent TS scanner, and decodes with FFmpeg/FFprobe. No real broadcast
capture or wire-arrival timestamps were available. The independent repository
verifier explicitly checks PCR-value progression from a file; it is not a
measurement of real-time PCR packet arrival or a paced constant-bitrate
transmission. The result therefore validates the emitted file's clock samples
and decoding, not a live transport pacing guarantee or the reporter's exact
source capture.

**Result: PARTIAL for the reported V8 case.** Bounded interpolation resolves
the receiver's 100 ms value-gap rejection on verified file/mux inputs while
preserving payload and PES timestamps. A real 231 ms Native Grid capture is
still needed to establish that this matches the reporter's source-clock and
audio interleave conditions.

## V3/V5 timing reports

Production no longer derives presentation timestamps from HRD-only legacy
timing. It uses validated Grid composition timing and continues to check POC
against PTS order, reorder bounds, DTS monotonicity, and timestamp bounds.
Existing regressions retain the old HRD/POC conflict and invalid reorder-bound
rejections in the legacy audit path, while the Grid-composition comparison
verifies that an HRD DPB value does not override explicit Grid composition.
The full source and bundled suites pass with those regressions. This does not
replay the reporters' original V3/V5 payloads; their per-case results remain
**UNVERIFIED** without those inputs.

## Standards and evidence boundary

The frame-number rule is in [ITU-T H.264 (08/2024), clause 7.4.3 and the
frame-number gap process in 8.2.5.2](https://www.itu.int/rec/T-REC-H.264-202408-S).
H.222.0 clause 2.7.2 specifies the maximum time interval between successive
PCR fields in a transport stream; [ETSI TS 101 154 clause 4.1.5.3](https://www.etsi.org/deliver/etsi_ts/101100_101199/101154/01.08.01_60/ts_101154v010801p.pdf)
repeats the 100 ms PCR-value interval for DVB use. These specifications do
not establish the proprietary SOOP Grid timestamp's source-clock semantics or
prove that a user's 231 ms report had the same cause as the synthetic test.
