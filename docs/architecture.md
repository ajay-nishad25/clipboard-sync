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

## Current implementation (Phase 7)

```text
Windows Clipboard
      ▲  (apply remote_update via pyperclip.copy)
      │  (set_last_content prevents feedback loop)
      ▼
ClipboardMonitor (desktop-agent)
      │  (poll every 0.5 s; send new text only)
      ▼
ClipboardWebSocketClient (desktop-agent)
      │  - Main thread: send(content) → clipboard.update
      │  - Listener thread: recv() → queue dispatch & remote update callback
      ▼
Django Backend (Daphne — HTTP + WebSocket on same port)
      │
      ├─── HTTP ──► REST API
      │             GET  /api/clipboard/latest/ → Android [RECEIVE CLIPBOARD]
      │
      └─── WS ───► ClipboardConsumer (Group: clipboard_sync_group)
                   clipboard.update  → ClipboardEntry.create() → clipboard.ack to sender
                                     → group_send() broadcast clipboard.remote_update to others
```

The desktop agent maintains one persistent WebSocket connection. On connection
loss it reconnects with bounded backoff (2 s → 5 s → 15 s → 30 s).
Clipboard values that arrive during an outage are not queued.

The REST API is kept intact for regression testing and Android manual fetch.

## Identity and authentication roadmap

Phase 0 has no authentication. Early development uses development IDs/tokens.
Planned order: development token → user/device authentication → Google OAuth →
device pairing.

## Data boundary

Only plain text clipboard data is in scope. Images, files, rich text,
screenshots, passwords, and arbitrary binary clipboard data are excluded.

## Event-loop prevention (Phase 7)

When Desktop Agent receives `clipboard.remote_update` over WebSocket:
1. It writes the text to the Windows clipboard via `pyperclip.copy(content)`.
2. It immediately updates `ClipboardMonitor.set_last_content(content)`.
3. When the monitoring loop polls `read_clipboard()` 0.5s later, `content == self._last_content` evaluates to `True`, automatically suppressing outbound synchronization and preventing feedback loops.

## Channel layer

Phase 7 uses `InMemoryChannelLayer`. It is not shared across processes and
resets on server restart. Redis will be introduced only if a concrete
multi-process deployment need requires it.
