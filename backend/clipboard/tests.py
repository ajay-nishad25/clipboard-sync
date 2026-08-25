from datetime import timedelta
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from clipboard.models import ClipboardEntry, ClipboardState, Device, DeviceType
from clipboard.services import (
    get_active_user_clipboard,
    resolve_device_and_user,
    set_user_clipboard,
)


class DeviceModelTests(TestCase):
    def test_device_belongs_to_user(self) -> None:
        user = User.objects.create_user("user_device_test")
        device = Device.objects.create(user=user, device_id="desktop-001", device_type=DeviceType.DESKTOP)
        self.assertEqual(device.user, user)
        self.assertEqual(device.device_id, "desktop-001")
        self.assertEqual(device.device_type, "desktop")

    def test_device_id_must_be_unique(self) -> None:
        user1 = User.objects.create_user("user1")
        user2 = User.objects.create_user("user2")
        Device.objects.create(user=user1, device_id="shared-device-id")
        with self.assertRaises(IntegrityError):
            Device.objects.create(user=user2, device_id="shared-device-id")

    def test_desktop_and_android_device_relationships(self) -> None:
        user = User.objects.create_user("multi_device_user")
        desktop = Device.objects.create(user=user, device_id="desktop-100", device_type=DeviceType.DESKTOP)
        android = Device.objects.create(user=user, device_id="android-100", device_type=DeviceType.ANDROID)

        devices = user.devices.all()
        self.assertEqual(len(devices), 2)
        self.assertIn(desktop, devices)
        self.assertIn(android, devices)

    def test_duplicate_device_registration_rejected(self) -> None:
        user = User.objects.create_user("dup_user")
        Device.objects.create(user=user, device_id="device-xyz")
        with self.assertRaises(IntegrityError):
            Device.objects.create(user=user, device_id="device-xyz")


class ClipboardStateTests(TestCase):
    def setUp(self) -> None:
        self.user_a = User.objects.create_user("user_a")
        self.user_b = User.objects.create_user("user_b")

    def test_one_clipboard_state_per_user(self) -> None:
        state_a = set_user_clipboard(self.user_a, "Hello User A")
        self.assertEqual(ClipboardState.objects.filter(user=self.user_a).count(), 1)
        self.assertEqual(state_a.user, self.user_a)

        with self.assertRaises(IntegrityError):
            ClipboardState.objects.create(
                user=self.user_a,
                content="Second State",
                expires_at=timezone.now() + timedelta(minutes=10),
            )

    def test_new_clipboard_replaces_existing_clipboard(self) -> None:
        set_user_clipboard(self.user_a, "First Text")
        self.assertEqual(ClipboardState.objects.count(), 1)

        set_user_clipboard(self.user_a, "Second Text")
        self.assertEqual(ClipboardState.objects.count(), 1)

        state = get_active_user_clipboard(self.user_a)
        self.assertIsNotNone(state)
        self.assertEqual(state.content, "Second Text")

    def test_updated_at_changes_on_replacement(self) -> None:
        state1 = set_user_clipboard(self.user_a, "Text 1")
        initial_updated_at = state1.updated_at

        state2 = set_user_clipboard(self.user_a, "Text 2")
        self.assertGreaterEqual(state2.updated_at, initial_updated_at)

    def test_expires_at_set_to_10_minutes_future(self) -> None:
        before = timezone.now()
        state = set_user_clipboard(self.user_a, "Expiring Text", ttl_minutes=10)
        after = timezone.now()

        expected_min = before + timedelta(minutes=10)
        expected_max = after + timedelta(minutes=10)
        self.assertTrue(expected_min <= state.expires_at <= expected_max)

    def test_expired_clipboard_is_unavailable_and_deleted(self) -> None:
        state = set_user_clipboard(self.user_a, "Old Text", ttl_minutes=10)
        state.expires_at = timezone.now() - timedelta(seconds=1)
        state.save()

        active_state = get_active_user_clipboard(self.user_a)
        self.assertIsNone(active_state)
        self.assertEqual(ClipboardState.objects.filter(user=self.user_a).count(), 0)

    def test_user_a_cannot_access_user_b_clipboard_state(self) -> None:
        set_user_clipboard(self.user_a, "User A Secret")
        set_user_clipboard(self.user_b, "User B Secret")

        state_a = get_active_user_clipboard(self.user_a)
        state_b = get_active_user_clipboard(self.user_b)

        self.assertEqual(state_a.content, "User A Secret")
        self.assertEqual(state_b.content, "User B Secret")
        self.assertNotEqual(state_a.content, state_b.content)


class ClipboardApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user_a = User.objects.create_user("api_user_a")
        self.device_a = Device.objects.create(user=self.user_a, device_id="desktop-A", device_type=DeviceType.DESKTOP)

        self.user_b = User.objects.create_user("api_user_b")
        self.device_b = Device.objects.create(user=self.user_b, device_id="desktop-B", device_type=DeviceType.DESKTOP)

    def test_post_creates_clipboard_entry_and_state(self) -> None:
        response = self.client.post(
            "/api/clipboard/",
            {"device_id": "desktop-A", "content": "Hello World"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["device_id"], "desktop-A")
        self.assertEqual(response.data["content"], "Hello World")
        self.assertEqual(ClipboardEntry.objects.count(), 1)

        state = get_active_user_clipboard(self.user_a)
        self.assertIsNotNone(state)
        self.assertEqual(state.content, "Hello World")

    def test_post_rejects_missing_or_non_text_fields(self) -> None:
        missing_device = self.client.post("/api/clipboard/", {"content": "Hello World"}, format="json")
        non_text_content = self.client.post(
            "/api/clipboard/",
            {"device_id": "desktop-A", "content": 123},
            format="json",
        )
        self.assertEqual(missing_device.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(non_text_content.status_code, status.HTTP_400_BAD_REQUEST)

    def test_user_scoped_latest_returns_correct_user_value(self) -> None:
        set_user_clipboard(self.user_a, "User A Content")
        set_user_clipboard(self.user_b, "User B Content")

        response_a = self.client.get("/api/clipboard/latest/?device_id=desktop-A")
        self.assertEqual(response_a.status_code, status.HTTP_200_OK)
        self.assertEqual(response_a.data["content"], "User A Content")

        response_b = self.client.get("/api/clipboard/latest/?device_id=desktop-B")
        self.assertEqual(response_b.status_code, status.HTTP_200_OK)
        self.assertEqual(response_b.data["content"], "User B Content")

    def test_user_a_cannot_retrieve_user_b_clipboard(self) -> None:
        set_user_clipboard(self.user_b, "User B Secret")

        response_a = self.client.get("/api/clipboard/latest/?device_id=desktop-A")
        self.assertEqual(response_a.status_code, status.HTTP_404_NOT_FOUND)

    def test_expired_clipboard_returns_not_found(self) -> None:
        state = set_user_clipboard(self.user_a, "Expired Text", ttl_minutes=10)
        state.expires_at = timezone.now() - timedelta(seconds=1)
        state.save()

        response = self.client.get("/api/clipboard/latest/?device_id=desktop-A")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
