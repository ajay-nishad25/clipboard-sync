"""WebSocket consumer for user-isolated clipboard synchronization."""

from __future__ import annotations

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from clipboard.models import ClipboardEntry
from clipboard.services import resolve_device_and_user, set_user_clipboard

logger = logging.getLogger(__name__)


class ClipboardConsumer(AsyncWebsocketConsumer):
    """Handle WebSocket connections for clipboard synchronization with user data isolation.

    Supported message types:
    - test.message — Connectivity test, echoes back test.ack.
    - clipboard.update — Store text clipboard content in user's ClipboardState,
      return clipboard.ack, and broadcast clipboard.remote_update ONLY to devices
      belonging to the SAME user (user-scoped group: clipboard_user_<user_id>).
    """

    async def connect(self) -> None:
        self.device_id = self._get_device_id()
        self.device, self.user = None, None
        self.group_name = None

        if self.device_id:
            self.device, self.user = await database_sync_to_async(resolve_device_and_user)(self.device_id)

        if self.user:
            self.group_name = f"clipboard_user_{self.user.id}"
            await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()
        logger.info(
            "WebSocket connection accepted for device %s (User %s).",
            self.device_id or "unknown",
            self.user.username if self.user else "none",
        )

    async def disconnect(self, close_code: int) -> None:
        if self.group_name:
            await self.channel_layer.group_discard(self.group_name, self.channel_name)
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
        if message_type == "test.message":
            await self._handle_test_message(message)
        elif message_type == "clipboard.update":
            await self._handle_clipboard_update(message)
        else:
            logger.warning("Unsupported WebSocket message type from device %s.", self.device_id or "unknown")
            await self._send_error(
                "unsupported_type",
                "Supported message types: test.message, clipboard.update.",
            )

    async def _handle_test_message(self, message: dict) -> None:
        text = message.get("message")
        if not isinstance(text, str) or not text:
            await self._send_error("invalid_message", "test.message requires a non-empty text message.")
            return

        logger.info("WebSocket test message received from device %s.", self.device_id or "unknown")
        await self.send(text_data=json.dumps({"type": "test.ack", "message": text}))

    async def _handle_clipboard_update(self, message: dict) -> None:
        device_id = message.get("device_id")
        if not isinstance(device_id, str) or not device_id.strip():
            await self._send_error(
                "invalid_message",
                "clipboard.update requires a non-empty device_id string.",
            )
            return

        content = message.get("content")
        if not isinstance(content, str) or not content:
            await self._send_error(
                "invalid_content",
                "Clipboard content must be a non-empty string.",
            )
            return

        device, user = await database_sync_to_async(resolve_device_and_user)(device_id)
        if not user:
            await self._send_error("invalid_device", "Device ID is not associated with a user.")
            return

        # Ensure consumer is joined to the user's channel group
        user_group = f"clipboard_user_{user.id}"
        if self.group_name != user_group:
            if self.group_name:
                await self.channel_layer.group_discard(self.group_name, self.channel_name)
            self.group_name = user_group
            await self.channel_layer.group_add(self.group_name, self.channel_name)

        # Replace active ClipboardState for user (10-minute expiration)
        await database_sync_to_async(set_user_clipboard)(user, content)

        # Store legacy ClipboardEntry log
        await database_sync_to_async(ClipboardEntry.objects.create)(
            device_id=device_id,
            content=content,
        )

        logger.info("ClipboardState updated for user %s via device %s.", user.username, device_id)

        # Send ACK to sender
        await self.send(
            text_data=json.dumps(
                {"type": "clipboard.ack", "device_id": device_id, "status": "stored"}
            )
        )

        # Broadcast remote_update ONLY to user's isolated channel group
        await self.channel_layer.group_send(
            user_group,
            {
                "type": "clipboard_broadcast",
                "sender_device_id": device_id,
                "content": content,
            },
        )

    async def clipboard_broadcast(self, event: dict) -> None:
        """Broadcast a remote clipboard update to connected devices belonging to the same user."""
        sender_device_id = event.get("sender_device_id")
        if sender_device_id != self.device_id:
            content = event.get("content", "")
            await self.send(
                text_data=json.dumps(
                    {
                        "type": "clipboard.remote_update",
                        "device_id": sender_device_id,
                        "content": content,
                    }
                )
            )
            logger.info(
                "Broadcasted remote clipboard update from device %s to device %s.",
                sender_device_id,
                self.device_id or "unknown",
            )

    def _get_device_id(self) -> str | None:
        query = parse_qs(self.scope["query_string"].decode("utf-8"))
        values = query.get("device_id")
        return values[0] if values else None

    async def _send_error(self, code: str, detail: str) -> None:
        logger.warning("Invalid WebSocket message from device %s: %s.", self.device_id or "unknown", code)
        await self.send(text_data=json.dumps({"type": "error", "code": code, "detail": detail}))
