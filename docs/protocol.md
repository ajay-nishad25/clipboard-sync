# Protocol Notes

## Verified Baseline Protocol (Phases 1–9C)

### HTTP REST API

- `POST /api/clipboard/` — Store a clipboard entry (requires `Authorization: Bearer <device_token>`).
- `GET /api/clipboard/latest/` — Return the active, non-expired `ClipboardState` belonging to caller's authenticated User account (requires `Authorization: Bearer <device_token>`).
- `POST /api/device/credential/register/` — Register desktop device and obtain an authentication token secret.
  - Request: `{"device_id": "desktop-4f2a91c8"}`
  - Response (201 Created): `{"device_id": "desktop-4f2a91c8", "credential": "devtok_..."}`
- `POST /api/device/pairing/create/` — Request a temporary 8-character pairing code for a desktop device (expires in 5 minutes).
  - Request: `{"device_id": "desktop-4f2a91c8"}`
  - Response (201 Created): `{"code": "AB7K-29XM", "expires_at": "2026-08-25T18:05:00Z"}`
- `POST /api/device/pair/` — Pair an Android device with a Desktop owner User account using a pairing code. Returns issued device credential.
  - Request: `{"code": "AB7K-29XM", "android_device_id": "android-b17f39a0"}`
  - Response (200 OK): `{"status": "paired", "device_id": "android-b17f39a0", "credential": "devtok_...", "user_id": 123, "user_name": "user_desktop-4f2a91c8"}`
  - Errors:
    - 400 Bad Request: `"Pairing code has expired."` / `"Pairing code has already been used."`
    - 404 Not Found: `"Invalid or unknown pairing code."`
    - 409 Conflict: `"Device is already paired with another user account."`
- `POST /api/device/unpair/` — Revoke the caller device's active authentication token (requires `Authorization: Bearer <device_token>`).
  - Response (200 OK): `{"status": "unpaired", "detail": "Device credential revoked successfully."}`

### WebSocket Endpoint

```text
ws://127.0.0.1:8000/ws/clipboard/?token=<device_token>&device_id=<device_id>
```

- Connection handshakes without a valid, active token are rejected immediately (close code `4001`).

#### Supported Message Types

1. **`test.message`** (Phase 4 — Connectivity Test):
   - Send: `{"type": "test.message", "message": "Hello"}`
   - Receive: `{"type": "test.ack", "message": "Hello"}`

2. **`clipboard.update`** (Phases 5–9C — Authenticated Outbound Clipboard Update):
   - Send: `{"type": "clipboard.update", "device_id": "desktop-4f2a91c8", "content": "Hello World"}`
   - Receive (Sender ACK): `{"type": "clipboard.ack", "device_id": "desktop-4f2a91c8", "status": "stored"}`

3. **`clipboard.remote_update`** (Phases 7–9C — Server Inbound User-Scoped Remote Broadcast):
   - Server $\rightarrow$ Client Receive: `{"type": "clipboard.remote_update", "device_id": "android-b17f39a0", "content": "Hello from Android"}`
   - Note: Broadcasts are routed **only** to connections joined to the authenticated User channel group (`clipboard_user_<user_id>`).

#### Error Responses (Baseline)
```json
{"type": "error", "code": "<code>", "detail": "<human-readable detail>"}
```
Codes: `invalid_json`, `invalid_message`, `unsupported_type`, `invalid_content`, `unauthorized`.

---

## Phase 9 Remaining Roadmap (PLANNED / NEXT)

Phase 9D–9E upgrades transport and deployment infrastructure to enforce **HTTPS/WSS** and **Production Deployment**.

### 1. Production Configuration & TLS (Phase 9D)

```text
wss://api.example.com/ws/clipboard/?token=<device_token>
```

- Enforces TLS certificate validation for `https://` and `wss://` in production.

---

### 2. Infrastructure Hardening (Phase 9E)

- PostgreSQL database integration.
- Redis channel layer for multi-worker scaling.
- Reverse proxy configuration with rate limiting and logging privacy.
