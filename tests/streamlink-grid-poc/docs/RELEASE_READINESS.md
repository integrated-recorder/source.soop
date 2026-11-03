# Release readiness

Candidate evaluated: `b070755ed1f1593714575c3813ace1bc64da221e`, bundle SHA-256 `5c1657d5eb317c5cd93a03e358046c4dbefcf0b47f343195f07fda0ad3901d17`.

## Gate

| Gate | Status | Evidence / gap |
|---|---|---|
| Source full regression | PASS | 764 passed, 2 optional libopenh264 skips |
| Bundle full regression | Pending final exact run | `ENDURANCE_RESULT.md` |
| Ruff / format / compileall / deterministic build | PASS on tracked project files | Untracked `tests/test_suffix_latejoin.py` was preserved and excluded from format check |
| POC 0/1/2 documented subsets | PARTIAL | Historical short live evidence uses older bundle; Type 1 live B picture absent |
| MMCO 5 | NO-GO | Production intentionally rejects pending complete state/timeline proof |
| AAC and TS integrity | Offline PASS; live current candidate unverified | Historic live tests are other hashes |
| Source-relative A/V sync | NO-GO for current exact hash | No current-hash live marker measurement |
| Parent recovery | PARTIAL | Deterministic tests and historical controlled case; repeated natural failures not established |
| 2 h and 6 h exact-candidate endurance | NO-GO | Not run on this candidate |
| Current-hash RSS/FD/thread trend | NO-GO | Not measured |
| Remote branch verification/push | BLOCKED at this inspection | GitHub DNS failed in restricted environment; retry only after local report/tests finalized |

## Decision

**Stable: NO-GO.** The required exact-candidate 2-hour and 6-hour endurance, source-relative sync and resource-trend evidence do not exist. The current offline suite is strong evidence for the covered synthetic inputs but cannot replace live/endurance gates.

**Beta: CONDITIONAL.** Existing experimental/Beta use may continue only with the documented supported subset, explicit Grid/Auto/HLS semantics, fail-closed behavior and bounded capture settings. Do not advertise MMCO 5, all H.264 structures, long-run stability, or universal A/V sync.

Before reconsidering Stable, execute the staged plan in `ENDURANCE_TEST_PLAN.md` on one immutable bundle and publish only scrubbed metrics with exact hashes.
