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
Expected: **43 tests**, all passing.

---

## Verified Baseline Features (Phases 1–8)

- **Real-Time Outbound Sync**: Monitors Windows clipboard and sends new text via `clipboard.update` over WebSocket.
- **Remote Update Inbound Listener**: Receives `clipboard.remote_update` from Django, updates Windows clipboard via `pyperclip.copy()`, and suppresses feedback loops via `monitor.set_last_content()`.
- **Startup / Reconnect Catch-Up**: On connection establishment, fetches `GET /api/clipboard/latest/` to recover missed clipboard updates.
- **Persistent Device ID**: Saved locally in `~/.clipboard_sync/device_id.txt` (`desktop-<uuid>`).

---

## Phase 9 Desktop Agent Roadmap (PLANNED / NEXT)

Phase 9 integrates Desktop Agent into the multi-user architecture:

1. **Device Pairing Code Generation**:
   - On initial launch or un-paired state, the agent displays a 8-character pairing code (e.g. `AB7K-29XM`) for Android enrollment.
2. **Persistent Device Credential**:
   - After pairing completes, the agent receives and stores a secure device authentication token locally (`~/.clipboard_sync/token.txt`).
3. **Authenticated Transport**:
   - Connects using production WSS endpoints (`wss://api.example.com/ws/clipboard/?token=<device_token>`).
4. **Loop Prevention & Catch-Up**:
   - Retains existing `set_last_content()` feedback loop suppression and startup HTTP catch-up.
