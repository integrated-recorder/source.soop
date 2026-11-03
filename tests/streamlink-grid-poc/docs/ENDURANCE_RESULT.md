# Exact-candidate endurance result

## Candidate and environment

* Branch: `fix/grid-startup-readiness`
* Commit: `b070755ed1f1593714575c3813ace1bc64da221e`
* Bundle `dist/soop_grid.py` SHA-256: `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`
* Linux x86_64, Python 3.12.3, Streamlink 8.6.2
* FFmpeg/FFprobe available to this run: 6.1.1 (Ubuntu build), with libx264; not the 9.0.2 documented by earlier validation reports
* Available filesystem space at inspection: approximately 198 GB

## Offline verification performed

| Check | Result |
|---|---|
| Source pytest, excluding preserved untracked `tests/test_suffix_latejoin.py` | PASS: 764 passed, 2 skipped, 62.46 s |
| Bundle pytest, excluding preserved untracked `tests/test_suffix_latejoin.py` | PASS: 755 passed, 2 skipped, 54.80 s |
| Skip 1 | `tests/test_h264clock.py:285`: optional generated POC-2 fixture requires FFmpeg `libopenh264`; installed FFmpeg exposes libx264 only |
| Skip 2 | `tests/test_h264clock.py:409`: same encoder dependency for a second check |
| Initial sandboxed source run | Not a product failure: 14 local TCP/socketpair tests raised `EPERM`; rerun outside sandbox passed |
| Ruff check | PASS |
| Ruff format check on tracked project paths, excluding preserved untracked suffix test | PASS: 54 files already formatted |
| `compileall` | PASS |
| Deterministic bundle `--check` | PASS; reproduced SHA-256 above |
| `git diff --check` | PASS before report edits; rerun at finalization |
| Streamlink 8.6.2 plugin load | PASS: `streamlink --plugin-dir plugins --plugins` lists both `soop` and `soop_grid` |
| Bundle SHA256SUMS | PASS: verified from `dist/`; `soop_grid.py: OK` |

The project-local alternate FFmpeg executable could not be launched because its isolated runtime dependency set is incomplete (`libpulsecommon-16.1.so`, then `liblapack.so.3` were unavailable on its loader path). No package installation or network download was performed. The available FFmpeg can generate and independently decode current fixtures, but not those two optional libopenh264-specific test vectors.

## Live and endurance stages

No new self-broadcast or authorized live session was run in this environment. No SOOP test target/credentials were configured in the process environment at inspection. This records the current execution boundary only; historical short self-broadcast evidence is preserved in `POC_GRID_LIVE_VALIDATION.md` under bundle SHA `e1a1433b…`, and must not be transferred to this candidate.

| Stage | Current exact candidate |
|---|---|
| Offline smoke | VERIFIED by source/bundle suites for their synthetic cases; not a live claim |
| Live 15–30 s | NOT_TESTED |
| 10 min | NOT_TESTED |
| 30 min | NOT_TESTED on this candidate |
| 2 h | NOT_TESTED on this candidate |
| 6 h | NOT_TESTED on this candidate |
| Endurance with controlled failures | NOT_TESTED on this candidate |
| Current-build source-relative sync/resource trend | NOT_TESTED |

Prior long-run and 30-minute reports concern other bundle hashes. They are useful historical evidence but do not pass the exact-candidate release gate.

## Result

This candidate passes the executed offline regression gates. It has no new production-code change from this campaign; the changes are compatibility documentation corrections and a staged validation plan. The candidate is **not Stable-ready** because current-hash live, A/V sync, controlled-live-recovery, 2-hour and 6-hour tests were not run.
