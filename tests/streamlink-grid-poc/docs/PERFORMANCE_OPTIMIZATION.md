# Native Grid CPU optimization evidence

## Scope and environment

This report compares the production path after the RBSP optimization with three independent candidates: preallocated MPEG-TS packetization, reuse of an already validated ADTS parse result, and avoiding per-frame JSON work when diagnostic capture is disabled. No SOOP connection or live recording was used.

Measurements ran on Linux, Python 3.12.3, Streamlink 8.6.2, and an Intel Core i5-4570 at 3.20 GHz (4 logical CPUs). A locally generated 10-second 1920x1080, 60 fps, nominal 8 Mbit/s H.264 input contains 600 access units and uses POC type 2 without B-frames. Its SHA-256 is `3b8f4e358155a479cac49facf7779022df4f8deca79d0977b3d392dcb65f3b7c`. The AAC input is a 10-second 48 kHz stereo AAC-LC ADTS sine fixture with 470 access units; SHA-256 `04733c88e22f0bdf4ba1f1f84647597adac333a2fd8ad12de74b84ffa885f11f`. The inputs are synthetic and locally encoded, not network captures.

The end-to-end workload feeds 600 video access units and 94 five-AU audio chunks through `MediaSink`, including the normal timestamp, identity hash, PES, and TS paths. Variants were warmed and measured in randomized order for nine repetitions. The “prior” variants execute the equivalent pre-optimization work while using the same current process, fixture, interpreter, and H.264 implementation. Results are offline CPU timings; they do not represent live network throughput or latency.

## Initial profile

The initial profile attributed the largest directly optimized allocation and loop cost to `TSMux.packetize()`: it made a 188-byte `bytearray`, converted each packet to `bytes`, retained a list, and joined the packet list for every PES. The initial 600-frame A/V run took about 0.29 seconds of process CPU. The previous RBSP work had already reduced the H.264-only path substantially; this change set did not revisit or weaken it. In the baseline profile, packetization accounted for about 0.141 CPU seconds (roughly 28% of the profiled run). ADTS parsing ran once per audio chunk in the sink and again in the mux, plus one additional parse for first-frame metadata. In the ordinary no-capture run, each of the 694 media events also built and serialized a frame record that had no output file.

## Candidate A/B results

Times below are median process CPU seconds (p95 in parentheses). The complete output SHA-256 was `faafe87a15d7a6d4e045b64dbf41cc3fee6fe8f734ab9065be1b4448081e58bb` for every variant; each emitted 10,853,616 bytes, 600 video frames, and 470 AAC access units.

| Candidate | Prior implementation | Candidate | CPU change | Decision |
|---|---:|---:|---:|---|
| OPT-01 packetization | 0.27244 s (0.27814) | 0.24775 s (0.25286) | 9.1% lower | Adopt |
| OPT-01 alternative preallocated slice-header variant | 0.25815 s (0.26039) | Scalar header stores: 0.24775 s (0.25286) | scalar variant 4.0% lower | Keep scalar-store variant |
| OPT-02 repeated ADTS parsing | 0.25332 s (0.25477) | 0.24775 s (0.25286) | 2.2% lower | Adopt |
| OPT-03 disabled frame JSON diagnostics | 0.26289 s (0.26439) | 0.24775 s (0.25286) | 5.8% lower | Adopt |
| Combined prior behavior | 0.28841 s (0.29049) | 0.24644 s (0.25144) | 14.6% lower | Adopt all three |

The packetizer now computes packet count and fills one output buffer. The existing TS header, adaptation field, PCR, payload, stuffing, and continuity logic is preserved. `tests/test_mpegts.py` retains the prior packetizer as a test oracle and checks byte equality at packet boundaries, PCR/no-PCR cases, 33-bit PCR values, large inputs, and 250 fixed-seed random inputs.

The ADTS result is parsed and validated once in `MediaSink`, then passed to the mux and first-frame audio metadata helper. The mux still performs its LC, configuration, raw-data-block, timestamp, sample-clock, and PES checks. Direct mux callers still invoke `parse_adts()` themselves. Pending preroll retains the parsed immutable result together with the bounded payload until the first video PES drains it.

When no private capture is open, the frame JSON object and `json.dumps()` are now skipped. With capture enabled, the `frames.jsonl` line is asserted byte-for-byte in the regression test.

## Aggregate and memory measurements

With all three optimizations enabled, randomized nine-run A/B measurements were:

