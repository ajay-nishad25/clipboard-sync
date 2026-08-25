# Desktop Clipboard Agent

Python desktop client for synchronizing plain-text clipboard changes with the Django backend.

## Prerequisites

- Python 3.11 or later
- Graphical desktop session with clipboard access
- Django backend running

Windows is the primary target. On Linux, `pyperclip` requires `xclip`, `xsel`, or `wl-clipboard`.

---

## Environment Setup (Development Baseline)

From `desktop-agent/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e .
```

### Configuration Options
All variables are optional; defaults shown below:

| Variable | Default | Purpose |
|----------|---------|---------|
| `CLIPBOARD_WS_URL` | `ws://127.0.0.1:8000/ws/clipboard/` | WebSocket endpoint |
| `CLIPBOARD_REST_LATEST_URL` | `http://127.0.0.1:8000/api/clipboard/latest/` | HTTP REST catch-up endpoint |
| `CLIPBOARD_PAIRING_URL` | `http://127.0.0.1:8000/api/device/pairing/create/` | HTTP REST pairing code endpoint |
| `CLIPBOARD_DEVICE_ID` | `~/.clipboard_sync/device_id.txt` | Auto-generated persistent `desktop-<uuid>` ID |
| `CLIPBOARD_API_TIMEOUT_SECONDS` | `5` | Request timeout in seconds |

### Run Agent
```powershell
clipboard-agent
# Or with custom polling interval:
clipboard-agent --interval 1.0
```

### Automated Verification
```powershell
python -m unittest discover -s tests -v
```
Expected: **45 tests**, all passing.

---

## Verified Baseline Features (Phases 1–9B Implemented)

- **Pairing Code Banner**: On launch, requests an 8-character pairing code (`AB7K-29XM`, 5-min expiration) from `POST /api/device/pairing/create/` and displays a terminal banner for Android pairing.
- **Real-Time Outbound Sync**: Monitors Windows clipboard and sends new text via `clipboard.update` over WebSocket.
- **Remote Update Inbound Listener**: Receives `clipboard.remote_update` from Django, updates Windows clipboard via `pyperclip.copy()`, and suppresses feedback loops via `monitor.set_last_content()`.
- **Startup / Reconnect Catch-Up**: On connection establishment, fetches `GET /api/clipboard/latest/` to recover missed clipboard updates.
- **Persistent Device ID**: Saved locally in `~/.clipboard_sync/device_id.txt` (`desktop-<uuid>`).

---

## Phase 9 Remaining Roadmap (PLANNED / NEXT)

- **Phase 9C**: Persistent device authentication tokens (`token.txt`) and authenticated WebSocket handshake (`wss://`).
