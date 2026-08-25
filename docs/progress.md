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
- [x] Phase 9A — Multi-User Data Model & User Isolation
- [x] Phase 9B — Desktop ↔ Android Device Pairing
- [x] Phase 9C — Authenticated Device Credentials & Communication
- [ ] Phase 9D — Production Configuration & HTTPS/WSS (PLANNED / NEXT)
- [ ] Phase 9E — Production Deployment & Hardening (PLANNED / NEXT)

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

## Phase 9A outcome

Implemented Multi-User Data Model & User Isolation on the Django backend:
- **Device Model**: Created `Device` model (`user`, `device_id`, `device_type`) linking hardware devices to Django `User` instances.
- **ClipboardState Model**: Created `ClipboardState` model (`user`, `content`, `updated_at`, `expires_at`). Replaces historical entries with a single active record per user.
- **10-Minute Retention Expiration**: Enforces 10-minute expiration (`expires_at = now + 10m`). Expired entries are automatically purged and hidden on access (`is_expired()`).
- **User-Scoped WebSocket Isolation**: Replaced global `clipboard_sync_group` with user-scoped channel groups (`clipboard_user_<user_id>`). Real-time `clipboard.remote_update` broadcasts are restricted to devices belonging to the same user.
- **User-Scoped REST API**: Updated `GET /api/clipboard/latest/` to resolve device identity to its owner user and return only that user's active `ClipboardState`.
- **Django Admin**: Registered `Device` and `ClipboardState` models in Django admin for administrator inspection.

Verification results:
- Backend tests: **27/27 PASS** (`Ran 27 tests in 0.305s OK`).

## Phase 9B outcome

Implemented Desktop ↔ Android Device Pairing:
- **PairingCode Model**: Created `PairingCode` model (`desktop_device`, `code`, `created_at`, `expires_at`, `is_used`, `used_at`).
- **Pairing Code Generation**: Formatted 8-character single-use code (e.g. `AB7K-29XM`, 5-min expiration) generated via `POST /api/device/pairing/create/`.
- **Android Pairing UI**: Added Pair Desktop section in `MainActivity` (`pairingCodeInput`, `pairButton`, `pairingStatusText`).
- **Device Ownership Association**: `POST /api/device/pair/` validates pairing code and links Android device to Desktop's owner User. Re-pairing to a different user is rejected with 409 Conflict.
- **Verification**: 43 backend tests, 45 desktop tests, 12 android unit tests passing cleanly.

## Phase 9C outcome

Implemented Authenticated Device Credentials & Communication:
- **DeviceCredential Model**: Created `DeviceCredential` model (`device`, `token_hash`, `created_at`, `last_used_at`, `revoked_at`). Stores SHA-256 hex digest of raw token secret. Raw credentials are never stored in the database or logged.
- **Credential Issuance**: Issued during Android pairing (`POST /api/device/pair/`) and Desktop registration (`POST /api/device/credential/register/`). Returned raw token is persisted locally on clients (`~/.clipboard_sync/token.txt` and Android `SharedPreferences`).
- **REST Token Authentication**: REST endpoints (`GET /api/clipboard/latest/`) validate `Authorization: Bearer <token>` header or query parameters. Requests with invalid or revoked tokens return 401 Unauthorized.
- **WebSocket Token Authentication**: WebSocket consumer validates `?token=<token>` parameter on `connect()`. Unauthenticated or revoked connections are rejected immediately with close code `4001`.
- **Token Revocation & Unpair**: `POST /api/device/unpair/` marks token revoked (`revoked_at`), immediately denying subsequent REST and WebSocket requests. Registered `DeviceCredential` in Django admin with revocation actions.

Verification results:
- Backend tests: **30/30 PASS** (`Ran 30 tests in 0.359s OK`).
- Desktop tests: **46/46 PASS** (`Ran 46 tests in 0.616s OK`).
- Android unit tests: **12/12 PASS** (`BUILD SUCCESSFUL`).
- Android Debug APK: **BUILD SUCCESSFUL**.
