"""Automated tests for the clipboard WebSocket infrastructure."""

from __future__ import annotations

from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.test import SimpleTestCase, TestCase

from clipboard.models import ClipboardEntry
from config.asgi import application


class ClipboardWebSocketTests(SimpleTestCase):
    """Tests that do not touch the database (Phase 4 infrastructure)."""

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
    async def test_unsupported_message_type_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to({"type": "unknown.type", "data": "irrelevant"})
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


class ClipboardUpdateWebSocketTests(TestCase):
    """Tests for clipboard.update messages that create database records."""

    @async_to_sync
    async def test_clipboard_update_stores_entry_and_returns_ack(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-001")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-001", "content": "Hello from Windows"}
        )
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "clipboard.ack")
        self.assertEqual(response["device_id"], "desktop-001")
        self.assertEqual(response["status"], "stored")

        entry = await database_sync_to_async(ClipboardEntry.objects.first)()
        self.assertIsNotNone(entry)
        self.assertEqual(entry.content, "Hello from Windows")
        self.assertEqual(entry.device_id, "desktop-001")

        await communicator.disconnect()

    @async_to_sync
    async def test_clipboard_update_missing_device_id_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to({"type": "clipboard.update", "content": "Hello"})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_message")
        count = await database_sync_to_async(ClipboardEntry.objects.count)()
        self.assertEqual(count, 0)
        await communicator.disconnect()

    @async_to_sync
    async def test_clipboard_update_non_string_device_id_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "clipboard.update", "device_id": 42, "content": "Hello"}
        )
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_message")
        await communicator.disconnect()

    @async_to_sync
    async def test_clipboard_update_empty_content_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-001", "content": ""}
        )
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_content")
        count = await database_sync_to_async(ClipboardEntry.objects.count)()
        self.assertEqual(count, 0)
        await communicator.disconnect()

    @async_to_sync
    async def test_clipboard_update_non_string_content_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-001", "content": 123}
        )
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_content")
        await communicator.disconnect()
