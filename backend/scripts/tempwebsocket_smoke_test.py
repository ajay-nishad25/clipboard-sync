"""Temporary-development-style client for manually checking the Phase 4 endpoint."""

from __future__ import annotations

import asyncio
import json
import os

from websockets.asyncio.client import connect

URL = os.getenv(
    "WEBSOCKET_SMOKE_URL",
    "ws://127.0.0.1:8000/ws/clipboard/?device_id=desktop-001",
)
MESSAGE = {"type": "test.message", "message": "Hello WebSocket"}


async def main() -> None:
    """Connect, exchange a Phase 4 test message, and close the connection."""
    async with connect(URL) as websocket:
        await websocket.send(json.dumps(MESSAGE))
        response = json.loads(await websocket.recv())

    expected = {"type": "test.ack", "message": MESSAGE["message"]}
    if response != expected:
        raise RuntimeError(f"Unexpected response: {response}")

    print("WebSocket smoke test passed.")
    print(json.dumps(response))


if __name__ == "__main__":
    asyncio.run(main())
