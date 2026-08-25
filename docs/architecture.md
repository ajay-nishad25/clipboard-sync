# Architecture

## Goal

The project synchronizes plain text clipboard data between a user's Windows desktop computer and an Android phone in near real time.

---

## Current Implementation (Phases 1–8 Verified Baseline)

```text
Windows Clipboard
      ▲  (apply remote_update / catch-up via pyperclip.copy)
      │  (set_last_content prevents feedback loop)
      ▼
ClipboardMonitor (desktop-agent — persistent device ID: desktop-<uuid>)
      │  (poll every 0.5 s; send new text only)
      ▼
ClipboardWebSocketClient (desktop-agent)
      │  - Main thread: send(content) → clipboard.update
      │  - Listener thread: recv() → queue dispatch & remote update callback
      │  - On Connect: fetch GET /api/clipboard/latest/ (catch-up)
      ▼
Django Backend (Daphne — HTTP + WebSocket on 127.0.0.1:8000)
      │
      ├─── HTTP ──► REST API
      │             GET /api/clipboard/latest/ → Android [RECEIVE CLIPBOARD] & Desktop Catch-Up
      │
      └─── WS ───► ClipboardConsumer (Group: clipboard_sync_group)
                   clipboard.update  → ClipboardEntry.create() → clipboard.ack to sender
                                     → group_send() broadcast clipboard.remote_update to others
```

### Android Architecture Constraints (MUST NOT BE CHANGED)
Android complies strictly with Android 10+ background clipboard restrictions (API 29+):
- **No Background Clipboard Harvesting**: Background services cannot access `ClipboardManager.getPrimaryClip()`.
- **Manual SEND**: User taps `[ SEND CLIPBOARD ]` in user-focused `MainActivity`, transmitting text over WebSocket.
- **Manual RECEIVE**: User taps `[ RECEIVE CLIPBOARD ]`, fetching the latest entry via `GET /api/clipboard/latest/` HTTP REST.
- **Persistent Device ID**: Saved in Android `SharedPreferences` (`android-<uuid>`).

---

## Target Multi-User Architecture (Phase 9 — PLANNED / NEXT)

Phase 9 transitions the project from a single-user proof-of-concept to a production-ready, multi-user architecture centered around **User Data Isolation**.

```text
                                 PRODUCTION ARCHITECTURE
                                 
Client Layer                    Transport & Gateway                 Backend & Persistence Layer
────────────                    ───────────────────                 ───────────────────────────
Desktop Agent A (Windows)  ──┐
                             ├──► HTTPS / WSS ──► Reverse Proxy ──► Django ASGI (Daphne)
Android App A (Java)       ──┘    (wss://api.example.com)               │
                                                                       ├──► User-Scoped Channels
                                                                       │    (Group: clipboard_user_A)
Desktop Agent B (Windows)  ──┐                                         │
                             ├──► HTTPS / WSS ──► Reverse Proxy ───────┼──► PostgreSQL (User/Devices)
Android App B (Java)       ──┘    (wss://api.example.com)               │
                                                                       └──► Redis Channel Layer
```

### 1. User Identity & Data Isolation Model
- **Ownership Hierarchy**:
  ```text
  User (User ID)
   ├── Desktop Device (Authenticated Token)
   └── Android Device (Authenticated Token)
  ```
- **Authorization Enforcement**: Device IDs alone indicate device origin but do **not** grant access. Server validates device authentication tokens to determine User ownership.
- **Strict Data Isolation**: User A and User B belong to distinct data domains. User A can never access or receive User B's clipboard data.

---

### 2. Device Pairing & Lifecycle

```text
[ INSTALL ] ──► Device ID Generated ──► [ PAIRING ENROLLMENT ] ──► Token Issued ──► [ AUTHENTICATED SYNC ]
                                                │
                                                ▼
                                    Desktop displays AB7K-29XM
                                    Android user enters code
                                    Backend associates Device → User
```

- **Enrollment Code**: Desktop Agent generates and displays a short, temporary pairing code (e.g. `AB7K-29XM`).
- **Enrollment vs Credential**: The pairing code is used solely for initial enrollment. Upon validation, the backend issues a persistent device authentication token stored securely on the client.
- **Lifecycle & Reset**:
  - Device pairing persists across restarts.
  - Device credential invalidation occurs on account unpair or device revocation.
  - App uninstall or factory reset generates a new device identity requiring re-enrollment.

---

### 3. User Clipboard Data Model & Data Minimization

- **Single Active Entry**: Each user has exactly **one** current clipboard record (`User.CurrentClipboard`), replacing unlimited historical logs.
  ```text
  User.CurrentClipboard
    ├── content (Text)
    ├── updated_at (Timestamp)
    └── expires_at (Timestamp = updated_at + 10 minutes)
  ```
- **Automatic Replacement**: Copying new text overwrites the user's single active clipboard record.

---

### 4. Ten-Minute Retention Expiration

- **Retention Window**: `expires_at` is set to `now + 10 minutes`.
- **Automatic Purge**: After 10 minutes, the backend purges or marks the clipboard entry unavailable. Stale data is never retained indefinitely.

---

### 5. User-Scoped WebSocket Routing

- **Group Name**: Replaces global `clipboard_sync_group` with user-scoped channel groups: `clipboard_user_<USER_ID>`.
- **Data Flow**:
  - Android A → Django → Validate Token → Update `User_A.CurrentClipboard` → Broadcast to `clipboard_user_A` → Desktop A.
  - Messages never cross user boundary lines to `clipboard_user_B`.

---

### 6. Admin Panel & Privacy Controls

- **Django Admin Interface**: Authorized administrators can inspect active Users, Paired Devices, connection states, and clip expiration times.
- **Privacy Enforcement**:
  - Restricted admin access with audit logging.
  - Clipboard text contents omitted from standard application logs.

---

### 7. Production Infrastructure Roadmap

| Component | POC Baseline (Phases 1–8) | Production Target (Phase 9) |
|---|---|---|
| **Database** | SQLite | PostgreSQL |
| **Channel Layer** | `InMemoryChannelLayer` | Redis Channel Layer |
| **Transport** | `http://`, `ws://` | `https://`, `wss://` (TLS) |
| **Routing** | Global `clipboard_sync_group` | User-Scoped `clipboard_user_<USER_ID>` |
| **Authentication** | Unauthenticated (trusted device_id) | Token Authentication / Server Validation |
| **Retention** | Permanent `ClipboardEntry` log | Single record per user, 10-min expiration |
| **Android Workflow** | Manual SEND / RECEIVE | Manual SEND / RECEIVE *(Preserved)* |
