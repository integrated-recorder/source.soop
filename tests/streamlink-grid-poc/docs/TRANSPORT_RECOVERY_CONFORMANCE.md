# Grid transport, recovery, lifecycle and security conformance

Code reviewed: `soop_grid/protocol.py`, `gateway.py`, `center.py`, `parent.py`, `recovery.py`, `startup.py`, `stream.py`, `diagnostics.py`.

## Transport and authorization

Gateway/Center/Parent frame readers validate family-specific headers, lengths, checksums and configured bounds before consuming bodies. Metadata/ticket and Gateway certificate acquisition use the first-party authorization flow. Explicit denial, malformed server response, changed media quality or invalid identity is terminal; no ticket, node key or credential is synthesized. The Grid control sockets are plaintext TCP by the documented protocol. Automatic login/session reauthentication and BNO switching are unsupported.

## Parent and Cache

Only one Parent connection supplies media at a time. Transport EOF/reset/timeouts and bounded media stall can trigger finite retry; malformed/auth/media-validation failures cannot. Current policy limits one Center rediscovery and eight Parent attempts per outage under a single recording deadline. Recovery is accepted only after exact overlap identity and continuity checks; mux/clock state is retained across verified overlap. Missing or conflicting overlap terminates; media is not fabricated. No cross-quality Parent failover or multi-parent aggregation is allowed.

Historical controlled client-owned socket-close and overlap E2E evidence exists, but repeated natural remote failures and independent failure domains are not established. See `LIVE_FAILOVER_VALIDATION.md` and keep its artifact scope.

## Startup, StreamIO and close

Startup retry is disabled by default, opt-in and bounded; only the specified initial Cache sequence gap before any output can retry. It cannot restart after publication. StreamIO uses a bounded buffer and cancellation-aware worker. `close()` closes sockets, wakes blocked producers, joins with a bound, and records accepted/read/discarded/unaccepted byte accounting. EOF/drain success is distinct from planned output size; shutdown timeout or lost bytes must remain failures.

HLS fallback is an independent Streamlink SOOP stream and is restricted to allowlisted initial transport failures before Grid output. It does not concatenate different timelines and is denied after media validation failure or publication.

## Diagnostics and resources

Routine diagnostics use allowlisted event/error fields and bounded numeric facts. Tokens, cookies, URLs, broadcast identifiers and payloads must not be added. Optional raw diagnostic capture is private, opt-in and capped. StreamIO queue, wire message sizes, retry counts, Cache identity window and startup staging are bounded. A bounded daemon-thread join cannot forcibly interrupt a blocked OS/file operation; timeout is surfaced as `reader_shutdown_timeout`.

## Current campaign status

No current-hash live Parent failure, session expiration, authentication denial, self-broadcast, or shutdown-under-network-fault test was executed. Local deterministic transport/fault tests are part of the module and bundled suites; exact current bundle counts are recorded in `ENDURANCE_RESULT.md`.

On source commit `69b2cce2a6f45dbee2b94bfdd95ee7ddf925b2c7`, the focused offline
recovery/StreamIO/startup-retry/Parent-fault suite passed **114 tests** in
5.71 s. It exercises synthetic peers and loopback-only sockets. This narrows
the unverified scope to real SOOP network behavior, long-duration resource
trends, and live failure timing; it does not replace those tests.
