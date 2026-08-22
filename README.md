# Clipboard Sync POC

A learning-focused proof of concept for near-real-time, text-only clipboard
synchronization between a Python desktop agent and a Java Android app through a
Django backend.

## Current status

Phase 3 (desktop agent to backend) is complete. The Python desktop agent sends
each newly detected non-empty text value to the Django REST API, which stores
it in SQLite. This is one-way development integration only, not device sync.

## Repository layout

```text
clipboard-sync/
├── backend/         # Django REST API and SQLite database
├── desktop-agent/   # Python clipboard detector and HTTP client
├── android-app/     # Planned Java Android application
├── docs/            # Architecture, protocol, development, and progress docs
├── README.md
├── AGENTS.md
└── .gitignore
```

## Planned technology

- Backend: Python, Django, Django REST Framework, Django Channels, SQLite, and
  WebSockets.
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
For backend setup, migrations, API examples, and tests, see
[backend/README.md](backend/README.md).

## Scope and safety

This POC supports text only. Authentication begins later with a development
device-token mechanism; Google OAuth is explicitly deferred. Never commit real
secrets or a local `.env` file.
