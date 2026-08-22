# Clipboard Sync Backend

Phase 5 makes `clipboard.update` a first-class WebSocket message. The desktop
agent sends clipboard changes over WebSocket; Django validates, stores, and
acknowledges them. The REST API from Phases 2–3 remains intact.

## Prerequisites

- Python 3.11 or later

## Environment setup

From `backend/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Set a local Django development secret:

```powershell
$env:DJANGO_SECRET_KEY = "choose-a-long-unique-local-development-value"
```

## Install dependencies

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

`pyproject.toml` declares `Django`, `djangorestframework`, `channels`, and
`daphne`. All are installed by the command above.

## Database migrations

```powershell
python manage.py migrate
```

## Start the development server

```powershell
python manage.py runserver
```

Daphne (listed first in `INSTALLED_APPS`) takes over `runserver` and handles
both HTTP and WebSocket connections on `http://127.0.0.1:8000/`.

## REST API

### Create an entry

`POST /api/clipboard/`

```json
{"device_id": "desktop-001", "content": "Hello World"}
```

Returns `201 Created`. Used for regression testing; in normal Phase 5 operation
the desktop agent uses WebSocket instead.

### Get the latest entry

`GET /api/clipboard/latest/`

Returns `200 OK` with the latest entry, or `404 Not Found`.

## WebSocket endpoint

```text
ws://127.0.0.1:8000/ws/clipboard/
ws://127.0.0.1:8000/ws/clipboard/?device_id=desktop-001
```

### Supported messages

#### `test.message` (Phase 4 — still supported)

Send: `{"type": "test.message", "message": "Hello WebSocket"}`
Receive: `{"type": "test.ack", "message": "Hello WebSocket"}`

#### `clipboard.update` (Phase 5)

Send:

```json
{"type": "clipboard.update", "device_id": "desktop-001", "content": "Hello from Windows"}
```

Receive on success:

```json
{"type": "clipboard.ack", "device_id": "desktop-001", "status": "stored"}
```

### Error responses

```json
{"type": "error", "code": "<code>", "detail": "<detail>"}
```

| Situation | `code` |
|-----------|--------|
| Non-JSON text | `invalid_json` |
| Not a JSON object | `invalid_message` |
| Unsupported `type` | `unsupported_type` |
| Missing/non-string `message` (test.message) | `invalid_message` |
| Missing/non-string `device_id` (clipboard.update) | `invalid_message` |
| Empty or non-string `content` | `invalid_content` |

## Tests

```powershell
python manage.py test
```

Expected: **15 tests**, all passing (5 REST, 5 WebSocket infrastructure, 5
clipboard.update).

## WebSocket smoke test

Start the dev server, then in a second terminal:

```powershell
python scripts/websocket_smoke_test.py
```

Override the URL if port 8000 is occupied:

```powershell
$env:WEBSOCKET_SMOKE_URL = "ws://127.0.0.1:8001/ws/clipboard/?device_id=desktop-001"
python scripts/websocket_smoke_test.py
```
