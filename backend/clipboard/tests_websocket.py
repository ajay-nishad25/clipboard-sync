"""Automated tests for user-isolated clipboard WebSocket infrastructure."""

from __future__ import annotations

from datetime import timedelta
from asgiref.sync import async_to_sync
from channels.db import database_sync_to_async
from channels.testing import WebsocketCommunicator
from django.contrib.auth.models import User
from django.test import TestCase
from django.utils import timezone

from clipboard.models import ClipboardEntry, ClipboardState, Device, DeviceType
from clipboard.services import get_active_user_clipboard
from config.asgi import application


class ClipboardWebSocketInfrastructureTests(TestCase):
    """Tests for connectivity, formatting, and basic error handling."""

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


class ClipboardUpdateWebSocketIsolationTests(TestCase):
    """Tests for clipboard.update with multi-user isolation and device ownership."""

    def setUp(self) -> None:
        # Create User A with Desktop A and Android A
        self.user_a = User.objects.create_user("ws_user_a")
        self.device_a_desktop = Device.objects.create(
            user=self.user_a, device_id="desktop-A", device_type=DeviceType.DESKTOP
        )
        self.device_a_android = Device.objects.create(
            user=self.user_a, device_id="android-A", device_type=DeviceType.ANDROID
        )

        # Create User B with Desktop B and Android B
        self.user_b = User.objects.create_user("ws_user_b")
        self.device_b_desktop = Device.objects.create(
            user=self.user_b, device_id="desktop-B", device_type=DeviceType.DESKTOP
        )
        self.device_b_android = Device.objects.create(
            user=self.user_b, device_id="android-B", device_type=DeviceType.ANDROID
        )

    @async_to_sync
    async def test_clipboard_update_stores_entry_and_state_returns_ack(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-A")
        connected, _ = await communicator.connect()
        self.assertTrue(connected)

        await communicator.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-A", "content": "Hello from Desktop A"}
        )
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "clipboard.ack")
        self.assertEqual(response["device_id"], "desktop-A")
        self.assertEqual(response["status"], "stored")

        state = await database_sync_to_async(get_active_user_clipboard)(self.user_a)
        self.assertIsNotNone(state)
        self.assertEqual(state.content, "Hello from Desktop A")

        await communicator.disconnect()

    @async_to_sync
    async def test_user_a_android_update_reaches_user_a_desktop(self) -> None:
        android_a = WebsocketCommunicator(application, "/ws/clipboard/?device_id=android-A")
        desktop_a = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-A")

        self.assertTrue((await android_a.connect())[0])
        self.assertTrue((await desktop_a.connect())[0])

        await android_a.send_json_to(
            {"type": "clipboard.update", "device_id": "android-A", "content": "Sync to Desktop A"}
        )

        ack = await android_a.receive_json_from()
        self.assertEqual(ack["type"], "clipboard.ack")

        broadcast = await desktop_a.receive_json_from()
        self.assertEqual(broadcast["type"], "clipboard.remote_update")
        self.assertEqual(broadcast["device_id"], "android-A")
        self.assertEqual(broadcast["content"], "Sync to Desktop A")

        await android_a.disconnect()
        await desktop_a.disconnect()

    @async_to_sync
    async def test_user_a_update_does_not_reach_user_b_desktop(self) -> None:
        desktop_a = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-A")
        desktop_b = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-B")

        self.assertTrue((await desktop_a.connect())[0])
        self.assertTrue((await desktop_b.connect())[0])

        await desktop_a.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-A", "content": "User A Secret"}
        )

        ack = await desktop_a.receive_json_from()
        self.assertEqual(ack["type"], "clipboard.ack")

        # Desktop B MUST NOT receive User A's update
        nothing = await desktop_b.receive_nothing()
        self.assertTrue(nothing)

        await desktop_a.disconnect()
        await desktop_b.disconnect()

    @async_to_sync
    async def test_sender_receives_ack_and_does_not_receive_remote_update(self) -> None:
        desktop_a = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-A")
        self.assertTrue((await desktop_a.connect())[0])

        await desktop_a.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-A", "content": "Self content"}
        )

        ack = await desktop_a.receive_json_from()
        self.assertEqual(ack["type"], "clipboard.ack")

        nothing = await desktop_a.receive_nothing()
        self.assertTrue(nothing)

        await desktop_a.disconnect()

    @async_to_sync
    async def test_unknown_or_blank_device_id_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/")
        await communicator.connect()

        await communicator.send_json_to({"type": "clipboard.update", "content": "Hello"})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_message")
        await communicator.disconnect()

    @async_to_sync
    async def test_clipboard_update_empty_content_returns_error(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-A")
        await communicator.connect()

        await communicator.send_json_to({"type": "clipboard.update", "device_id": "desktop-A", "content": ""})
        response = await communicator.receive_json_from()

        self.assertEqual(response["type"], "error")
        self.assertEqual(response["code"], "invalid_content")
        await communicator.disconnect()

    @async_to_sync
    async def test_expired_clipboard_not_returned_after_expiration(self) -> None:
        communicator = WebsocketCommunicator(application, "/ws/clipboard/?device_id=desktop-A")
        await communicator.connect()

        await communicator.send_json_to(
            {"type": "clipboard.update", "device_id": "desktop-A", "content": "Temporary Text"}
        )
        await communicator.receive_json_from()

        state = await database_sync_to_async(ClipboardState.objects.get)(user=self.user_a)
        state.expires_at = timezone.now() - timedelta(seconds=1)
        await database_sync_to_async(state.save)()

        active = await database_sync_to_async(get_active_user_clipboard)(self.user_a)
        self.assertIsNone(active)

        await communicator.disconnect()
