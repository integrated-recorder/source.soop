# Integrated Recorder SOOP Adapter

Standalone Integrated Recorder Adapter Protocol v1 executable for SOOP live HLS streams.

The adapter supports channel login IDs and `play.sooplive.com`, `play.sooplive.co.kr`, and historical `play.afreecatv.com` URLs. It uses SOOP's current live API and dynamic HLS assignment endpoint. It does not record streams or run a polling loop; the caller controls each watch check.

## Capabilities

- `watch`: checks one channel and returns `offline` or live HLS media with a broadcast-specific session reference.
- `resolve`: resolves a live channel into HLS media.
- `metadata`: reports the current broadcast title when its broadcast number still matches the recording.
- `refresh`: requests a new AID and manifest after HTTP 401 or 403.

Platform failures, login requirements, and malformed responses are errors; they are not reported as offline.

## Input and configuration

| Field | Location | Behavior |
| --- | --- | --- |
| `channel` | Input, required | SOOP login ID, or a `play.sooplive.com`, `play.sooplive.co.kr`, or `play.afreecatv.com` URL. A URL may include a broadcast number as its second path segment. |
| `stream_password` | Input, secret | Optional password for a protected broadcast. |
| `quality` | Configuration | `best` by default, `worst`, or an exact SOOP preset name/label. `auto` is not selectable. |
| `account_username` | Configuration, secret | Optional SOOP account username. Supply it with `account_password`. |
| `account_password` | Configuration, secret | Optional SOOP account password. Supply it with `account_username`. |

The stream password and any configured account credentials are returned only through Protocol v1's secret state mutations, namespaced by channel and broadcast number so refresh can recover them after the adapter process restarts. They are not placed in media metadata or error messages. Signed manifest URLs are marked sensitive.

## Platform flow

The adapter calls SOOP's `player_live_api.php` endpoint for live status, broadcast identity, title, CDN, and quality presets. If SOOP requires an account (`RESULT=-6`), it logs in through `LoginAction.php`, retains the returned cookies for the current process, and retries. It requests an AID using the broadcast number, selected quality, and optional stream password, then calls the returned RMD host's `broad_stream_assign.html` endpoint to obtain the HLS manifest URL. Dynamic platform URLs must use HTTPS and a SOOP/Afreeca domain.

The Core scheduler controls how often `watch` runs. The adapter performs one check per request and does not invoke FFmpeg, Streamlink, or a recorder.

## References

- [Adapter SDK v0.1.0 and Protocol v1](https://github.com/dltkddnr04/integrated-recorder-adapter-sdk-go/tree/v0.1.0)
- [Historical AfreecaTV Auto Recorder](https://github.com/dltkddnr04/AfreecaTV-Auto-Recorder/blob/main/main.py) and its [stream status fixture](https://github.com/dltkddnr04/AfreecaTV-Auto-Recorder/blob/main/test/stream_status_detection.py)
- Streamlink's [current SOOP plugin](https://github.com/streamlink/streamlink/blob/master/src/streamlink/plugins/soop.py) and [plugin tests](https://github.com/streamlink/streamlink/blob/master/tests/plugins/test_soop.py)

Build and verify:

```sh
GOWORK=off go test -race -count=1 ./...
GOWORK=off go vet ./...
GOWORK=off go build -o integrated-recorder-adapter-soop ./cmd/integrated-recorder-adapter-soop
```

The executable reads Protocol v1 newline-delimited JSON from stdin and writes protocol frames only to stdout. Diagnostics, if any, go to stderr.
