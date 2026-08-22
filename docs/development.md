# Development Guide

## Phase-by-phase workflow

Work on one phase at a time. Before proceeding, run relevant checks, document
the result, and confirm the phase has a working, testable state. Do not begin a
future phase automatically.

## Current setup

Phase 1 adds the local Python desktop agent in `desktop-agent/`. It uses a
`src/` package layout, `pyperclip`, and standard-library `unittest` tests.

Phase 2 adds `backend/`, a Django project with Django REST Framework and
SQLite. Its `ClipboardEntry` model and HTTP API are covered by Django's built-in
test runner. See `backend/README.md` for virtual-environment setup, migrations,
server startup, API examples, and test commands.

Phase 3 connects `desktop-agent/` to `POST /api/clipboard/` with `requests`.
The default settings are the local endpoint, device ID `desktop-001`, and a
five-second timeout; all are overridable through environment variables. Unit
tests mock HTTP calls, while the integration instructions start both local
components.

Phase 4 adds Django Channels WebSocket infrastructure to the backend. The
server is now run by Daphne (installed into the backend venv). The ASGI
application routes HTTP to Django and WebSocket connections to
`ClipboardConsumer`. A `test.message` round-trip validates the plumbing;
real clipboard synchronization belongs to Phase 5.

### Phase 4 backend setup

Install Channels and Daphne into the backend venv if not already present:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python -m pip install channels daphne
```

Start the server (Daphne takes over `runserver` automatically):

```powershell
python manage.py runserver
```

Run all automated tests (REST + WebSocket, 10 total):

```powershell
python manage.py test
```

Run the WebSocket smoke test (server must be running):

```powershell
python scripts/websocket_smoke_test.py
```

## Future local development direction

- Android Studio and Gradle instructions will be added when the Android project
  is initialized.

## Quality expectations

Use readable code, focused modules, useful logs, appropriate tests, and clear
error handling. Python follows PEP 8 and uses `logging`; Android remains in
Java unless an explicit request changes that decision. Keep `.env` files and
real credentials out of version control.

## Git guidance

Use small, logical commits. The Phase 0 setup is suitable for a commit such as:

```text
chore: initialize project structure
```
