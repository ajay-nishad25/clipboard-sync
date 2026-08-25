# Development Guide

## Phase-by-Phase Workflow

Work on one phase at a time. Before proceeding, run relevant checks, document the result, and confirm the phase has a working, testable state.

---

## Current Verified Baseline (Phases 1–8)

### Phase 1 — Desktop Clipboard Detection
`desktop-agent/` polls OS clipboard via `pyperclip` and logs each distinct text value.

### Phase 2 — Django Backend
`backend/` Django REST Framework & SQLite backend (`ClipboardEntry` model, HTTP API).

### Phase 3 — Desktop Agent to Backend HTTP
`desktop-agent/` sends text to `POST /api/clipboard/` via `requests`.

### Phase 4 — WebSocket Infrastructure
Daphne serves HTTP and WebSocket via Django Channels (`test.message` / `test.ack`).

### Phase 5 — Desktop Real-Time WebSocket Sync
`clipboard.update` / `clipboard.ack` over `ClipboardWebSocketClient` with bounded-backoff reconnection.

### Phase 6 — Android Application
Manual Android clipboard sync (`[ SEND CLIPBOARD ]` over WS, `[ RECEIVE CLIPBOARD ]` over HTTP GET) adhering to Android 10+ background clipboard access rules.

### Phase 7 — Bidirectional Update Broadcasting
Server broadcasts `clipboard.remote_update` to connected devices in `clipboard_sync_group`. Desktop Agent applies updates via `pyperclip.copy()` and suppresses outbound sync loops via `monitor.set_last_content()`.

### Phase 8 — Desktop Catch-Up & Persistent Identity
Desktop Agent recovers `GET /api/clipboard/latest/` on startup/reconnect. Persistent UUID device IDs for Desktop (`~/.clipboard_sync/device_id.txt`) and Android (`SharedPreferences`).

---

## Component Setup Commands (Baseline)

### 1. Backend Setup
```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python manage.py migrate
python manage.py runserver      # Daphne serves HTTP + WebSocket on 127.0.0.1:8000
```
Run backend tests (17 total):
```powershell
python manage.py test
```

### 2. Desktop Agent Setup
```powershell
cd desktop-agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
clipboard-agent
```
Run desktop tests (43 total):
```powershell
python -m unittest discover -s tests -v
```

### 3. Android App Setup
```powershell
cd android-app
.\gradlew.bat test
.\gradlew.bat assembleDebug
```

---

## Phase 9 Sub-Phases Roadmap (PLANNED / NEXT)

- [ ] **Phase 9A — Multi-User Data Model & User Isolation**
  - Implement `User.CurrentClipboard` model with single-record replacement and 10-minute expiration.
  - Implement user-scoped channel groups (`clipboard_user_<USER_ID>`).
- [ ] **Phase 9B — Desktop ↔ Android Pairing**
  - Implement Desktop pairing code generation (`AB7K-29XM`).
  - Implement Android pairing screen and backend token exchange endpoint (`POST /api/device/pair/`).
- [ ] **Phase 9C — Authenticated WebSocket & REST Communication**
  - Require device authentication tokens for WebSocket connections and REST requests.
  - Enforce server-side ownership validation for all clipboard operations.
- [ ] **Phase 9D — Production Configuration & HTTPS/WSS**
  - Support configurable production transport endpoints (`https://` and `wss://`).
  - Enforce TLS in production while retaining local HTTP/WS development options.
- [ ] **Phase 9E — Production Deployment & Hardening**
  - Configure PostgreSQL, Redis Channels layer, Daphne ASGI deployment, secrets management, and admin auditing.

---

## Mandatory Multi-User Isolation Tests (Phase 9 Planned)

Future Phase 9 implementation must create test suites verifying:

1. **User Isolation Sync**: `User A Android` → `User A Desktop` (**PASS**).
2. **Cross-User Isolation**: `User A Android` → `User B Desktop` (**MUST NOT RECEIVE**).
3. **Cross-User Isolation**: `User B Android` → `User A Desktop` (**MUST NOT RECEIVE**).
4. **REST Data Isolation**: `User A REST request` → `User B clipboard` (**MUST NOT ACCESS**).
5. **Unpaired Device Rejection**: Unpaired device request → `clipboard API` (**MUST NOT ACCESS**).
6. **Authentication Rejection**: Invalid device token → WebSocket connection (**REJECTED**).
7. **Expiration Retention**: Clipboard entry older than 10 minutes (**DELETED / UNAVAILABLE**).

---

## Quality & Security Expectations

- **Plain Text Only**: No binary, image, screenshot, or rich-text data.
- **Android Restrictions**: Do NOT attempt background clipboard harvesting on Android 10+. Maintain manual `[ SEND CLIPBOARD ]` and `[ RECEIVE CLIPBOARD ]` UI triggers.
- **Privacy & Logging**: Clipboard content must never be printed to application logs.
- **Secret Safety**: Never commit credentials, tokens, or `.env` files to git.
