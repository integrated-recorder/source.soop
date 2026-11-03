# Release readiness

Candidate evaluated: `b070755ed1f1593714575c3813ace1bc64da221e`, bundle SHA-256 `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.

## Gate

| Gate | Status | Evidence / gap |
|---|---|---|
| Source full regression | PASS | 764 passed, 2 optional libopenh264 skips |
| Bundle full regression | PASS | 755 passed, 2 optional libopenh264 skips; same candidate code/bundle hash as endurance run |
| Ruff / format / compileall / deterministic build | PASS on tracked project files | Untracked `tests/test_suffix_latejoin.py` was preserved and excluded from format check |
| POC 0/1/2 documented subsets | PARTIAL | Historical short live evidence uses older bundle; Type 1 live B picture absent |
| MMCO 5 | NO-GO | Production intentionally rejects pending complete state/timeline proof |
| AAC and TS integrity | PASS for 30 min exact bundle | 3,144,607 TS packets; 3,602 PSI sections CRC-valid; full H.264/AAC decode and independent PES checks pass |
| Source-relative A/V sync | PASS over 30 min common event overlap; strict full-edge gate not met | 1,929 events / 1,799.167 s; added offset median 0.333 ms, max/p95 0.667 ms; drift −0.002615 ppm. Receiver-start/finite-tail events are censored; detector extras 11 vs 16 in source baseline. |
| Parent recovery | PARTIAL | Deterministic tests and historical controlled case; repeated natural failures not established |
| 2 h and 6 h exact-candidate endurance | NO-GO | User currently cannot provide a test broadcast; not run |
| Current-hash RSS/FD/thread trend | PASS for 30 min clean run | RSS peak 59,364 KiB; FD 13; threads 3; no recovery events |
| 10 min exact-bundle live self-broadcast | PASS (capture) | Receiver exited 0; full TS, H.264/AAC identity and timestamp checks pass. Publisher cleanup hit harness wait limit, but reference covered the captured interval. |
| 30 min endurance | PASS WITH MEASURED EDGE LIMITS | Exact-bundle self-broadcast; full decode and byte identity pass; strict A/V edge gate remains false |
| 2 h / 6 h endurance | NO-GO pending | Not run; no further authorized test broadcast is currently available |
| Remote branch verification/push | BLOCKED at this inspection | GitHub DNS failed in restricted environment; retry only after local report/tests finalized |

## Decision

**Stable: NO-GO.** Exact-candidate 30-minute live capture, full decode, TS/PES checks, source media identity, and overlap A/V sync now exist. The strict A/V boundary gate remains false due measured start/tail censorship and detector artifacts. 2-hour/6-hour endurance and controlled recovery remain untested because no further test broadcast is currently available. The clean synthetic self-broadcast does not exercise recovery or establish arbitrary-broadcast compatibility.

**Beta: CONDITIONAL.** Existing experimental/Beta use may continue only with the documented supported subset, explicit Grid/Auto/HLS semantics, fail-closed behavior and bounded capture settings. Do not advertise MMCO 5, all H.264 structures, long-run stability, or universal A/V sync.

Before reconsidering Stable, execute the staged plan in `ENDURANCE_TEST_PLAN.md` on one immutable bundle and publish only scrubbed metrics with exact hashes.
