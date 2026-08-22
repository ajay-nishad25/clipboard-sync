# Clipboard Sync POC

A learning-focused proof of concept for near-real-time, text-only clipboard
synchronization between a Python desktop agent and a Java Android app through a
Django backend.

## Current status

Phase 4 (WebSocket infrastructure) is complete. The Django backend now serves
both a REST API and a WebSocket endpoint via Django Channels and Daphne. The
Python desktop agent continues to send clipboard text over HTTP. No real
clipboard synchronization over WebSockets exists yet; Phase 4 validates the
infrastructure only.

## Repository layout

```text
clipboard-sync/
├── backend/         # Django REST API, SQLite, and Channels WebSocket
├── desktop-agent/   # Python clipboard detector and HTTP client
├── android-app/     # Planned Java Android application
├── docs/            # Architecture, protocol, development, and progress docs
├── README.md
├── AGENTS.md
└── .gitignore
```

## Planned technology

- Backend: Python, Django, Django REST Framework, Django Channels, Daphne,
  SQLite, and WebSockets.
- Desktop: Python, an appropriate cross-platform clipboard library, and a
  WebSocket client.
- Android: Android Studio, Java, Android `ClipboardManager`, and a compatible
  WebSocket client.

See [the architecture notes](docs/architecture.md),
[development guide](docs/development.md), [protocol notes](docs/protocol.md),
and [progress tracker](docs/progress.md) for the current plan.

## Getting started

For the desktop-agent setup, API URL/device configuration, and integration
testing instructions, see [desktop-agent/README.md](desktop-agent/README.md).
For backend setup, migrations, API examples, WebSocket endpoint, and tests, see
[backend/README.md](backend/README.md).

## Endpoints

| Protocol | Endpoint | Purpose |
|----------|----------|---------|
| HTTP | `POST /api/clipboard/` | Store a clipboard entry |
| HTTP | `GET /api/clipboard/latest/` | Retrieve the newest entry |
| WebSocket | `ws://127.0.0.1:8000/ws/clipboard/` | Phase 4 test infrastructure |

## Scope and safety

This POC supports text only. Authentication begins later with a development
device-token mechanism; Google OAuth is explicitly deferred. Never commit real
secrets or a local `.env` file.

