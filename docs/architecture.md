# Architecture

## Goal

The project synchronizes plain text clipboard data between a user's Windows desktop computer and an Android phone in near real time.

---

## Implemented Architecture (Phases 1–9B Baseline)

```text
Windows Clipboard
      ▲  (apply remote_update / catch-up via pyperclip.copy)
      │  (set_last_content prevents feedback loop)
      ▼
ClipboardMonitor (desktop-agent — persistent device ID: desktop-<uuid>)
      │  - Generates/displays pairing code (e.g. AB7K-29XM) via POST /api/device/pairing/create/
      │  - Polls Windows clipboard every 0.5 s; sends new text only
      ▼
ClipboardWebSocketClient (desktop-agent)
      │  - Main thread: send(content) → clipboard.update
      │  - Listener thread: recv() → queue dispatch & remote update callback
      │  - On Connect: fetch GET /api/clipboard/latest/ (catch-up)
      ▼
Django Backend (Daphne — HTTP + WebSocket on 127.0.0.1:8000)
      │
      ├─── Device / User Association ──► Device (desktop-<uuid>) ──► User A ◄── Device (android-<uuid>)
      │                                                                           ▲
      │                                                                           │ (POST /api/device/pair/)
      │                                                                 Android App (Java)
      │
      ├─── REST API ──────────────────► GET /api/clipboard/latest/?device_id=...
      │                                 (Returns caller User's active ClipboardState if < 10m old)
      │
      └─── WS ────────────────────────► ClipboardConsumer (User Group: clipboard_user_<user_id>)
                                        clipboard.update → set_user_clipboard() → clipboard.ack to sender
                                                        → group_send() broadcast clipboard.remote_update to user group
```

### Android Architecture Constraints (MUST NOT BE CHANGED)
Android complies strictly with Android 10+ background clipboard restrictions (API 29+):
- **No Background Clipboard Harvesting**: Background services cannot access `ClipboardManager.getPrimaryClip()`.
- **Pair Desktop UI**: User enters 8-character code (e.g. `AB7K-29XM`) in `MainActivity` to pair with Desktop's owner User account (`POST /api/device/pair/`). Pairing state persists in `SharedPreferences`.
- **Manual SEND**: User taps `[ SEND CLIPBOARD ]` in user-focused `MainActivity`, transmitting text over WebSocket.
- **Manual RECEIVE**: User taps `[ RECEIVE CLIPBOARD ]`, fetching the latest entry via `GET /api/clipboard/latest/` HTTP REST.
- **Persistent Device ID**: Saved in Android `SharedPreferences` (`android-<uuid>`).

---

## Multi-User & Device Pairing Architecture (Phase 9)

Phase 9 transitions the project from a single-user proof-of-concept to a multi-user architecture centered around **User Data Isolation** and **Device Pairing**.

### 1. User Identity & Device Pairing Model
- **Ownership Hierarchy**:
  ```text
  User (User ID)
   ├── Desktop Device (desktop-<uuid>)
   └── Android Device (android-<uuid>)
  ```
- **Pairing Enrollment Flow (Phase 9B Implemented)**:
  ```text
  [ Desktop Startup ] ──► POST /api/device/pairing/create/ ──► Displays AB7K-29XM (Expires in 5 min)
                                                                       │
  [ Android App ]     ──► Enter Code + POST /api/device/pair/ ────────┘
                               │
                               ▼
                    Django validates code (valid, unexpired, single-use)
                    Associates Android Device with Desktop's User account
                    Returns {"status": "paired", "device_id": "android-...", "user_id": 123}
  ```
- **Security & Re-Pairing Rules**:
  - Android device cannot select or supply `user_id`. The user identity comes solely from `pairing_code` $\rightarrow$ `desktop_device` $\rightarrow$ `desktop_user`.
  - Re-pairing protection: An Android device already owned by User A cannot be silently moved to User B by submitting User B's pairing code (HTTP 409 Conflict).

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

| Component | Current Implemented (Phases 1–9B) | Production Target (Phases 9C–9E) |
|---|---|---|
| **Database** | SQLite | PostgreSQL |
| **Channel Layer** | `InMemoryChannelLayer` | Redis Channel Layer |
| **Transport** | `http://`, `ws://` | `https://`, `wss://` (TLS) |
| **Routing** | User-Scoped `clipboard_user_<user_id>` | User-Scoped `clipboard_user_<user_id>` |
| **Device Pairing** | Temporary pairing code (`AB7K-29XM`) | Temporary pairing code (`AB7K-29XM`) |
| **Authentication** | Dev Identity / Server Pairing | Persistent Token Authentication |
| **Retention** | Single record per user, 10-min expiration | Single record per user, 10-min expiration |
| **Android Workflow** | Manual SEND / RECEIVE + Pairing UI | Manual SEND / RECEIVE + Pairing UI |
