# Desktop Clipboard Agent

Phase 5 connects the clipboard detector to the Django backend via WebSocket.
Each new, non-empty clipboard text value is sent as a `clipboard.update`
message. Django stores it and returns `clipboard.ack`. The agent uses a
persistent WebSocket connection with bounded-backoff reconnection.

## Prerequisites

- Python 3.11 or later
- A graphical desktop session with clipboard access
- The Django backend running (see `backend/README.md`)

Windows is the initial target. On Linux, `pyperclip` may require a clipboard
utility such as `xclip`, `xsel`, or `wl-clipboard`.

## Set up a virtual environment

From `desktop-agent/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

## Install

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

Installs `pyperclip`, `requests`, and `websockets`.

## Configuration

All variables are optional. `.env.example` shows their defaults.

| Variable | Default | Purpose |
|----------|---------|---------|
| `CLIPBOARD_WS_URL` | `ws://127.0.0.1:8000/ws/clipboard/` | WebSocket endpoint |
| `CLIPBOARD_DEVICE_ID` | `desktop-001` | Development device identifier |
| `CLIPBOARD_API_URL` | `http://127.0.0.1:8000/api/clipboard/` | REST endpoint (regression testing only) |
| `CLIPBOARD_API_TIMEOUT_SECONDS` | `5` | REST request timeout in seconds |

Example override in PowerShell:

```powershell
$env:CLIPBOARD_WS_URL = "ws://127.0.0.1:8001/ws/clipboard/"
$env:CLIPBOARD_DEVICE_ID = "desktop-002"
```

The agent reads environment variables directly; it does not load `.env` files.

## Run

Start the backend in one terminal:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py runserver
```

Then start the agent in a second terminal:

```powershell
cd desktop-agent
.\.venv\Scripts\Activate.ps1
clipboard-agent
```

Or with a custom polling interval:

```powershell
clipboard-agent --interval 1.0
```

Press `Ctrl+C` to stop. A typical session looks like:

```text
INFO WebSocket connection established to ws://127.0.0.1:8000/ws/clipboard/?device_id=desktop-001.
INFO Clipboard changed:
Hello from Windows
INFO Clipboard entry synchronized successfully via WebSocket.
```

### Duplicate prevention

If the same text is copied twice in a row, only the first occurrence is sent.

### Connection failures

If Django is unavailable, the agent logs a warning and schedules a reconnection
attempt using bounded backoff (2 s → 5 s → 15 s → 30 s). The clipboard monitor
continues running without crashing. Clipboard values copied during an outage
are not queued or retried; they are silently dropped. After Django restarts, the
next new clipboard value triggers a reconnection and resumes sync.

## Test

```powershell
python -m unittest discover -s tests -v
```

Expected: **37 tests**, all passing.

## Manual integration test

1. Start Django (`python manage.py runserver` from `backend/`).
2. Start the agent (`clipboard-agent` from `desktop-agent/`).
3. Copy a short text value — confirm the WebSocket established log and sync log.
4. Copy a multiline value — confirm it is stored.
5. Copy the same value again — confirm no duplicate send in the logs.
6. Verify the stored value:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/clipboard/latest/
```

## Failure/recovery test

1. Start the agent, copy a value, confirm sync.
2. Stop Django. Copy a value. Confirm the agent logs a connection failure and
   does **not** crash.
3. Restart Django. Copy a **new** value. Confirm the agent reconnects and
   syncs the new value.
4. Stop the agent with `Ctrl+C`.
