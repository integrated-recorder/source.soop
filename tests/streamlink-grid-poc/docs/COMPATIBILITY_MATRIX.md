# Current Native Grid compatibility matrix

Evidence is scoped to code/tests and explicitly named artifact hashes. `VERIFIED` means evidence exists at that scope, not universal service compatibility.

| Feature | Offline | Grid E2E | 30 min | 2 h | 6 h | Current exact-candidate status |
|---|---|---|---|---|---|---|
| POC 0 progressive subset | VERIFIED | Historical short self-broadcast, B pictures, older bundle `e1a1433b…` | Historical other artifact(s) only | Historical other artifact(s) only | NOT_TESTED | VERIFIED_FOR_SUBSET; current hash live NOT_TESTED |
| POC 1 progressive subset | VERIFIED including offline B pictures | Historical short self-broadcast no-reorder, older bundle | NOT established for current candidate | NOT_TESTED | NOT_TESTED | Live B-picture UNVERIFIED |
| POC 2 zero-reorder subset | VERIFIED | Historical short low-delay/no-B, older bundle | NOT_TESTED current candidate | NOT_TESTED current candidate | NOT_TESTED | VERIFIED_FOR_SUBSET; MMCO5 unsupported |
| MMCO 5 | Helper/parser checks; production rejects | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | UNSUPPORTED (`h264_grid_mmco5_unverified`) |
| AAC-LC/ADTS | VERIFIED by parser/MediaSink/TS tests | Historical short self-broadcast AU identity, older bundle | Historical only | Historical only | NOT_TESTED | VERIFIED_FOR_SUBSET; exact current hash live NOT_TESTED |
| A/V perceptual/source-relative sync | Synthetic marker and historical 2 h evidence on other hashes | Historical short markers on other hash | Historical | Historical 2 h on other hash | NOT_TESTED | Current exact candidate NOT_TESTED |
| PCR/TS | Synthetic PCR insertion/wrap/continuity/full decode | Historical short output only | Historical artifacts | Historical artifacts | NOT_TESTED | Offline VERIFIED; not real-time pacing |
| Parent/Cache recovery | Deterministic fault suite | Historical controlled client-owned socket close | Historical | NOT_TESTED current hash | NOT_TESTED | VERIFIED_FOR_TESTED_OVERLAP; natural repeated failures UNVERIFIED |
| StreamIO/EOF | Full module/bundle tests | Historical short drain | Historical artifact only | Historical other artifact only | NOT_TESTED | Current unit/bundle VERIFIED; live current hash NOT_TESTED |
| Memory/FD/thread trend | Bounded structures and short tests | Historical measurements on other hashes | Historical | Historical measurements on other hashes | NOT_TESTED | Current long-run trend NOT_TESTED |
| Quality/HLS/fallback | Full deterministic selection/fallback tests | Historical profile receives | NOT_TESTED current hash | NOT_TESTED | NOT_TESTED | Offline VERIFIED; current live resolution NOT_TESTED |
| Security/auth boundaries | Offline auth/parser tests | Historical authorized sessions | Historical | Historical | NOT_TESTED | Offline VERIFIED; no new auth-expiry live test |

Exact current candidate identity and test result: `ENDURANCE_RESULT.md`.
