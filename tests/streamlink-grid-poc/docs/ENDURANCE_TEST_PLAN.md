# Native Grid endurance and chaos test plan

This plan applies to one immutable candidate identified by commit SHA and Bundle SHA-256. Historical runs on other hashes are context only. Use an authorized self-broadcast or other expressly permitted source; never retain broadcast media longer than required for private verification.

## Gates and stages

1. **Offline compatibility smoke (15–30 s fixtures):** risk-based combinations covering POC 0/1/2, B/no-B, AAC 44.1/48 kHz, quality profiles, normal EOF and StreamIO drain. Validate actual SPS, AU identity, TS continuity/PSI/PCR, FFprobe and full decode. Keep parser-negative fixtures separate.
2. **Grid smoke (15–30 s per needed combination):** same exact build; one session at a time. Verify selected server profile against SPS, audio config, sequence continuity, source/output normalized AU hashes and EOF/drain.
3. **10 min:** one representative B-frame and one low-delay profile, with periodic sync markers and resource sampling.
4. **30 min:** B-frame and low-delay cases, no unsupported structural gaps; validate all packets and whole-file decode.
5. **2 h:** immutable final candidate; record source-relative sync events, RSS, FDs, threads, buffer peak, Parent recovery and full TS/A/V verification.
6. **6 h:** same immutable final candidate and representative high-load permitted source; all 2 h checks plus full six-hour decode, byte accounting and orderly stop.
7. **Controlled failures:** at least 2 h only after normal 2 h stability passes; inject client-side Parent close, short network pause/delay, exact Cache overlap success/failure, reader close/cancel and slow consumer. Do not impair SOOP servers.

## Required per-run record

Commit/bundle hashes; OS/Python/Streamlink/FFmpeg versions; POC type/profile/level/SPS/PPS; resolution/FPS; AAC rate/channels; source and output AU counts/hashes; Grid gaps/duplicates; recovery count; PCR/PTS/DTS/TS/PSI/CRC results; decode errors; source-relative sync offset/p95/drift and uncertainty; RSS trend/peak; FDs/threads; StreamIO accepted/read/discarded/unaccepted bytes; duration/stop reason.

## Pass and stop conditions

Pass requires zero unexplained Grid gaps, output AU loss/duplication, TS continuity or PSI CRC errors, DTS regression, impossible POC/PTS conflict, decoder errors, unexplained A/V marker loss, payload change, output accounting loss or sustained resource growth. Any explicit media-integrity error stops the run; do not run out the duration after a known corruption. A recoverable outage passes only after exact Cache overlap proof and no duplicate output. Recovery failure must terminate clearly.

Disk budget must be calculated from expected bitrate and duration with spare capacity. Put artifacts in private, size-capped temporary storage; scrub secrets from reports. For each stage record actual elapsed duration; incomplete external streams are not duration passes.

## Release gate

Stable requires successful exact-candidate 2 h and 6 h runs, whole-file structural checks and decode, source-relative sync, stable RSS/FD/thread behavior, EOF/drain and recovery evidence. Until all are measured for the exact candidate SHA, Stable is NO-GO regardless of historical Stable Candidate results.
