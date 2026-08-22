# Protocol Notes

## HTTP API (Phases 2–3, unchanged)

- `POST /api/clipboard/` — create a clipboard entry.
- `GET /api/clipboard/latest/` — return the most recently created entry.

### Create request

```json
{"device_id": "desktop-001", "content": "Hello World"}
```

Both fields required. `content` must be a non-empty JSON string. Returns
`201 Created` with `id` and `created_at`.

---

## WebSocket endpoint (Phases 4–5)

```text
ws://127.0.0.1:8000/ws/clipboard/
ws://127.0.0.1:8000/ws/clipboard/?device_id=<id>
```

`device_id` in the query string is used for connection-level logging only.
Each `clipboard.update` message carries its own `device_id`.

### `test.message` (Phase 4 — connectivity test)

Send:

```json
{"type": "test.message", "message": "Hello WebSocket"}
```

Receive:

```json
{"type": "test.ack", "message": "Hello WebSocket"}
```

### `clipboard.update` (Phase 5 — clipboard sync)

Send:

```json
{
  "type": "clipboard.update",
  "device_id": "desktop-001",
  "content": "Hello from Windows"
}
```

Both `device_id` and `content` are required non-empty strings.

Receive on success:

```json
{
  "type": "clipboard.ack",
  "device_id": "desktop-001",
  "status": "stored"
}
```

### Error responses

The server returns a structured error and **keeps the connection open**:

```json
{"type": "error", "code": "<code>", "detail": "<human-readable detail>"}
```

| Situation | `code` |
|-----------|--------|
| Non-JSON text received | `invalid_json` |
| JSON value is not an object | `invalid_message` |
| `type` is not a supported value | `unsupported_type` |
| Missing/non-string `message` (test.message) | `invalid_message` |
| Missing/non-string/blank `device_id` (clipboard.update) | `invalid_message` |
| Empty or non-string `content` | `invalid_content` |

### Phase 5 limitations

- No broadcasting: `clipboard.update` is stored but not forwarded to other
  connected clients.
- `InMemoryChannelLayer` — not shared across processes, resets on restart.
- No authentication or device authorization.
- No reconnection logic on the server side.
- The desktop agent does not queue or retry values missed during an outage.

---

## Planned event shape (Phase 6+)

Later phases will add `event_id` and `source_device` fields for idempotency
and event-loop prevention:

```json
{
  "type": "clipboard.update",
  "event_id": "unique-event-id",
  "source_device": "desktop-001",
  "content": "Hello World"
}
```

Rules:

- `content` is plain text only.
- `event_id` is unique for every clipboard event.
- `source_device` identifies the originating device.
- Receivers use event and source identity to prevent loops and ignore duplicates.
