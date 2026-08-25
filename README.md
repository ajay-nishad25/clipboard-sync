# Clipboard Sync

A cross-platform clipboard synchronization system between a Python desktop agent (Windows) and a Java Android app through a Django backend.

## Current Status (Verified Baseline)

Phases 1–8 are **complete and verified**:
- **Real-Time Desktop Sync**: Windows desktop agent syncs clipboard updates over WebSocket (`clipboard.update` / `clipboard.remote_update`).
- **Manual Android Sync**: Java Android application uses `[ SEND CLIPBOARD ]` (WebSocket) and `[ RECEIVE CLIPBOARD ]` (`GET /api/clipboard/latest/`) to respect Android 10+ background clipboard restrictions.
- **Desktop Catch-Up**: Desktop Agent fetches the latest server entry on startup or reconnection without triggering feedback loops.
- **Persistent Device IDs**: Auto-generated persistent UUIDs for Desktop and Android installations.

See [Phase 9 Roadmap](#phase-9-roadmap--target-architecture-planned--next) for upcoming multi-user identity and production isolation architecture.

---

## Repository Layout

```text
clipboard-sync/
├── backend/         # Django REST API, SQLite, Channels WebSocket (Daphne)
├── desktop-agent/   # Python clipboard detector, listener thread & WebSocket client
├── android-app/     # Java Android application (Manual SEND/RECEIVE UI & Service)
├── docs/            # Architecture, protocol, development, and progress docs
├── README.md
├── AGENTS.md
└── .gitignore
```

---

## Technology Stack

- **Backend**: Python, Django, Django REST Framework, Django Channels, Daphne, SQLite (`InMemoryChannelLayer`).
- **Desktop Agent**: Python, `pyperclip`, `websockets` (sync client with background listener thread).
- **Android App**: Java 17, Android SDK API 34, `OkHttp 5.5.0` (WebSocket & HTTP REST).

See [architecture](docs/architecture.md), [development](docs/development.md), [protocol](docs/protocol.md), and [progress](docs/progress.md) for complete details.

---

## Endpoints (Current POC Baseline)

| Protocol | Endpoint | Purpose |
|----------|----------|---------|
| HTTP | `POST /api/clipboard/` | Store a clipboard entry (regression testing) |
| HTTP | `GET /api/clipboard/latest/` | Retrieve newest clipboard entry (Android RECEIVE & Desktop Catch-Up) |
| WebSocket | `ws://127.0.0.1:8000/ws/clipboard/?device_id=<id>` | Real-time bidirectional clipboard sync & remote update broadcast |

---

## Phase 9 Roadmap & Target Architecture (PLANNED / NEXT)

Phase 9 transitions the project from a single-user local proof-of-concept into a multi-user, production-ready architecture focused on **User Data Isolation**:

```text
User A (User ID A)                          User B (User ID B)
  ├── Desktop A (Authenticated)               ├── Desktop B (Authenticated)
  └── Android A (Paired)                      └── Android B (Paired)
        │                                           │
        ▼                                           ▼
Channel: clipboard_user_A                   Channel: clipboard_user_B
  (Isolated to User A)                        (Isolated to User B)
```

### Key Target Features
1. **User Data Isolation**: Multi-user model with user-scoped channel routing (`clipboard_user_<USER_ID>`). User A and User B cannot access or receive each other's clipboard data.
2. **Device Pairing**: Desktop Agent generates a short enrollment code (e.g. `AB7K-29XM`); Android app exchanges code for a persistent device credential token.
3. **Single Active Clipboard & 10-Minute Expiration**: Each user retains exactly one current clipboard entry with automatic 10-minute retention expiration (`expires_at = now + 10m`).
4. **Production Security & Transport**: HTTPS (`https://`) and WSS (`wss://`), token authentication, restricted admin panel, and no clipboard text in logs.

---

## Scope and Safety

- Plain text clipboard only. Images, files, rich text, screenshots, and passwords are excluded.
- Android 10+ background clipboard rules are respected (no background harvesting).
- Never commit real credentials or `.env` files.
