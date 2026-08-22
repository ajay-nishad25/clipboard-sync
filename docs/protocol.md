# Protocol Notes

## Current HTTP API

Phase 2 provides development/testing endpoints only:

- `POST /api/clipboard/` creates a plain-text clipboard entry.
- `GET /api/clipboard/latest/` returns the most recently created entry, or
  `404 Not Found` when none exists.

The API has no authentication, client integration, or WebSocket support yet.

## Create request and response

```json
{
  "device_id": "desktop-001",
  "content": "Hello World"
}
```

Both fields are required. `content` must be a non-empty JSON string. A
successful request returns `201 Created` and includes the server-generated `id`
and `created_at` fields.

## Planned event shape

Later WebSocket clipboard events will use a structured JSON message, rather
than arbitrary payloads. A representative later-phase message is:

```json
{
  "type": "clipboard.update",
  "event_id": "unique-event-id",
  "source_device": "desktop-001",
  "content": "Hello World"
}
```

## Rules

- `content` is plain text only.
- `event_id` is unique for every clipboard event.
- `source_device` identifies the device that originated the user action.
- Receivers use the event and source identity to prevent event loops and ignore
  duplicates.
- Endpoint paths, acknowledgement behavior, validation rules, and
  authentication details will be documented when their corresponding phases are
  implemented and tested.
