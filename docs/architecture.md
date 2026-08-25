# Architecture

## Goal

The project synchronizes plain text clipboard data between a user's Windows desktop computer and an Android phone in near real time using authenticated device credentials and user data isolation.

---

## Implemented Architecture (Phases 1–9C Baseline)

```text
Windows Clipboard
      ▲  (apply remote_update / catch-up via pyperclip.copy)
      │  (set_last_content prevents feedback loop)
      ▼
ClipboardMonitor (desktop-agent — persistent device ID: desktop-<uuid>, credential: devtok_...)
      │  - Generates/displays pairing code (e.g. AB7K-29XM) via POST /api/device/pairing/create/
      │  - Connects to WS with ?token=<credential>
      │  - Polls Windows clipboard every 0.5 s; sends new text only
      ▼
ClipboardWebSocketClient (desktop-agent)
      │  - Main thread: send(content) → clipboard.update
      │  - Listener thread: recv() → queue dispatch & remote update callback
      │  - On Connect: fetch GET /api/clipboard/latest/ with Authorization: Bearer <credential>
      ▼
Django Backend (Daphne — HTTP + WebSocket on 127.0.0.1:8000)
      │
      ├─── Token Authentication ───────► DeviceCredential (SHA-256 token_hash) ──► Device ──► User A
      │                                                                                         ▲
      │                                                                                         │ (Bearer <token>)
      │                                                                               Android App (Java)
      │
      ├─── REST API ──────────────────► GET /api/clipboard/latest/ (Authorization: Bearer <token>)
      │                                 (Returns caller User's active ClipboardState if < 10m old)
      │
      └─── WS ────────────────────────► ClipboardConsumer (User Group: clipboard_user_<user_id>)
                                        Authenticate ?token=<token> → join user_group
                                        clipboard.update → set_user_clipboard() → clipboard.ack to sender
                                                        → group_send() broadcast clipboard.remote_update to user group
```

### Android Architecture Constraints (MUST NOT BE CHANGED)
Android complies strictly with Android 10+ background clipboard restrictions (API 29+):
- **No Background Clipboard Harvesting**: Background services cannot access `ClipboardManager.getPrimaryClip()`.
- **Pair Desktop UI**: User enters 8-character code (e.g. `AB7K-29XM`) in `MainActivity` to pair with Desktop's owner User account (`POST /api/device/pair/`). Receives and stores `device_token` secret in `SharedPreferences`.
- **Manual SEND**: User taps `[ SEND CLIPBOARD ]` in user-focused `MainActivity`, transmitting text over authenticated WebSocket (`?token=<device_token>`).
- **Manual RECEIVE**: User taps `[ RECEIVE CLIPBOARD ]`, fetching the latest entry via `GET /api/clipboard/latest/` HTTP REST with `Authorization: Bearer <device_token>`.
- **Persistent Device ID & Token**: Saved in Android `SharedPreferences`.

---

## Multi-User & Authenticated Security Architecture (Phase 9)

Phase 9 transitions the project from a single-user proof-of-concept to a multi-user architecture centered around **User Data Isolation** and **Authenticated Device Credentials**.

### 1. Authenticated Device Ownership Model
- **Ownership Hierarchy**:
  ```text
  User (User ID)
   ├── Desktop Device (desktop-<uuid>) ── DeviceCredential (SHA-256 token_hash)
   └── Android Device (android-<uuid>) ── DeviceCredential (SHA-256 token_hash)
  ```
- **Credential Issuance & Authentication Flow (Phase 9C Implemented)**:
  - **Pairing Bootstrap**: Android pairing (`POST /api/device/pair/`) issues an opaque device credential token (`devtok_<32 hex chars>`) stored in client `SharedPreferences`.
  - **Desktop Registration**: Desktop requests/registers credential on boot (`POST /api/device/credential/register/`) and persists token in `~/.clipboard_sync/token.txt`.
  - **Backend Storage**: Raw tokens are **never** stored in database; only SHA-256 hex digests (`token_hash`) are saved in `DeviceCredential`.
  - **REST Auth**: `Authorization: Bearer <token>` header required for all clipboard data operations.
  - **WebSocket Auth**: `?token=<token>` query parameter validated on connect (`connect()`). Connections without valid/active tokens are rejected with code `4001`.
  - **Revocation & Unpair**: Setting `revoked_at` timestamp immediately invalidates token for all future REST and WebSocket authentication.

---

### 2. User Clipboard Data Model & Expiration
- **Single Active Entry per User**: Each user has exactly **one** current clipboard record (`ClipboardState`), replacing historical logs.
- **10-Minute Expiration**: `expires_at` is set to `now + 10 minutes`. On access, if `expires_at <= now`, the record is automatically purged from the database and returns 404 Not Found.

---

### 3. User-Scoped WebSocket Routing
- **Group Name**: User-scoped channel groups: `clipboard_user_<user_id>`.
- **Data Flow**: Broadcasts (`clipboard.remote_update`) remain within `clipboard_user_<user_id>` and never cross user boundary lines.

---

### 4. Infrastructure Roadmap

| Component | Current Implemented (Phases 1–9C) | Production Target (Phases 9D–9E) |
|---|---|---|
| **Database** | SQLite | PostgreSQL |
| **Channel Layer** | `InMemoryChannelLayer` | Redis Channel Layer |
| **Transport** | `http://`, `ws://` | `https://`, `wss://` (TLS) |
| **Routing** | User-Scoped `clipboard_user_<user_id>` | User-Scoped `clipboard_user_<user_id>` |
| **Device Pairing** | Temporary pairing code (`AB7K-29XM`) | Temporary pairing code (`AB7K-29XM`) |
| **Authentication** | Token Auth (SHA-256 Hashing, Bearer & `?token=`) | Token Auth + TLS Certificate Validation |
| **Retention** | Single record per user, 10-min expiration | Single record per user, 10-min expiration |
| **Android Workflow** | Manual SEND / RECEIVE + Pairing UI | Manual SEND / RECEIVE + Pairing UI |
