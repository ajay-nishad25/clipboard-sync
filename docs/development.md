# Development Guide

## Phase-by-Phase Workflow

Work on one phase at a time. Before proceeding, run relevant checks, document the result, and confirm the phase has a working, testable state.

---

## Current Verified Baseline (Phases 1–9B)

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
Server broadcasts `clipboard.remote_update` to connected devices. Desktop Agent applies updates via `pyperclip.copy()` and suppresses outbound sync loops via `monitor.set_last_content()`.

### Phase 8 — Desktop Catch-Up & Persistent Identity
Desktop Agent recovers `GET /api/clipboard/latest/` on startup/reconnect. Persistent UUID device IDs for Desktop (`~/.clipboard_sync/device_id.txt`) and Android (`SharedPreferences`).

### Phase 9A — Multi-User Data Model & User Isolation
`Device` and `ClipboardState` models. Single active record per user with 10-minute expiration. User-scoped WebSocket channel groups (`clipboard_user_<user_id>`).

### Phase 9B — Desktop ↔ Android Device Pairing
Temporary pairing code generation (`AB7K-29XM`, 5-min expiration) on Desktop startup (`POST /api/device/pairing/create/`). Android pairing section in `MainActivity` with `POST /api/device/pair/` endpoint associating Android Device with Desktop's owner User.

---

## Component Setup & Testing Commands (Baseline)

### 1. Backend Setup & Tests (43 tests total)
```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py check
python manage.py makemigrations --check
python manage.py test
```

### 2. Desktop Agent Setup & Tests (45 tests total)
```powershell
cd desktop-agent
.\.venv\Scripts\Activate.ps1
python -m unittest discover -s tests -v
```

### 3. Android App Setup & Tests (12 tests total)
```powershell
cd android-app
.\gradlew.bat test
.\gradlew.bat assembleDebug
```

---

## Phase 9 Sub-Phases Roadmap

- [x] **Phase 9A — Multi-User Data Model & User Isolation**
- [x] **Phase 9B — Desktop ↔ Android Pairing**
- [ ] **Phase 9C — Authenticated WebSocket & REST Communication (PLANNED / NEXT)**
  - Require device authentication tokens for WebSocket connections and REST requests.
  - Enforce server-side ownership validation for all clipboard operations.
- [ ] **Phase 9D — Production Configuration & HTTPS/WSS (PLANNED / NEXT)**
  - Support configurable production transport endpoints (`https://` and `wss://`).
  - Enforce TLS in production while retaining local HTTP/WS development options.
- [ ] **Phase 9E — Production Deployment & Hardening (PLANNED / NEXT)**
  - Configure PostgreSQL, Redis Channels layer, Daphne ASGI deployment, secrets management, and admin auditing.

---

## Quality & Security Expectations

- **Plain Text Only**: No binary, image, screenshot, or rich-text data.
- **Android Restrictions**: Do NOT attempt background clipboard harvesting on Android 10+. Maintain manual `[ SEND CLIPBOARD ]` and `[ RECEIVE CLIPBOARD ]` UI triggers.
- **Privacy & Logging**: Clipboard content must never be printed to application logs.
- **Secret Safety**: Never commit credentials, tokens, or `.env` files to git.
