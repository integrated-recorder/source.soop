# Short self-broadcast Native Grid validation by H.264 POC type

Date: 2026-11-02. Tested artifact: working-tree production bundle SHA-256 `e1a1433bbcfb67febb37e43b7e92f2761c3f1cd58b4119dfbaa44c5dc0f6029b` (built from branch `fix/grid-startup-readiness`, base HEAD `41309cb826e6a673d597a99423526c2369d5cebc`). Streamlink 8.6.2 received each test through Native Grid. Tests used only synthetic self-broadcast content. No broadcast identifier, URL, credential, received payload or raw packet capture is retained here.

## Method

Each source master was 20 seconds long; the test receiver was limited to 15 seconds, one session at a time. A separate 20-second source/reference path and the Native Grid output were compared. Three marker-enabled trials used eight irregular, paired video-flash/audio-click events. Before broadcast, each master passed full FFmpeg decode and the event analyzer reported all eight markers with zero source A/V offset. The receiver's stdout/stderr and raw Grid capture were disabled; temporary outputs were kept under mode-0700 `/tmp` storage.

Native Grid did not re-encode the tested media: source-to-RTMP reference VCL/AAC access units matched exactly, then the Grid result was an exact contiguous subsequence of that reference. The selected SPS POC type was separately parsed from the source, RTMP reference and Grid TS. This establishes identity for the captured interval, not for source media outside that interval.

## Results

| Source POC | SPS at Grid | Source VCL AUs | Grid VCL AUs | Exact VCL interval | Source AAC AUs | Grid AAC AUs | Exact AAC interval | FFmpeg/TS verifier |
|---:|---:|---:|---:|---|---:|---:|---|---|
| 0 | 0 | 600 | 468 | 468/468, source offset 60 | 937 | 792 | 792/792, offset 24 | PASS |
| 1 | 1 | 599 | 466 | 466/466, source offset 60 | 937 | 792 | 792/792, offset 25 | PASS |
| 2 | 2 | 600 | 466 | 466/466, source offset 60 | 937 | 792 | 792/792, offset 25 | PASS |

All three source, RTMP-reference and Grid SPS NALs were byte-identical. Type 0 and 2 PPS NALs were byte-identical. Type 1 carried an additional byte-distinct PPS NAL variant in the demuxed Grid output; its parsed PPS fields matched the source PPS and VCL payload was byte-identical. The source and RTMP-reference PPS matched exactly. The origin of that extra serialized PPS variant is not established, so this report does not claim byte identity for every non-VCL NAL in Type 1.

| POC | Video pictures decoded | Audio PCM samples/channel | TS packets | TS continuity errors | PSI CRC errors | Maximum PCR-value delta | Marker comparison |
|---:|---:|---:|---:|---:|---:|---:|---|
| 0 | 468 | 811,008 | 19,225 | 0 | 0 | 34 ms | 7 common events; median added offset 0.333 ms, max 0.333 ms, estimated drift 11.1 ppm |
| 1 | 466 | 811,008 | 21,139 | 0 | 0 | 34 ms | 7 common events; median added offset 0 ms, max 0.333 ms, estimated drift 11.1 ppm |
| 2 | 466 | 811,008 | 21,139 | 0 | 0 | 34 ms | 7 common events; median added offset 0 ms, max 0.333 ms, estimated drift 11.1 ppm |

The event analyzer marked one source event outside the clipped capture interval as unmatched in each run; the seven common events were compared. That coverage warning is not counted as a sync pass for the omitted event. The measured offsets are decoded synthetic event timing, not subjective playback or speaker-latency measurements.

Each capture also had zero Grid sequence discontinuities and media gap events, `reader_eof_observed=1`, `stream_output_bytes_drained=1`, equal accepted/read byte counts, zero active sockets after close, and `stop_reason=duration_limit`. The standalone recording verifier passed for every full TS, including PSI/PCR/PES structure, timestamps, H.264/AAC decode, and its 10-second minimum-duration gate. Direct FFmpeg `-xerror` decode also exited successfully.

## Interpretation and limits

* POC 0 was tested live with B pictures (390 B pictures in the source master; 304 in the captured interval). Offline POC 0/1 both exercised B-picture reordering through the production pipeline.
* POC 1 live validation covers a valid constructed, no-reorder Type-1 stream. It does not establish encoder-native Type-1 behavior or live Type-1 B-picture handling.
* POC 2 live validation covers a generated low-delay, zero-reorder sequence. The separate offline syntax tests reject prohibited adjacent non-reference pictures.
* The 15-second duration limit clips the 20-second source. Grid output begins at source VCL offset 60 and audio offset 24/25; omitted leading/trailing source pictures are expected in this bounded capture. The test proves a contiguous preserved interval, not a complete recording of the 20-second master.
* MMCO 5 was absent. Interlaced streams, arbitrary reference-DPB arrangements, unusual Type-1 cycles, live Type-1 B pictures, long-run drift and all SOOP encoder variants remain unverified.
