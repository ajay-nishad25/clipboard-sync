"""WebSocket consumer for user-isolated authenticated clipboard synchronization."""

from __future__ import annotations

import json
import logging
from urllib.parse import parse_qs

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from clipboard.models import ClipboardEntry
from clipboard.services import authenticate_device_token, set_user_clipboard

logger = logging.getLogger(__name__)


class ClipboardConsumer(AsyncWebsocketConsumer):
    """Handle WebSocket connections for authenticated clipboard synchronization with user data isolation.

    Supported message types:
    - test.message — Connectivity test, echoes back test.ack.
    - clipboard.update — Store text clipboard content in user's ClipboardState,
      return clipboard.ack, and broadcast clipboard.remote_update ONLY to devices
      belonging to the SAME user (user-scoped group: clipboard_user_<user_id>).
    """

    async def connect(self) -> None:
        self.raw_token = self._get_token()
        self.cred, self.device, self.user = None, None, None
        self.group_name = None
        self.device_id = None

        if self.raw_token:
            self.cred, self.device, self.user = await database_sync_to_async(authenticate_device_token)(self.raw_token)

        if not self.cred or not self.device or not self.user:
            logger.warning("Rejecting unauthenticated WebSocket connection.")
            await self.close(code=4001)
            return

        self.device_id = self.device.device_id
        self.group_name = f"clipboard_user_{self.user.id}"
        await self.channel_layer.group_add(self.group_name, self.channel_name)

        await self.accept()
        logger.info(
            "WebSocket connection accepted for authenticated device %s (User %s).",
            self.device_id,
            self.user.username,
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
        content = message.get("content")
        if not isinstance(content, str) or not content:
            await self._send_error(
                "invalid_content",
                "Clipboard content must be a non-empty string.",
            )
            return

        if not self.user or not self.device:
            await self._send_error("unauthorized", "Unauthenticated WebSocket connection.")
            return

        device_id = self.device.device_id

        # Replace active ClipboardState for user (10-minute expiration)
        await database_sync_to_async(set_user_clipboard)(self.user, content)

        # Store legacy ClipboardEntry log
        await database_sync_to_async(ClipboardEntry.objects.create)(
            device_id=device_id,
            content=content,
        )

        logger.info("ClipboardState updated for user %s via device %s.", self.user.username, device_id)

        # Send ACK to sender
        await self.send(
            text_data=json.dumps(
                {"type": "clipboard.ack", "device_id": device_id, "status": "stored"}
            )
        )

        # Broadcast remote_update ONLY to user's isolated channel group
        await self.channel_layer.group_send(
            self.group_name,
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

    def _get_token(self) -> str | None:
        query = parse_qs(self.scope["query_string"].decode("utf-8"))
        tokens = query.get("token")
        if tokens and tokens[0].strip():
            return tokens[0].strip()

        # Development fallback query param
        device_ids = query.get("device_id")
        if device_ids and device_ids[0].strip():
            return device_ids[0].strip()

        return None

    async def _send_error(self, code: str, detail: str) -> None:
        logger.warning("Invalid WebSocket message from device %s: %s.", self.device_id or "unknown", code)
        await self.send(text_data=json.dumps({"type": "error", "code": code, "detail": detail}))
