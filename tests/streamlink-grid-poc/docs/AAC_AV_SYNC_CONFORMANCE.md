# AAC and A/V synchronization conformance

Scope: `soop_grid/aac.py`, `soop_grid/media.py`, `soop_grid/mpegts.py`, StreamIO output. This document distinguishes parser correctness, stream-span checks and measured source-relative sync.

## AAC subset

`parse_adts()` bounds payload to 4 MiB and 8192 ADTS frames; it validates sync/layer, sample-rate index, profile syntax, channel configuration, frame length, CRC-layout bounds and exact chunk exhaustion. It returns read-only frame views and exact core-sample duration. The parser can describe 1–4 raw data blocks, but production `MediaSink` accepts AAC-LC only and rejects any ADTS frame with more than one raw data block. It rejects channel configuration 0/PCE, in-capture configuration changes, timestamp regressions and unexplained sample-clock discrepancy. Input AUs are not decoded or rewritten by the parser.

ADTS ASC/profile fields do not prove decoded output characteristics for implicit SBR/PS. The current product path is limited to the validated SOOP AAC-LC/ADTS subset. Other object types and unsupported ADTS structures fail closed.

## Clock and output

Audio timing is accumulated from AAC core sample counts at the signaled rate, anchored to the shared media origin. Grid audio-message count is not treated as AU count. PES carries original ADTS payload with output timestamps; PCR is derived from video DTS. Per-chunk and cumulative audio clock checks reject regression or a discrepancy at least one AU long. A/V final coverage compares observed track spans and start boundaries; it is not a perceptual lip-sync measurement.

## Evidence

Historical short self-broadcast trials recorded exact AAC AU interval identity and full audio decode for the tested synthetic stream. A separate earlier two-hour artifact has source-relative marker results in `STABLE_CANDIDATE_VALIDATION.md`; it is not the current build. No current exact-bundle A/V marker test, 2-hour run or 6-hour run was performed in this campaign. The local test suite exercises sample-clock parsing, mixed media and TS output but does not substitute for source-relative drift measurement.

Current offline E2E also exercises 43 AAC-LC AUs at 44.1 kHz stereo alongside a 30-frame POC-2 video fixture through `MediaSink`, StreamIO and MPEG-TS. FFprobe reports 44.1 kHz/two channels, all source AAC raw data blocks and video VCL NALs match after demux, full FFmpeg decode succeeds, and EOF/drain accounting matches. This is a short synthetic format/transport check, not source-relative synchronization or long-duration evidence.

## Required follow-up

For an authorized self-broadcast, insert numbered audio clicks and video flashes at a known cadence; retain a bounded source reference and output for the same interval. Report initial offset, additional offset, maximum and p95 offset, fitted drift (ppm), missing markers and uncertainty. Require the exact test Bundle SHA, same capture interval and complete decode before interpreting the result. Do not infer long-term sync from one short sample or track-span coverage alone.
