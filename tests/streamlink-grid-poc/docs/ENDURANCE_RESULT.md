# Exact-candidate endurance result

## Candidate and environment

* Branch: `fix/grid-startup-readiness`
* Commit: `b070755ed1f1593714575c3813ace1bc64da221e`
* Bundle `dist/soop_grid.py` SHA-256: `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`
* Linux x86_64, Python 3.12.3, Streamlink 8.6.2
* FFmpeg/FFprobe available to this run: 6.1.1 (Ubuntu build), with libx264; not the 9.0.2 documented by earlier validation reports
* Available filesystem space before live tests: approximately 198 GB

## Offline verification performed

| Check | Result |
|---|---|
| Source pytest, excluding preserved untracked `tests/test_suffix_latejoin.py` | Initial run: 764 passed, 2 skipped. Supplemental run after replacing the encoder-specific fixture: **767 passed, 0 skipped, 50.47 s** |
| Bundle pytest, excluding preserved untracked `tests/test_suffix_latejoin.py` | Initial run: 755 passed, 2 skipped. Supplemental run on the same production bundle: **758 passed, 0 skipped, 44.43 s** |
| Former skip 1 | `tests/test_h264clock.py:285`: now runs with a real libx264-generated POC-2 fixture; independently decoded and full TS path passes |
| Former skip 2 | `tests/test_h264clock.py:409`: now runs against the same fixture and passes its malformed B-slice/reordering rejection check |
| Initial sandboxed source run | Not a product failure: 14 local TCP/socketpair tests raised `EPERM`; rerun outside sandbox passed |
| Ruff check | PASS |
| Ruff format check on tracked project paths, excluding preserved untracked suffix test | PASS: 54 files already formatted |
| `compileall` | PASS |
| Deterministic bundle `--check` | PASS; reproduced SHA-256 above |
| `git diff --check` | PASS before report edits; rerun at finalization |
| Streamlink 8.6.2 plugin load | PASS: `streamlink --plugin-dir plugins --plugins` lists both `soop` and `soop_grid` |
| Bundle SHA256SUMS | PASS: verified from `dist/`; `soop_grid.py: OK` |

The project-local alternate FFmpeg executable could not be launched because its isolated runtime dependency set is incomplete (`libpulsecommon-16.1.so`, then `liblapack.so.3` were unavailable on its loader path). No package installation or network download was performed. The system FFmpeg 6.1.1 libx264 encoder now generates the POC-2 no-B fixture; its emitted SPS is checked for `pic_order_cnt_type=2`, zero reorder, and non-fixed VUI timing, and FFmpeg independently decodes it. The two encoder-dependent skips are therefore closed without relaxing assertions.

The supplemental test-fixture change does not alter production sources. The deterministic single-file bundle remains SHA-256 `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.

## Live and endurance stages

The first environment check looked only for process environment variables and incorrectly concluded that no test credentials were configured. A later permissions-safe check found the user's existing mode-0600 test configuration outside the repository; it was used only by the private harness, with values kept out of logs and reports. The user also confirmed an authorized test broadcast. The exact bundle hash above was copied into the isolated receiver plugin for the following tests.

| Stage | Outcome | Evidence / scope |
|---|---|---|
| Offline smoke | PASS | Source and bundle suites listed above; synthetic cases only. |
| Live 120 s pilot | PASS | Self-owned synthetic broadcast; exact bundle; 7,457 VCL / 5,808 AAC AUs form contiguous byte-identical source intervals; SPS/PPS identical; 7,371 pictures fully decoded; B pictures present; TS and timestamp checks pass. Source continued beyond receiver cutoff; event misses are proven right-censored tail only. |
| 10 min | PASS — receiver capture; publisher cleanup disclosed | Exact bundle; receiver exit 0 at 600 s; H.264 High, 1920×1080, POC type 0, B pictures; 36,284 VCL / 28,344 AAC AUs match contiguous source intervals; SPS/PPS identical; full TS/FFmpeg validation pass. 1,052,629 TS packets, continuity/PSI CRC/PCR regression errors 0, max PCR delta 17 ms, DTS regression 0. A/V 240 common events, added offset median 0.333 ms, max/p95 0.667 ms, measured drift 0.224 ppm over 602.3 s. |
| Looped-source seam smoke | REJECTED as an endurance fixture | RTMP input loop had a 4 ms audio timestamp overlap in the local reference and a 20.667 ms A/V offset jump at the seam despite Grid sequence continuity. Not attributed to the receiver. |
| 30 min | PASS WITH MEASURED EDGE LIMITS | Exact bundle; authorized self-owned non-looping 1080p60 H.264 B-frame + AAC-LC 48 kHz stereo broadcast; receiver and publisher exit 0; 1,800.24 s, StreamIO drain complete, emitted/read/accepted bytes equal (590,853,840), discarded/unaccepted 0. Grid sequence gaps/discontinuities 0; one Parent, no failover/recovery. Source/Grid contiguous identity: 108,115 VCL and 84,456 AAC AUs; SPS/PPS equal. Output TS: 3,144,607 packets, 3,602 valid PSI sections; 108,035 video PES / 3,519 audio PES; TS continuity, PSI CRC, PCR regressions, DTS regressions, duplicate PTS and PTS/DTS mismatches 0. Full FFmpeg H.264/AAC decode passes for 1,800.62 s video and 1,801.73 s audio. Independent TS/PES checker passes. First 80 captured video preroll chunks (492,902 bytes, before decodable IDR) are excluded; no interior/suffix coded video bytes are excluded. |
| 30 min A/V event sync | PASS FOR COMMON OVERLAP; strict full-edge gate not met | 1,929 common controlled flash/click events across 1,799.167 s; added offset median 0.333 ms, max/p95 0.667 ms; fitted drift −0.002615 ppm (−0.00157 ms per 600 s). Matched event IDs are contiguous over captured overlap; initial source event IDs 0–1 (video) / 0 (audio) precede receiver coverage and the finite source has a censored tail. Audio onset detector found 11 unmatched observed onsets versus 16 in the source/reference detector baseline; treated as detector artifacts, not hidden media loss, because AAC AUs are byte-identical. The original strict `validation-gate.json` remains `passed=false` due edge/detector coverage conditions; overlap timing metrics meet limits. |
| 2 h | NOT_TESTED — unavailable | User confirmed no test broadcast is currently available; remaining work is offline-only. |
| 6 h | NOT_TESTED — unavailable | User confirmed no test broadcast is currently available; remaining work is offline-only. |
| Endurance with controlled failures | NOT_TESTED | Clean 10 min run had no failover/recovery event, so recovery is not evidenced. |
| Source-relative sync/resource trend | VERIFIED_FOR_30_MIN_CLEAN_RUN | 361 samples / 5 s: RSS peak 59,364 KiB; FD peak 13; threads peak 3; 195.58 CPU seconds over 1,800.24 s. No recovery/failover event occurred in this clean run. |

Prior long-run and 30-minute reports concern other bundle hashes. They are useful historical evidence but do not pass the exact-candidate release gate.

## Result

This candidate passes the executed offline regression gates and has passed 120 s, 600 s, and 1,800 s authorized synthetic self-broadcast captures on the exact bundle. The 30 min receiver and publisher both exited cleanly. Coded media identity, TS/PES, independent timestamps, full decoding, EOF/drain, and source-relative A/V timing over the common event interval passed. Startup/finite-capture event edges remain measured exclusions; the strict full-coverage A/V gate is not green. No production code changed. The user has since confirmed no further test broadcast is currently available, so 2 h, 6 h, and controlled-failure live endurance remain untested. Stable remains **NO-GO**.
