# Progress

- [x] Phase 0 — Project Setup
- [x] Phase 1 — Desktop Clipboard Detection
- [x] Phase 2 — Django Backend
- [x] Phase 3 — Desktop Agent to Backend
- [x] Phase 4 — WebSocket Infrastructure
- [x] Phase 5 — Desktop Real-Time WebSocket Sync
- [x] Phase 6 — Android Application
- [x] Phase 7 — Server-Side Broadcasting & Remote Desktop Clipboard Update
- [x] Phase 8 — Desktop Catch-Up, Persistent Device Identity & Android Testing

## Phase 0 outcome

Created the monorepo directory layout, project instructions, baseline
documentation, and repository ignore rules.

## Phase 1 outcome

Implemented and tested a local Python text clipboard detector in
`desktop-agent/`. Logs each distinct non-empty text value once; safely handles
empty content and clipboard read failures.

## Phase 2 outcome

Implemented and verified the Django REST backend in `backend/`. SQLite,
`ClipboardEntry` model, `POST /api/clipboard/`, `GET /api/clipboard/latest/`.

## Phase 3 outcome

Connected the desktop agent to the Django REST API via HTTP. Each distinct
non-empty clipboard value is sent as JSON. Network and backend failures are
logged without stopping the agent.

## Phase 4 outcome

Added Django Channels WebSocket infrastructure. Daphne serves HTTP and
WebSocket on the same port. `ClipboardConsumer` handles `test.message` /
`test.ack`. `InMemoryChannelLayer` is used; no Redis.

## Phase 5 outcome

Connected the desktop agent to the backend over WebSocket using the `websockets`
sync client. Key additions:

- `desktop-agent/src/clipboard_agent/ws_client.py` — `ClipboardWebSocketClient`
  with persistent connection, `clipboard.update` payload, bounded-backoff
  reconnection (2 s → 5 s → 15 s → 30 s, non-blocking), and graceful error
  handling.
- `desktop-agent/src/clipboard_agent/config.py` — added `ws_url` / `CLIPBOARD_WS_URL`.
- `desktop-agent/src/clipboard_agent/cli.py` — monitoring loop now uses
  `ClipboardWebSocketClient` as its transport; `ClipboardBackendClient` retained
  for regression tests but not wired into the live sync path.
- `backend/clipboard/consumers.py` — added `clipboard.update` handler:
  validates `device_id` and `content`, stores `ClipboardEntry` via
  `database_sync_to_async`, returns `clipboard.ack`.
- `backend/clipboard/tests_websocket.py` — 5 new `clipboard.update` tests.
- `desktop-agent/tests/test_ws_client.py` — 20 new WS client tests.
- `desktop-agent/tests/test_config.py` — extended with `ws_url` tests.

Verification results:
- Backend: 15/15 tests passing (5 REST + 5 WS infra + 5 clipboard.update).
- Desktop agent: 37/37 tests passing (17 existing + 20 new WS client tests).
- No Redis, no authentication, no broadcasting, no Android changes, no Git
  commits without explicit permission.

Limitations: clipboard values missed during WebSocket outages are not queued;
`InMemoryChannelLayer` does not persist across server restarts; no event_id or
source_device loop prevention yet.

## Phase 6 outcome

Implemented manual Android clipboard synchronization to comply with Android 10+ background clipboard restrictions:
- User-triggered manual `[ SEND CLIPBOARD ]` button reads system clipboard in user-focused `MainActivity` and sends over WebSocket.
- User-triggered manual `[ RECEIVE CLIPBOARD ]` button fetches latest backend clipboard entry via `GET /api/clipboard/latest/` and applies it to the Android clipboard.
- Foreground service `ClipboardMonitorService` manages WebSocket lifecycle without background clipboard harvesting.
- Verified on physical Realme Android 14 (API 34) device.

## Phase 7 outcome

Implemented Django WebSocket update broadcasting and Python Desktop Agent remote update application with feedback loop prevention:
- `backend/clipboard/consumers.py`: Connected clients join `clipboard_sync_group`. Valid `clipboard.update` messages trigger a `group_send` that broadcasts `clipboard.remote_update` (`device_id`, `content`) to all connected clients except the sender.
- `desktop-agent/src/clipboard_agent/ws_client.py`: Added background listener thread with thread-safe `queue.Queue` ACK dispatching and `on_remote_update` callback handling.
- `desktop-agent/src/clipboard_agent/monitor.py`: Added `set_last_content(content)` to update internal state when remote content is written via `pyperclip.copy()`.
- `desktop-agent/src/clipboard_agent/cli.py`: Wired `on_remote_update` callback to execute `pyperclip.copy(content)` and `monitor.set_last_content(content)`.
- Loop Prevention: Setting `monitor.set_last_content(content)` ensures subsequent polling (`content == self._last_content`) suppresses outbound sync automatically.

Verification results:
- Backend: 17/17 tests passing (including 2 new broadcasting tests).
- Desktop Agent: 39/39 unit tests passing (including loop suppression and remote update callback tests).
- Android: 22/22 Gradle tasks UP-TO-DATE, unit tests passing, APK assembleDebug successful. 0 Android files modified.

## Phase 8 outcome

Implemented Desktop Catch-Up, Persistent Device Identity, and Android Unit Tests:
- **Desktop Catch-Up on Connection/Reconnect**: When Desktop Agent connects or reconnects over WebSocket, it fetches the latest entry from `GET /api/clipboard/latest/` via HTTP. If a valid entry exists, it applies it to the Windows clipboard via `pyperclip.copy(content)` and updates `monitor.set_last_content(content)`. This recovers missed clips sent while Desktop was offline without triggering outbound re-synchronization.
- **Desktop Configuration**: Added `rest_latest_url` field to `AgentConfig` (default `http://127.0.0.1:8000/api/clipboard/latest/`, override `CLIPBOARD_REST_LATEST_URL`).
- **Persistent Desktop Device ID**: Auto-generates a persistent UUID (`desktop-<uuid>`) saved to `~/.clipboard_sync/device_id.txt` on first launch. Reused on subsequent runs. `CLIPBOARD_DEVICE_ID` environment variable continues to override.
- **Persistent Android Device ID**: Auto-generates a persistent UUID (`android-<uuid>`) saved in Android `SharedPreferences` via `Config.getDeviceId(Context)`.
- **Android Unit Testing**: Added `ClipboardApiClientTest.java` covering successful 200 response, JSON extraction, 404 response, network failure, and malformed JSON format.

Verification results:
- Backend: 17/17 tests passing.
- Desktop Agent: 43/43 unit tests passing.
- Android: 9 unit tests passing (`ClipboardApiClientTest` + `ConfigTest`), APK build successful.
