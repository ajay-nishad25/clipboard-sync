"""WebSocket consumer for the clipboard application."""

from __future__ import annotations

import json
import logging
from urllib.parse import parse_qs

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class ClipboardConsumer(AsyncWebsocketConsumer):
    """Accept test messages without performing clipboard synchronization."""

    async def connect(self) -> None:
        self.device_id = self._get_device_id()
        await self.accept()
        logger.info("WebSocket connection accepted for device %s.", self.device_id or "unknown")

    async def disconnect(self, close_code: int) -> None:
        logger.info(
            "WebSocket disconnected for device %s with code %s.",
            getattr(self, "device_id", None) or "unknown",
            close_code,
        )

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        if bytes_data is not None or text_data is None:
            await self._send_error("invalid_json", "WebSocket messages must contain JSON text.")
            return

        try:
            message = json.loads(text_data)
        except json.JSONDecodeError:
            logger.warning("Invalid JSON received from device %s.", self.device_id or "unknown")
            await self._send_error("invalid_json", "Message must be valid JSON.")
            return

        if not isinstance(message, dict):
            await self._send_error("invalid_message", "Message must be a JSON object.")
            return

        message_type = message.get("type")
        if message_type != "test.message":
            logger.warning("Unsupported WebSocket message type from device %s.", self.device_id or "unknown")
            await self._send_error("unsupported_type", "Only test.message is supported in Phase 4.")
            return

        text = message.get("message")
        if not isinstance(text, str) or not text:
            await self._send_error("invalid_message", "test.message requires a non-empty text message.")
            return

        logger.info("WebSocket test message received from device %s.", self.device_id or "unknown")
        await self.send(
            text_data=json.dumps({"type": "test.ack", "message": text}),
        )
        logger.info("WebSocket acknowledgement sent to device %s.", self.device_id or "unknown")

    def _get_device_id(self) -> str | None:
        query = parse_qs(self.scope["query_string"].decode("utf-8"))
        values = query.get("device_id")
        return values[0] if values else None

    async def _send_error(self, code: str, detail: str) -> None:
        logger.warning("Invalid WebSocket message from device %s: %s.", self.device_id or "unknown", code)
        await self.send(text_data=json.dumps({"type": "error", "code": code, "detail": detail}))
