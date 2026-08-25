# Clipboard Sync Backend

Django REST Framework and Django Channels backend for clipboard synchronization.

## Prerequisites

- Python 3.11 or later

## Environment Setup (Development Baseline)

From `backend/` in PowerShell:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
```

Set a local Django development secret:

```powershell
$env:DJANGO_SECRET_KEY = "choose-a-long-unique-local-development-value"
```

Install dependencies:

```powershell
python -m pip install --upgrade pip
python -m pip install -e .
```

Database migrations & start dev server:

```powershell
python manage.py migrate
python manage.py runserver     # Daphne serves HTTP + WebSocket on http://127.0.0.1:8000/
```

---

## Current Verified Endpoints (Phases 1–9C Implemented)

### HTTP REST API
- `POST /api/clipboard/` — Store a clipboard entry (requires `Authorization: Bearer <device_token>`).
- `GET /api/clipboard/latest/` — Retrieve newest, non-expired `ClipboardState` belonging to caller's authenticated User (requires `Authorization: Bearer <device_token>`).
- `POST /api/device/credential/register/` — Register desktop device and obtain device authentication token.
- `POST /api/device/pairing/create/` — Generate temporary 8-character desktop pairing code (e.g. `AB7K-29XM`, 5-min expiration).
- `POST /api/device/pair/` — Pair Android device with Desktop's owner User account using a pairing code; returns issued device credential token.
- `POST /api/device/unpair/` — Revoke device credential token.

### WebSocket Endpoint
```text
ws://127.0.0.1:8000/ws/clipboard/?token=<device_token>&device_id=<device_id>
```

#### Supported Messages
- `test.message`: Connectivity test (`test.ack`).
- `clipboard.update`: Client outbound clipboard update (`clipboard.ack`).
- `clipboard.remote_update`: Server-side broadcast to user-scoped channel group (`clipboard_user_<user_id>`).

### Automated Verification (30 tests)
```powershell
python manage.py check
python manage.py makemigrations --check
python manage.py test
```
Expected: **30 tests**, all passing (`OK`).

---

## Phase 9 Remaining Roadmap (PLANNED / NEXT)

- **Phase 9D**: Production Configuration & HTTPS/WSS (TLS certificate validation).
- **Phase 9E**: PostgreSQL, Redis Channel Layer, and deployment hardening.
