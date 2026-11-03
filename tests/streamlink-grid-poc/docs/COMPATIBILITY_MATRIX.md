# Current Native Grid compatibility matrix

Evidence is scoped to code/tests and explicitly named artifact hashes. `VERIFIED` means evidence exists at that scope, not universal service compatibility.

| Feature | Offline | Grid E2E | 30 min | 2 h | 6 h | Current exact-candidate status |
|---|---|---|---|---|---|---|
| POC 0 progressive subset | VERIFIED | Current exact bundle: 120 s, 600 s, and 1,800 s self-broadcast; 1080p, B pictures, contiguous source/Grid VCL identity | 1,800 s exact-bundle capture PASS; full TS/decode pass | NOT_TESTED | NOT_TESTED | VERIFIED_FOR_SUBSET; MMCO5 and other POC types remain separate |
| POC 1 progressive subset | VERIFIED including offline B pictures | Historical short self-broadcast no-reorder, older bundle | NOT established for current candidate | NOT_TESTED | NOT_TESTED | Live B-picture UNVERIFIED |
| POC 2 zero-reorder subset | VERIFIED | Historical short low-delay/no-B, older bundle | NOT_TESTED current candidate | NOT_TESTED current candidate | NOT_TESTED | VERIFIED_FOR_SUBSET; MMCO5 unsupported |
| MMCO 5 | Helper/parser checks; production rejects | NOT_TESTED | NOT_TESTED | NOT_TESTED | NOT_TESTED | UNSUPPORTED (`h264_grid_mmco5_unverified`) |
| AAC-LC/ADTS | VERIFIED by parser/MediaSink/TS tests | Current exact bundle: source/Grid contiguous AU identity at 120 s, 600 s, and 1,800 s | PASS; 84,456 AUs in the 1,800 s capture; full AAC decode | NOT_TESTED | NOT_TESTED | VERIFIED_FOR_SUBSET; synthetic 48 kHz stereo AAC-LC |
| A/V source-relative sync | Synthetic marker and control-delay calibration | Current exact bundle: 120 s, 600 s, and 1,800 s controlled self-broadcast | Common-overlap PASS: 1,929 events / 1,799.167 s; added median 0.333 ms, max/p95 0.667 ms, drift −0.002615 ppm. Strict edge gate false due receiver-start/finite-tail censorship and 11 audio detector extras (16 in source baseline). | NOT_TESTED | NOT_TESTED | Synthetic overlap subset only; not perceptual or arbitrary live content; edge coverage limited |
| PCR/TS | Synthetic PCR insertion/wrap/continuity/full decode | Current exact bundle: full 600 s and 1,800 s outputs | 30 min PASS; 3,144,607 packets, 3,602 valid PSI sections; continuity/CRC/PCR regression 0; full FFmpeg decode | NOT_TESTED | NOT_TESTED | File integrity verified; not real-time network pacing |
| Parent/Cache recovery | Deterministic fault suite | Historical controlled client-owned socket close | Historical | NOT_TESTED current hash | NOT_TESTED | VERIFIED_FOR_TESTED_OVERLAP; natural repeated failures UNVERIFIED |
| StreamIO/EOF | Full module/bundle tests | Current exact bundle, 1,800 s; drain complete, emitted/read/accepted bytes equal, discarded/unaccepted 0 | PASS | NOT_TESTED | NOT_TESTED | VERIFIED_FOR_30_MIN_CLEAN_RUN; parent recovery not exercised |
| Memory/FD/thread trend | Bounded structures and short tests | Current exact bundle, 1,800 s; 5 s samples | PASS for 30 min: RSS peak 59,364 KiB, FD 13, threads 3 | NOT_TESTED | NOT_TESTED | VERIFIED_FOR_30_MIN_CLEAN_RUN only |
| Quality/HLS/fallback | Full deterministic selection/fallback tests | Historical profile receives | NOT_TESTED current hash | NOT_TESTED | NOT_TESTED | Offline VERIFIED; current live resolution NOT_TESTED |
| Security/auth boundaries | Offline auth/parser tests | Historical authorized sessions | Historical | Historical | NOT_TESTED | Offline VERIFIED; no new auth-expiry live test |

Exact current candidate identity and staged result: `ENDURANCE_RESULT.md`. A looped-source smoke is excluded from PASS because its loop boundary introduced a reference audio timestamp overlap and A/V offset jump; the 30-minute source is non-looping. User availability now blocks further live sessions; 2 h, 6 h, and controlled-failure stages are NOT_TESTED.

Supplemental offline regression for the same production bundle: Source 767 passed / 0 skipped; bundled production-code suite 758 passed / 0 skipped. The two former POC-2 fixture skips were closed using independently decoded libx264 output; this does not change the live/endurance rows above.
