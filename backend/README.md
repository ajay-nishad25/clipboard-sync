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

## Current Verified Baseline Endpoints (Phases 1–8)

### HTTP REST API
- `POST /api/clipboard/` — Store a clipboard entry (regression testing).
- `GET /api/clipboard/latest/` — Retrieve newest clipboard entry.

### WebSocket Endpoint
```text
ws://127.0.0.1:8000/ws/clipboard/?device_id=<id>
```

#### Supported Messages
- `test.message`: Connectivity test (`test.ack`).
- `clipboard.update`: Client outbound clipboard update (`clipboard.ack`).
- `clipboard.remote_update`: Server-side broadcast to other connected clients in `clipboard_sync_group`.

### Automated Verification
```powershell
python manage.py test
```
Expected: **17 tests**, all passing (REST, WS infrastructure, clipboard.update, remote broadcasting).

---

## Phase 9 Backend Architecture & Security Roadmap (PLANNED / NEXT)

Phase 9 transforms the backend into a production-ready, multi-user service focused on **User Data Isolation**.

### 1. User Data Isolation Model
- **User Ownership**:
  - `User` has one active `CurrentClipboard` entry.
  - `User.CurrentClipboard` stores `content`, `updated_at`, and `expires_at` (`now + 10 minutes`).
  - Copying new text overwrites the previous entry. Historical entries are not kept indefinitely.
- **10-Minute Retention**: Entries older than 10 minutes are automatically deleted or marked unavailable.

### 2. User-Scoped Channel Routing
- Replace global `clipboard_sync_group` with user-scoped channel groups: `clipboard_user_<USER_ID>`.
- Client `clipboard.update` broadcasts `clipboard.remote_update` **only** to connections belonging to the same authenticated user. User A and User B channels are strictly segregated.

### 3. Device Pairing & Authentication
- `POST /api/device/pair/`: Validates temporary pairing codes (e.g. `AB7K-29XM`) and issues persistent device tokens.
- Token validation required on WebSocket connect (`wss://`) and REST API requests.

### 4. Admin Panel & Privacy Controls
- Restricted Django admin views for authenticated administrators to monitor User devices, connection states, and clip expiration.
- Clipboard text content omitted from application logs.

### 5. Production Infrastructure
- **Database**: PostgreSQL (replacing SQLite).
- **Channel Layer**: Redis Channel Layer (replacing `InMemoryChannelLayer`).
- **Deployment**: Daphne ASGI behind reverse proxy with HTTPS/WSS (TLS).
