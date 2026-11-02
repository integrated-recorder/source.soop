# Native Grid quality selection: measured profiles and limits

**Observation date:** 2026-11-02
**Scope:** public, password-free live listings and short, memory-only Native Grid receives. No broadcaster identifiers, broadcast numbers, tickets, cookies, signed URLs, or media payloads were retained.

## Public listing survey

A fresh scan covered 32 pages of SOOP's public live listing. Filtering to non-adult, password-free, non-subscription-only entries left 1,681 unique live targets with valid advertised dimensions. The current listing's most common original dimensions were:

| Advertised original | Eligible targets |
| --- | ---: |
| 1920×1080 | 1,296 |
| 1280×720 | 272 |
| 800×600 | 21 |
| 1024×576 | 17 |
| 2560×1440 | 16 |
| 576×1024 | 14 |
| Other dimensions | 45 |

No 3840×2160 target appeared in this scan. A prior scan of later pages also returned no additional entries. This is evidence about the public listing snapshot and observation window, not proof that no SOOP broadcaster can ever publish a 2160p stream. A published 4K setup was used as a separate lead, but its live listing and Grid SPS were 2560×1440; it did not provide a 2160p sample.

## Measured Native Grid profiles

The Center `0x69` allocation request's integer `quality` is an effective profile selector in the tested sessions. The selected Parent's returned quality and the first H.264 SPS were both checked. The quality values are empirical wire values, not a claim that all integer values are valid.

| Streamlink profile | Center allocation quality | Center JOIN fields | Required H.264 SPS height | Official live preset required |
| --- | ---: | --- | ---: | --- |
| `original` | 1 | `quality=ori`, `is_auto=false` | Exact advertised original height when available | `name=original` |
| `720p` | 2 | `quality=ori`, `is_auto=false` | 720 | `label=720p`, `name=hd4k` |
| `540p` | 4 | `quality=ori`, `is_auto=false` | 540 | `label=540p`, `name=hd` |
| `360p` | 8 | `quality=low`, `is_auto=true` | 360 | `label=360p`, `name=sd` |

The new `360p` result is the reason the set of known values is not limited to 1, 2, and 4. In a fresh strict validation, nine separate public broadcasts were tested: three with 2560×1440 originals, three with 1920×1080 originals, and three with 1280×720 originals. All nine advertised the official `360p:sd` preset; all nine returned Parent quality 8 for the q=8 request; all nine supplied video and audio; all nine's measured SPS height was 360 and passed the receiver's height guard; and all nine completed the two-second sample without a Grid sequence discontinuity. Media remained in memory and was discarded.

The q=8 test used the complete observed selector pair (`quality=low`, `is_auto=true`) along with Center allocation quality 8. Holding the JOIN fields at `ori/false` is not equivalent. Exact Parent assignment and SPS checks remain required; the implementation does not accept a server response that silently substitutes another profile.

## Controlled RTMP test source

A bounded synthetic test used a protected RTMP test configuration, after confirming that its channel was offline. A 1920×1080@30 synthetic H.264/AAC input was accepted for a short run; the real Streamlink bundle received `original`/`1080p` at 1920×1080 with Center quality 1, `540p` at 960×540 with quality 4, and `360p` at 640×360 with quality 8. The received audio was AAC, 48 kHz stereo. Every completed sample had zero Grid sequence discontinuities and valid 188-byte TS alignment. Temporary TS outputs and diagnostics were removed after extracting these non-content measurements. The broadcast's available list did not offer `720p`, so quality 2 was not tested on this particular source.

The same test configuration did **not** accept synthetic 2560×1440 inputs at 4 or 8 Mbps, or 3840×2160 inputs at 6 or 12 Mbps. FFmpeg reached the RTMP publish stage and then received a broken pipe (exit 224); the 1920×1080 control succeeded. This isolates the failure to the current test ingest/session path, but the server-side policy response was not available, so it does not prove that SOOP universally rejects 1440p/2160p. No 2160p Grid stream was obtained, and no 2160p downscale profile can be claimed from this test.

Earlier bounded samples independently established the following mappings:

| Advertised original | Request | Parent response | H.264 SPS | Evidence |
| --- | ---: | ---: | ---: | --- |
| 1920×1080 | 1 | 1 | 1920×1080 | 8-broadcast sample; q=1 matched all 8 |
| 1920×1080 | 2 | 2 | 1280×720 | 6 clean of 8; 1 later Cache gap, 1 no SPS within the short window |
| 1920×1080 | 4 | 4 | 960×540 | 8-broadcast sample; q=4 matched all 8 |
| 2560×1440 | 1 | 1 | 2560×1440 | All 16 listed 1440p candidates' originals matched; short memory samples |
| 2560×1440 | 2 | 2 | 1280×720 | 8-broadcast sample; q=2 matched all 8 |
| 2560×1440 | 4 | 4 | 960×540 | 7 matched; 1 first-party HTTP failure was inconclusive |
| 1280×720 | 1 | 1 | 1280×720 | 8-broadcast sample; q=1 matched all 8 |
| 1280×720 | 4 | 4 | 960×540 | 8-broadcast sample; q=4 matched all 8 |

The table records short reception checks, not full-length decode or long-run stability for every profile. A few q=2 observations ended in a Cache gap or did not deliver SPS within the bounded window; these are reported as failures/inconclusive rather than resolution matches.

## Other selector candidates

The separate Center values 3, 10, and 11 were tried based on static analysis of a client binary. Returned Parent qualities did not match the requested value in those sessions (q=3→1, q=10→2, q=11→1), so they were rejected before output. Selector variants 5, 6, 7, and 9 were also not shown to produce a distinct profile in paired JOIN/Center tests. The values `high_4000` and `high_8000` are not resolution labels. These unverified values are not exposed.

The candidate `SOOPStreamer.exe` artifact used in prior static analysis has SHA-256 `98a1741b2368be33e25958a46443760663ff8da225c742aabac16d625297709b`, but its update-list size/hash did not match the retrieved bytes and full Authenticode verification failed. It was analyzed statically and never executed. Its selector names guide hypotheses only; measured server responses and H.264 SPS determine the supported profiles above.

## Enumeration and fail-closed behavior

The plugin intersects the broadcast's official `VIEWPRESET` entries with the measured mappings. `best` and `worst` select only among profiles returned for that broadcast. If the selected profile's Parent quality does not match, discovery fails. Before producing TS, the first applicable H.264 SPS must match the selected height. If the official metadata is missing or ambiguous, only `original` is exposed. Auto fallback uses the exact corresponding HLS key when one was identified; it does not substitute another quality.

Examples:

```sh
streamlink 'https://play.sooplive.com/CHANNEL_ID/BNO' 360p -o recording.ts
streamlink 'https://play.sooplive.com/CHANNEL_ID/BNO' 720p -o recording.ts
streamlink 'https://play.sooplive.com/CHANNEL_ID/BNO' original -o recording.ts
```

## Unverified targets and boundaries

* No active 2160p original was found in the public listing scan. A 2160p→1080p Native Grid profile is **not verified** and is not advertised.
* Official HLS presets are availability hints. Their labels do not, by themselves, prove a Grid profile; each listed Grid mapping also has measured Parent and SPS evidence.
* Samples were brief and memory-only. They do not establish 30-minute stability, every channel's profile availability, or universal service behavior.
* The measured 360p profile is a downscaled Grid stream; it does not establish 1080p output from a 2160p source.
* HLS remains a separate transport and quality list. Grid and HLS timelines are not mixed.
