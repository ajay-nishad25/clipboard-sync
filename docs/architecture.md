# Architecture

## Goal

The project will make a text value copied on either a desktop computer or an
Android phone available on the other device in near real time. It is a POC for
one user's devices, not a production service.

## Planned components

```text
Desktop Agent (Python)  ── HTTP / WebSocket ──┐
                                              │
                                      Django Backend
                                      - REST API
                                      - Channels/WebSocket
                                      - SQLite (initially)
                                              │
Android App (Java)     ── HTTP / WebSocket ──┘
```

- The desktop agent will run on Windows first and be designed with Linux in
  mind.
- The backend will begin with SQLite. Redis is not part of Phase 0 and will be
  added only if Django Channels implementation actually requires it.
- The Android app will initially receive and display messages before it writes
  to the system clipboard.

## Current implementation

Phase 1 implements a local desktop detector. It polls the operating-system
clipboard through `pyperclip`, logs each new non-empty text value once, and
handles clipboard read failures without exiting.

Phase 2 adds a local Django REST API with a SQLite database. Phase 3 connects
the desktop agent to its existing `POST /api/clipboard/` endpoint using JSON
and the development device ID `desktop-001`.

Phase 4 adds Django Channels and WebSocket infrastructure to the backend. The
server now runs under Daphne, which handles both HTTP and WebSocket connections.
A `ClipboardConsumer` accepts WebSocket connections, validates a Phase 4
test-only `test.message` round-trip, and returns structured errors for invalid
input. The desktop agent remains HTTP-only.

```text
                    Django Backend (Daphne)
                            │
             ┌──────────────┴──────────────┐
             │                             │
             ▼                             ▼
       REST API                      WebSocket
  POST /api/clipboard/          ws/clipboard/
  GET  /api/clipboard/latest/   ClipboardConsumer
             │                             │
             ▼                             ▼
  SQLite ClipboardEntry           In-memory channel layer
                                  (Phase 4: test messages only)
```

The desktop agent uses `requests` with a five-second default timeout. It logs
network, timeout, HTTP-status, and unexpected-response failures, then keeps
monitoring. It does not queue or retry failed values.

## Identity and authentication roadmap

Phase 0 has no authentication implementation. Early development will identify
devices with development IDs/tokens. The planned order is development token,
user/device authentication, Google OAuth, then device pairing.

## Data boundary

Only plain text clipboard data is in scope. Images, files, rich text,
screenshots, passwords, and arbitrary binary clipboard data are excluded until
the text workflow is reliable.

## Event-loop prevention (planned)

Each synchronization event will have a unique event ID and source device ID.
When a client applies a received event to its clipboard, it must recognize that
change as synchronization-generated and not send the same event back to the
server.
