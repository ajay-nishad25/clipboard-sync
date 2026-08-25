# Protocol Notes

## Verified Baseline Protocol (Phases 1–8)

### HTTP API
- `POST /api/clipboard/` — Store a clipboard entry (regression testing).
- `GET /api/clipboard/latest/` — Return the most recently created clipboard entry.

### WebSocket Endpoint (Phases 4–8)

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

3. **`clipboard.remote_update`** (Phase 7 — Server Inbound Remote Broadcast):
   - Server → Client Receive: `{"type": "clipboard.remote_update", "device_id": "android-b17f39a0", "content": "Hello from Android"}`

#### Error Responses (Baseline)
```json
{"type": "error", "code": "<code>", "detail": "<human-readable detail>"}
```
Codes: `invalid_json`, `invalid_message`, `unsupported_type`, `invalid_content`.

---

## Phase 9 Protocol Roadmap (PLANNED / NEXT)

Phase 9 upgrades transport and framing to enforce **User Identity**, **Device Pairing**, and **Authentication**.

### 1. Authenticated Transport & Connection

```text
wss://api.example.com/ws/clipboard/?token=<device_token>
```

- **Authentication Header / Query Parameter**: WebSocket handshake requires a valid `<device_token>`.
- **Connection Rejection**: Unauthenticated or invalid token connections are rejected immediately (`4001 Unauthorized`).

---

### 2. Device Pairing Endpoint

```text
POST /api/device/pair/
```

- **Request**:
  ```json
  {
    "device_id": "android-b17f39a0",
    "pairing_code": "AB7K-29XM"
  }
  ```
- **Response (200 OK)**:
  ```json
  {
    "status": "paired",
    "user_id": "user_12345",
    "device_token": "devtok_9876543210abcdef"
  }
  ```
- **Error (400 Bad Request / 401 Unauthorized)**:
  ```json
  {
    "error": "invalid_pairing_code",
    "detail": "Pairing code expired or invalid."
  }
  ```

---

### 3. User-Scoped WebSocket Broadcast

- Inbound `clipboard.remote_update` messages are routed **only** to connections belonging to the authenticated `User` (`clipboard_user_<USER_ID>`).
- Payload contains sender device metadata:
  ```json
  {
    "type": "clipboard.remote_update",
    "sender_device_id": "android-b17f39a0",
    "content": "Authenticated user text",
    "timestamp": "2026-08-25T18:00:00Z"
  }
  ```

---

### 4. Authenticated REST API & 10-Minute Expiration

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
  - If `now > expires_at` (older than 10 minutes), the server returns `404 Not Found` (`"Clipboard entry expired"`).
