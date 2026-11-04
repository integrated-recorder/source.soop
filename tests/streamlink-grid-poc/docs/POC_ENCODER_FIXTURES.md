# POC encoder and fixture evidence

All media used here is generated synthetic test content. No broadcast-origin media is included. The live source masters were held in a mode-0700 temporary directory and are not part of Git.

## Toolchain

* FFmpeg/FFprobe 6.1.1 (Ubuntu build), with libx264 and AAC encoder.
* Python 3.12 test environment; Streamlink 8.6.2.
* `libopenh264` is absent. The former tests that required it now use libx264 for their real POC-2 no-B fixture; the SPS is parsed and checked, and FFmpeg independently decodes the elementary stream. This removes the environment-specific skips without weakening the fixture assertions.

## Deterministic offline fixtures

`tests/test_poc_type_e2e.py` generates 30-frame 320x180 streams and AAC-LC ADTS audio at 48 kHz, then sends Grid-shaped media through the real production `MediaSink`, `SoopGridReader.open/read/close`, buffer/consumer, TS mux and EOF/drain paths.

* Type 0: libx264 Main/CAVLC, 2 B frames, repeat headers; generated SPS is parsed and asserted to signal type 0.
* Type 1: a standards-conforming syntax transformation of that Type-0 bitstream. It changes the SPS POC model to a one-entry reference cycle and writes slice deltas to preserve the source POC values; coded macroblock data is copied. FFmpeg full decode succeeds, and decoded frame hashes equal the original Type-0 stream.
* Type 2: libx264 Baseline, no B frames; the emitted SPS is parsed and asserted to signal type 2 and zero reorder.

The POC-2 no-fixed-clock fixture used by `tests/test_h264clock.py` is generated with libx264 Baseline, 60 frames at 30 fps, `bframes=0`, repeated headers and a 30-frame key interval. The actual emitted SPS is asserted to have POC type 2, no fixed VUI timing and a signaled zero-reorder bound. The raw stream is decoded independently before the production clock/mux test runs. Two independent executions of the fixture command produced the same SHA-256: `3a18cfe163a16a233c778725a8d70094c26ceab1be9a0b24b6b7f987d1c9cca8`. The generated SPS is Baseline, 160×96, POC type 2, MaxFrameNum 16, max reference frames 3, gaps disallowed, zero reorder, 30 fps; the stream has 60 coded slices and no B-slices. The B-slice syntax test uses that valid SPS/PPS as a prefix and confirms the production parser rejects a B slice when zero reorder is required; it does not claim that the synthetic partial slice is a decodable picture.

This is not claimed to be an encoder-native Type-1 mode. It is an independently decoded, valid Type-1 coded stream used to exercise the production parser/muxer. The transformer rejects unsupported source features such as MMCO 5 and unsuitable PPS/SPS syntax.

An additional no-B Type-1 fixture exercises
`delta_pic_order_always_zero_flag=1`: it starts from the independently
decodable progressive POC-2 libx264 stream, replaces the SPS POC syntax with a
one-entry +2 reference cycle, and leaves slice syntax unchanged. The emitted
SPS is reparsed and asserted as Type 1 with the flag set; FFmpeg frame hashes
match the POC-2 source. It traverses the production H264Clock and
MediaSink→StreamIO→MPEG-TS path, preserves VCL NALs and AAC AU payloads, and
passes full TS decode and EOF/drain. This is a syntax-derived conformance fixture, not a native
Type-1 encoder mode. The available encoder inventory was rechecked: the local
FFmpeg exposes libx264, but no JM reference encoder, `lencod`, or OpenH264
encoder was found, so native Type-1 encoder output remains unavailable here.

A second Type-1 header transform toggles the PPS
`bottom_field_pic_order_in_frame_present_flag` and inserts
`delta_pic_order_cnt[1]=0` after each parsed `delta_pic_order_cnt[0]`. Its
offset constraints are checked before transformation. The SPS/PPS/slice
headers are reparsed, every inserted `delta_poc1` is asserted to be zero, and
the derived stream's per-picture `frame_num` and `delta_poc0` match the
pre-transform stream. FFmpeg frame hashes match. This extends the Type-1
parser/E2E fixture subset; it is not native encoder output.

A third Type-1 variant uses an empty reference POC cycle and
`offset_for_non_ref_pic=-1`. Slice deltas are derived from the source Type-0
POC so reference and non-reference display order is retained. The resulting
SPS is checked for a zero-length cycle and the signed non-reference offset;
H264Clock POC values are compared picture by picture and FFmpeg frame hashes
match. It passes the production Parent/StreamIO/TS path and is not native
Type-1 encoder output.

## Short live-broadcast masters

The three 20-second synchronized masters use generated 640x360 video and AAC-LC stereo. Eight irregular one-frame flashes are paired to 5 ms audio clicks at the same source times. The following hashes identify the exact synthetic Matroska inputs used in the marker-enabled SOOP tests:

| POC | Fixture SHA-256 | Encoding / tested stream shape |
|---:|---|---|
| 0 | `7ef1fe04b94d1b9d766dd39884662831986cab846f65bdeffd8b3add0ec9188a` | libx264 Main/CAVLC, B pictures |
| 1 | `e47b1c99e530882f66c63971eef5ee639bb5b371b71c4e8c537ca3a50aeffbc4` | Type-2 low-delay source with SPS converted to Type 1, one-entry +2 cycle; no B pictures |
| 2 | `030d8fabc3ff315440fee6daee19459002469e8e23b5ecadf23a07dd3fa58421` | libx264 Baseline, no B pictures |

The source masters independently pass full FFmpeg decode. Their actual SPS values—not encoder command-line intent—were checked. POC 1 is a constructed test stream, not an encoder-native Type-1 claim. All three live masters carry no MMCO 5.

## Safety of fixtures

The offline generators are reproducible from the repository tests and local FFmpeg toolchain. The hashes above are for synthetic A/V marker masters only. They contain no credentials, channel identifiers, broadcast URLs or received payloads.
