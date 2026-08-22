# Clipboard Sync POC — Project Instructions

## Purpose

Clipboard Sync is a learning-focused, cross-platform proof of concept for
synchronizing **text-only** clipboard content between a Python desktop agent
(Windows first, Linux-aware) and an Android application.  It is deliberately
incremental: complete, test, document, and review each phase before beginning
the next.

## Architecture

The planned system has three components:

- `backend/`: Django backend using Django REST Framework, Django Channels,
  WebSockets, and SQLite for the initial POC. Redis is introduced only when a
  concrete Channels deployment need requires it.
- `desktop-agent/`: Python desktop client using an appropriate cross-platform
  clipboard library (such as `pyperclip`) and a WebSocket client. It targets
  Windows first while retaining Linux-compatible design.
- `android-app/`: Android Studio application written in Java, using Android's
  `ClipboardManager` and an Android-compatible WebSocket client. Do not change
  it to Kotlin unless explicitly requested.

The intended data flow is desktop/Android client ↔ Django HTTP or WebSocket
endpoint ↔ database/other connected device. All devices will eventually belong
to a single authenticated user, but Google OAuth is intentionally deferred.

## Development Phases

0. Create the monorepo structure and documentation only.
1. Detect text clipboard changes locally in the Python desktop agent; log them.
2. Create the Django backend, a small clipboard model, and development APIs.
3. Send desktop clipboard changes to the backend over HTTP.
4. Add and independently test Django Channels/WebSocket infrastructure.
5. Send structured desktop clipboard events over WebSockets.
6. Create the Java Android app; receive and display WebSocket messages only.
7. Integrate Android clipboard read/write with loop prevention.

Do not start a later phase unless the user explicitly requests it. Do not claim
a phase is complete until its relevant checks have passed and its documentation
has been updated.

## Engineering Rules

- Start every task by inspecting the repository and identifying the active
  phase.
- Implement only the requested phase or narrowly requested task.
- Keep the POC simple. Prefer readable, focused modules and small functions to
  abstractions or patterns that do not solve a present problem.
- Python code follows PEP 8, uses meaningful names, Python `logging`, and type
  hints where useful. Handle clipboard and network errors visibly; do not
  silently swallow them.
- Android code remains readable, idiomatic Java and uses Android logging.
- Add comments only when they explain a non-obvious reason, not when they restate
  code.
- Initial clipboard scope is text only. Do not add images, files, screenshots,
  rich text, passwords, or arbitrary binary data.
- Never hardcode real secrets, passwords, tokens, or OAuth credentials. Use
  environment variables when configuration becomes necessary, add `.env.example`,
  and keep `.env` ignored.
- Make no large, silent architectural decisions. For a material ambiguity,
  explain it, recommend the simplest option, and wait for approval. Use normal
  judgment for small implementation details.

## Event, Identity, and Security Direction

- Early development uses simple device IDs/tokens, such as `desktop-001` and
  `android-001`; Google OAuth and device pairing are later work.
- Every eventual sync event must carry a unique `event_id` and source device
  identity. Clients must distinguish user-created clipboard changes from
  sync-created changes to prevent feedback loops.
- Event messages must be structured and documented in `docs/protocol.md`.
- The eventual production direction is HTTPS/WSS, authenticated users, and
  device authorization. Do not intentionally introduce insecure architecture,
  even for the POC.
- Reconnection must eventually use reasonable backoff, not aggressive retry
  loops.

## Testing and Documentation Workflow

For each completed phase:

1. Run relevant automated checks and practical manual test instructions.
2. Fix discovered errors within the requested scope.
3. Update `README.md`, `docs/architecture.md`, `docs/protocol.md`,
   `docs/development.md`, and `docs/progress.md` as applicable.
4. Report what changed, why, how to run and test it, known limitations, and the
   next recommended step.

Backend work should use Django/API/WebSocket tests where practical. Desktop and
Android work should include practical unit tests where feasible plus clear
manual testing steps. Keep commits small and logically scoped; do not mix
unrelated work.
