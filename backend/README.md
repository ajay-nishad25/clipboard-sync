# Clipboard Sync Backend

Phase 4 adds Django Channels and WebSocket infrastructure to the existing
Django REST backend. The REST API from Phase 2/3 remains unchanged. Phase 4
validates the WebSocket plumbing with a test-only message round-trip; real
clipboard synchronization belongs to Phase 5.

## Prerequisites

- Python 3.11 or later

## Environment setup

From `backend/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Set a local Django development secret. Do not commit its value:

```powershell
$env:DJANGO_SECRET_KEY = "choose-a-long-unique-local-development-value"
```

`DJANGO_DEBUG` defaults to `True` for this POC. See `.env.example` for the
expected variable names; Django does not load `.env` files automatically.

## Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
python -m pip install channels daphne
```

`channels` and `daphne` are runtime requirements for Phase 4 and later. They
are not yet listed in `pyproject.toml` because the POC installs them
explicitly; they will be declared in a future tidy-up.

## Database migrations

```powershell
python manage.py migrate
```

SQLite stores local data in `db.sqlite3`, which is ignored by Git.

## Start the development server

```powershell
python manage.py runserver
```

Because `daphne` is listed first in `INSTALLED_APPS`, Django's `runserver`
command is replaced by Daphne, which supports both HTTP and WebSocket
connections. The server listens on `http://127.0.0.1:8000/` by default.

## REST API endpoints

### Create an entry

`POST /api/clipboard/`

Required JSON fields:

```json
{
  "device_id": "desktop-001",
  "content": "Hello World"
}
```

Example PowerShell request:

```powershell
Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/api/clipboard/ `
  -ContentType "application/json" `
  -Body '{"device_id":"desktop-001","content":"Hello World"}'
```

It returns `201 Created` with the entry, including its database-generated `id`
and `created_at` timestamp. `content` must be a non-empty JSON string.

### Get the latest entry

`GET /api/clipboard/latest/`

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/clipboard/latest/
```

It returns `200 OK` with the latest entry, or `404 Not Found` with a JSON
detail message when no entry has been created.

## WebSocket endpoint (Phase 4)

```text
ws://127.0.0.1:8000/ws/clipboard/
ws://127.0.0.1:8000/ws/clipboard/?device_id=desktop-001
```

The optional `device_id` query parameter is used for logging only.

### Supported message (Phase 4 only)

Send:

```json
{"type": "test.message", "message": "Hello WebSocket"}
```

Receive:

```json
{"type": "test.ack", "message": "Hello WebSocket"}
```

### Error responses

```json
{"type": "error", "code": "<code>", "detail": "<human-readable detail>"}
```

| Situation | `code` |
|-----------|--------|
| Non-JSON text | `invalid_json` |
| Not a JSON object | `invalid_message` |
| Unsupported `type` value | `unsupported_type` |
| Missing or non-string `message` field | `invalid_message` |

## Test

Run all tests (REST + WebSocket):

```powershell
python manage.py test
```

Expected: 10 tests, all passing.

## WebSocket smoke test

Start the dev server in one terminal, then in a second:

```powershell
python scripts/websocket_smoke_test.py
```

Expected output:

```text
WebSocket smoke test passed.
{"type": "test.ack", "message": "Hello WebSocket"}
```

If port 8000 is occupied, override the URL:

```powershell
$env:WEBSOCKET_SMOKE_URL = "ws://127.0.0.1:8001/ws/clipboard/?device_id=desktop-001"
python scripts/websocket_smoke_test.py
```
