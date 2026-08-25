# Protocol Notes

## Verified Baseline Protocol (Phases 1–9B)

### HTTP API
- `POST /api/clipboard/` — Store a clipboard entry (regression testing).
- `GET /api/clipboard/latest/?device_id=<id>` — Return the active, non-expired `ClipboardState` belonging to caller device's User owner account.
- `POST /api/device/pairing/create/` — Request a temporary 8-character pairing code for a desktop device (expires in 5 minutes).
  - Request: `{"device_id": "desktop-4f2a91c8"}`
  - Response (201 Created): `{"code": "AB7K-29XM", "expires_at": "2026-08-25T18:05:00Z"}`
- `POST /api/device/pair/` — Pair an Android device with a Desktop owner User account using a pairing code.
  - Request: `{"code": "AB7K-29XM", "android_device_id": "android-b17f39a0"}`
  - Response (200 OK): `{"status": "paired", "device_id": "android-b17f39a0", "user_id": 123, "user_name": "user_desktop-4f2a91c8"}`
  - Errors:
    - 400 Bad Request: `"Pairing code has expired."` / `"Pairing code has already been used."`
    - 404 Not Found: `"Invalid or unknown pairing code."`
    - 409 Conflict: `"Device is already paired with another user account."`

### WebSocket Endpoint

```text
ws://127.0.0.1:8000/ws/clipboard/?device_id=<id>
```

#### Message Types

1. **`test.message`** (Phase 4 — Connectivity Test):
   - Send: `{"type": "test.message", "message": "Hello"}`
   - Receive: `{"type": "test.ack", "message": "Hello"}`

2. **`clipboard.update`** (Phase 5 — Client Outbound Clipboard Update):
   - Send: `{"type": "clipboard.update", "device_id": "desktop-4f2a91c8", "content": "Hello World"}`
   - Receive (Sender ACK): `{"type": "clipboard.ack", "device_id": "desktop-4f2a91c8", "status": "stored"}`

3. **`clipboard.remote_update`** (Phases 7–9B — Server Inbound User-Scoped Remote Broadcast):
   - Server $\rightarrow$ Client Receive: `{"type": "clipboard.remote_update", "device_id": "android-b17f39a0", "content": "Hello from Android"}`
   - Note: Broadcasts are routed **only** to devices belonging to the sender's User channel group (`clipboard_user_<user_id>`).

#### Error Responses (Baseline)
```json
{"type": "error", "code": "<code>", "detail": "<human-readable detail>"}
```
Codes: `invalid_json`, `invalid_message`, `unsupported_type`, `invalid_content`.

---

## Phase 9 Remaining Roadmap (PLANNED / NEXT)

Phase 9C–9E upgrades transport and framing to enforce persistent **Device Tokens**, **HTTPS/WSS**, and **Production Deployment**.

### 1. Authenticated Transport & Connection (Phase 9C)

```text
wss://api.example.com/ws/clipboard/?token=<device_token>
```

- **Authentication Header / Query Parameter**: WebSocket handshake requires a valid `<device_token>`.
- **Connection Rejection**: Unauthenticated or invalid token connections are rejected immediately (`4001 Unauthorized`).

---

### 2. User-Scoped Authenticated REST API (Phase 9C)

```text
GET /api/clipboard/latest/
Header: Authorization: Bearer <device_token>
```

- **Response (200 OK)**:
  ```json
  {
    "content": "Latest user clipboard",
    "updated_at": "2026-08-25T18:05:00Z",
    "expires_at": "2026-08-25T18:15:00Z"
  }
  ```
- **Expired Entry Response (404 Not Found)**:
  - If `now > expires_at` (older than 10 minutes), the server returns `404 Not Found` (`"No clipboard entries found."`).
