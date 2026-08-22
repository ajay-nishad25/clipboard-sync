# Protocol Notes

## HTTP API (Phases 2–3, unchanged)

Phase 2 provides development/testing endpoints only:

- `POST /api/clipboard/` creates a plain-text clipboard entry.
- `GET /api/clipboard/latest/` returns the most recently created entry, or
  `404 Not Found` when none exists.

The API has no authentication or client integration.

### Create request and response

```json
{
  "device_id": "desktop-001",
  "content": "Hello World"
}
```

Both fields are required. `content` must be a non-empty JSON string. A
successful request returns `201 Created` and includes the server-generated `id`
and `created_at` fields.

## WebSocket endpoint (Phase 4)

```text
ws://127.0.0.1:8000/ws/clipboard/
ws://127.0.0.1:8000/ws/clipboard/?device_id=<id>
```

The `device_id` query parameter is optional and used for server-side logging
only. No authentication or authorization is enforced in Phase 4.

### Phase 4 test message

Clients may send exactly one message type in Phase 4:

```json
{"type": "test.message", "message": "<non-empty string>"}
```

The server responds with an acknowledgement echoing the message text:

```json
{"type": "test.ack", "message": "<echoed string>"}
```

### Error responses

The server returns a structured error for invalid input without closing the
connection:

```json
{"type": "error", "code": "<code>", "detail": "<human-readable detail>"}
```

| Situation | `code` |
|-----------|--------|
| Non-JSON text received | `invalid_json` |
| JSON value is not an object | `invalid_message` |
| `type` field is not `test.message` | `unsupported_type` |
| `message` field missing or not a non-empty string | `invalid_message` |

### Phase 4 limitations

- Only `test.message` / `test.ack` is supported. `clipboard.update` and all
  other types return `unsupported_type`.
- No clipboard data is read, stored, or broadcast over WebSocket.
- The channel layer is `InMemoryChannelLayer`; it is not shared across
  processes and resets on server restart.
- No authentication, device pairing, or reconnection logic exists yet.

## Planned event shape (Phase 5+)

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
