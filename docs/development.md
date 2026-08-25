# Development Guide

## Phase-by-phase workflow

Work on one phase at a time. Before proceeding, run relevant checks, document
the result, and confirm the phase has a working, testable state.

## Current setup

### Phase 1 — Desktop clipboard detection

`desktop-agent/` polls the OS clipboard via `pyperclip` and logs each new
non-empty text value once.

### Phase 2 — Django backend

`backend/` is a Django project with Django REST Framework and SQLite. The
`ClipboardEntry` model and HTTP API are covered by Django's test runner.

### Phase 3 — Desktop agent to backend

`desktop-agent/` sends clipboard text to `POST /api/clipboard/` via `requests`.
The HTTP `ClipboardBackendClient` class is retained for regression tests.

### Phase 4 — WebSocket infrastructure

`backend/` now runs under Daphne and handles WebSocket connections via Django
Channels. `ClipboardConsumer` accepts `test.message` and returns `test.ack`.

### Phase 5 — Desktop real-time WebSocket sync

`clipboard.update` is now the primary clipboard sync message. The desktop agent
uses `ClipboardWebSocketClient` (websockets sync API) as its transport, with
bounded-backoff reconnection.

---

## Backend setup

```powershell
cd backend
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
python manage.py migrate
python manage.py runserver      # Daphne serves HTTP + WebSocket
```

Run all tests (15 total):

```powershell
python manage.py test
```

Smoke test (server must be running):

```powershell
python scripts/websocket_smoke_test.py
```

## Desktop-agent setup

```powershell
cd desktop-agent
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .      # installs pyperclip, requests, websockets
clipboard-agent
```

Run all tests (37 total):

```powershell
python -m unittest discover -s tests -v
```

## Manual integration test

1. Start Django (`python manage.py runserver` from `backend/`).
2. Start the agent (`clipboard-agent` from `desktop-agent/`).
3. Copy text on Windows.
4. Confirm sync log in the agent terminal.
5. Verify with: `Invoke-RestMethod -Uri http://127.0.0.1:8000/api/clipboard/latest/`

## Failure/recovery test

1. Start the agent, confirm a successful sync.
2. Stop Django. Copy text. Confirm the agent logs a failure without crashing.
3. Restart Django. Copy a new value. Confirm reconnection and sync.

## Future work

- Android Studio and Gradle instructions will be added when the Android project
  is initialized.

## Quality expectations

Readable code, focused modules, useful logs, appropriate tests, clear error
handling. Python follows PEP 8 and uses `logging`. Android stays in Java unless
explicitly changed. Keep `.env` files and real credentials out of version
control.

## Git guidance

Use small, logical commits. Example:

```text
feat: add clipboard.update WebSocket handler (Phase 5)
```