| Workload | Prior CPU median | Current CPU median | CPU reduction | Prior wall median | Current wall median |
|---|---:|---:|---:|---:|---:|
| One `MediaSink`, 10-second A/V fixture | 0.28841 s | 0.24644 s | 14.6% | 0.28910 s | 0.24817 s |
| Ten independent processes, one fixture each | 3.09084 s aggregate child CPU | 2.67470 s | 13.5% | 1.03382 s | 0.89190 s |

For one `MediaSink`, the output-byte processing rate increased from about 37.6 MB/s to 44.0 MB/s, based on the 10,853,616-byte output and median CPU time.

The ten-process run produced one identical TS digest and byte count across all workers in each variant. It is a local concurrency stress sample, not ten live streams.

Five traced-allocation runs measured median peak traced memory of 329,560 bytes for the combined prior behavior and 292,002 bytes with the optimizations (11.4% lower). Isolated-process peak RSS was 51,712 KiB before and 51,584 KiB after; this 128 KiB difference is within measurement noise and is not claimed as a material RSS improvement. No unbounded buffers or extra long-lived media copies were introduced.

## Other candidates

| Candidate | Evidence | Decision |
|---|---|---|
| OPT-04 repeated H.264 NAL scan | The profile showed 604 `nals()` calls for 600 video access units, about 0.017 s cumulative under profiling. The normal accepted-frame path scans once in `H264Clock`; additional scans are conditional or startup-only. | Do not change; little demonstrated duplicate work for the interface risk. |
| OPT-05 H.264 state snapshots | `inspect()` and parsing dominate; a snapshot redesign would alter rollback semantics covering POC, parameter sets, MMCO5, and timing. Snapshot-only cost was not shown to be a significant share. | Do not change. |
| OPT-06 StreamIO front deletion | A cursor-buffer prototype was slower for 188, 512, 4096, and 8192-byte reads; at 64 KiB it was within noise. The prototype added cursor/compaction state. | Reject; retain current bounded bytearray. |
| OPT-07 startup retry | Retry is disabled by default and only runs on a bounded startup failure. The steady-state A/V fixture does not exercise retry. | Do not optimize without evidence of a material cost on that exceptional path. |
| OPT-08 recovery SHA-256 | Identity digests protect overlap and duplicate checks. No alternative that preserves the exact identity contract was measured. | Retain full SHA-256 and exact overlap validation. |
| OPT-09 other hot paths | `H264Clock._inspect`, `MediaSink._record_output`, parser work, and payload identity hashes remain visible. No lower-risk candidate had a measured favorable A/B result in this pass. | No further production change. |

The StreamIO prototype used the existing 10.7 MB TS fixture, a 1 MiB bounded buffer, and concurrent producer/consumer threads. Median wall times (current bytearray vs cursor prototype) were 0.149/0.187 s at 188-byte reads, 0.089/0.096 s at 512, 0.108/0.119 s at 4096, 0.051/0.057 s at 8192, and 0.034/0.033 s at 65536. The cursor variant was not adopted.

## Integrity and limits

The pre-optimization packetizer oracle and current packetizer match byte for byte over directed and seeded-random inputs; continuity-counter state matches too. The old and optimized A/V output hashes, lengths, frame/AU counts, PCR, PTS, and DTS therefore match for the benchmark workload. FFmpeg fully decoded both saved TS outputs with `-xerror`; FFprobe reported H.264 1920x1080 and AAC 48 kHz stereo.

The initial restricted source run reported 16 local-loopback failures because the environment denied socket creation; rerunning with local socket permission resolved them. The final tracked-source run, with the available FFmpeg/FFprobe paths supplied, passed **986 tests with zero skips**. The final single-file parity run passed **977 tests with zero skips** under the same media-tool and loopback permissions. The preserved untracked `test_suffix_latejoin.py` is excluded from these release counts and is not part of this change.

The rebuilt bundle SHA-256 is `454584b94785207dc6132e7b3ba02c0a4d28c6d0c05c2b7bad354bfc92bc612e`; the deterministic builder check and `dist/SHA256SUMS` both matched it. Streamlink 8.6.2 loaded the copied bundle through `--plugin-dir` and listed `soop_grid` while retaining the built-in `soop` plugin.

The private synthetic fixtures and temporary benchmark scripts are not included in the repository. No real SOOP stream, ten-stream network capture, startup retry event, or slow-consumer live session was tested.
