# Architecture

## Goal

The project will make a text value copied on either a desktop computer or an
Android phone available on the other device in near real time. It is a POC for
one user's devices, not a production service.

## Planned components

```text
Desktop Agent (Python)  ── WebSocket ──┐
                                       │
                               Django Backend
                               - REST API
                               - Channels/WebSocket
                               - SQLite
                                       │
Android App (Java)     ── WebSocket ──┘
```

## Current implementation (Phase 5)

```text
Windows Clipboard
      │  (poll every 0.5 s via pyperclip)
      ▼
ClipboardMonitor
      │  (new text only; duplicates dropped)
      ▼
ClipboardWebSocketClient.send(content)
      │  websockets.sync.client  (persistent connection)
      │  ws://127.0.0.1:8000/ws/clipboard/?device_id=desktop-001
      ▼
Django Backend (Daphne — HTTP + WebSocket on same port)
      │
      ├─── HTTP ──► REST API
      │             POST /api/clipboard/    → ClipboardEntry + 201
      │             GET  /api/clipboard/latest/ → latest entry
      │
      └─── WS ───► ClipboardConsumer
                   clipboard.update  → validate → ClipboardEntry.objects.create → clipboard.ack
                   test.message      → test.ack
```

The desktop agent maintains one persistent WebSocket connection. On connection
loss it reconnects with bounded exponential backoff (2 s → 5 s → 15 s → 30 s).
Clipboard values that arrive during an outage are not queued.

The REST API is kept intact for regression testing and future use. The desktop
agent no longer drives HTTP for clipboard sync; only WebSocket is used.

## Identity and authentication roadmap

Phase 0 has no authentication. Early development uses development IDs/tokens.
Planned order: development token → user/device authentication → Google OAuth →
device pairing.

## Data boundary

Only plain text clipboard data is in scope. Images, files, rich text,
screenshots, passwords, and arbitrary binary clipboard data are excluded.

## Event-loop prevention (planned)

Each synchronization event will have a unique event ID and source device ID.
When a client applies a received event to its clipboard, it must recognize that
change as synchronization-generated and not send it back.

## Channel layer

Phase 5 uses `InMemoryChannelLayer`. It is not shared across processes and
resets on server restart. Redis will be introduced only if a concrete
multi-process deployment need requires it.
