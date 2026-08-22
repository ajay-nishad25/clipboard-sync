# Clipboard Sync POC

A learning-focused proof of concept for near-real-time, text-only clipboard
synchronization between a Python desktop agent and a Java Android app through a
Django backend.

## Current status

Phase 5 (desktop real-time WebSocket sync) is complete. The Python desktop
agent now sends each clipboard change as a `clipboard.update` WebSocket message
to Django Channels, which validates the payload, stores it in SQLite, and
returns a `clipboard.ack`. The REST API remains available for regression
testing and manual inspection.

## Repository layout

```text
clipboard-sync/
├── backend/         # Django REST API, SQLite, Channels WebSocket
├── desktop-agent/   # Python clipboard detector and WebSocket client
├── android-app/     # Planned Java Android application
├── docs/            # Architecture, protocol, development, and progress docs
├── README.md
├── AGENTS.md
└── .gitignore
```

## Technology

- Backend: Python, Django, Django REST Framework, Django Channels, Daphne, SQLite.
- Desktop: Python, pyperclip, websockets (sync client).
- Android: Android Studio, Java (planned).

See [architecture](docs/architecture.md), [development](docs/development.md),
[protocol](docs/protocol.md), and [progress](docs/progress.md) for details.

## Getting started

See [backend/README.md](backend/README.md) for backend setup and
[desktop-agent/README.md](desktop-agent/README.md) for desktop-agent setup.

## Endpoints

| Protocol | Endpoint | Purpose |
|----------|----------|---------|
| HTTP | `POST /api/clipboard/` | Store a clipboard entry (regression testing) |
| HTTP | `GET /api/clipboard/latest/` | Retrieve the newest entry |
| WebSocket | `ws://127.0.0.1:8000/ws/clipboard/` | Real-time clipboard sync |

## Scope and safety

Text only. Authentication begins later. Never commit real secrets or `.env`.
