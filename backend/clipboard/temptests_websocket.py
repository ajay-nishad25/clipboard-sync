"""Automated tests for the clipboard WebSocket infrastructure."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase

from config.asgi import application


class ClipboardWebSocketTests(SimpleTestCase):
    @async_to_sync
    async def test_connection_succeeds_and_disconnects_cleanly(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-001")

        connected, _ = await communicator.connect()

        self.assertTrue(connected)
        await communicator.disconnect()

    @async_to_sync
    async def test_valid_test_message_receives_acknowledgement(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to({"type": "test.message", "message": "Hello WebSocket"})
        response = await communicator.receive_json_from()

        self.assertEqual(response, {"type": "test.ack", "message": "Hello WebSocket"})
        await communicator.disconnect()

    @async_to_sync
    async def test_malformed_json_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_to(text_data="not-json")
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_json")
        await communicator.disconnect()

    @async_to_sync
    async def test_invalid_message_type_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to({"type": "clipboard.update", "content": "Not yet supported"})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "unsupported_type")
        await communicator.disconnect()

    @async_to_sync
    async def test_missing_message_field_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to({"type": "test.message"})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_message")
        await communicator.disconnect()
