# Desktop Clipboard Agent

Phase 3 provides a text-only desktop clipboard detector that sends each new,
non-empty value to the local Django REST API. It has no WebSocket, Android,
authentication, or multi-device synchronization support.

## Prerequisites

- Python 3.11 or later
- A graphical desktop session with clipboard access

Windows is the initial target. On Linux, `pyperclip` may require a clipboard
utility such as `xclip`, `xsel`, or `wl-clipboard`, depending on the display
server.

## Set up a virtual environment

From this directory in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

If PowerShell prevents activation, run the agent with the virtual environment's
Python directly instead:

```powershell
.\.venv\Scripts\python.exe -m pip install -e .
.\.venv\Scripts\clipboard-agent.exe
```

## Install

With the environment activated:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

This installs the project and its runtime dependencies: `pyperclip` and
`requests`.

## Backend configuration

The agent sends JSON to `POST /api/clipboard/`. These optional environment
variables configure the connection; `.env.example` shows their defaults.

| Variable | Default | Purpose |
| --- | --- | --- |
| `CLIPBOARD_API_URL` | `http://127.0.0.1:8000/api/clipboard/` | Django create-entry endpoint |
| `CLIPBOARD_DEVICE_ID` | `desktop-001` | Development device identifier |
| `CLIPBOARD_API_TIMEOUT_SECONDS` | `5` | Per-request timeout in seconds |

For example, in PowerShell:

```powershell
$env:CLIPBOARD_API_URL = "http://127.0.0.1:8000/api/clipboard/"
$env:CLIPBOARD_DEVICE_ID = "desktop-001"
```

The agent reads environment variables directly; it does not load `.env` files.

## Run

First start the backend in another PowerShell window, following
`backend/README.md`:

```powershell
cd backend
.\.venv\Scripts\Activate.ps1
python manage.py migrate
python manage.py runserver
```

Then start the agent in this directory:

```powershell
clipboard-agent
```

The agent polls every 0.5 seconds by default. To choose a different interval:

```powershell
clipboard-agent --interval 1.0
```

Press `Ctrl+C` to stop it. A typical log entry is:

```text
INFO Clipboard changed:
Hello World
INFO Sending clipboard entry to backend.
INFO Clipboard entry synchronized successfully.
```

Empty clipboard content is ignored as an event, clipboard-access failures are
logged as warnings, and duplicate text is neither logged nor sent repeatedly.
Backend connection errors, timeouts, HTTP errors, and unexpected responses are
logged without stopping clipboard monitoring. Failed content is not queued or
retried; the next new clipboard value is processed normally.

## Test

Run the unit tests without accessing the real clipboard:

```powershell
python -m unittest discover -s tests -v
```

For a manual integration test, start Django, then start the agent. Copy two
different short text values and confirm a successful-send log for each. Run:

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/clipboard/latest/
```

The result should contain the second value and `device_id` `desktop-001`.

For a failure/recovery test, stop Django, copy text, and confirm an error is
logged without the agent exiting. Restart Django, copy a new value, and confirm
the success log and latest-entry API response. Stop the agent with `Ctrl+C`.
