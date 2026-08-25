from datetime import timedelta
from django.contrib.auth.models import User
from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from clipboard.models import ClipboardEntry, ClipboardState, Device, DeviceCredential, DeviceType, PairingCode
from clipboard.services import (
    authenticate_device_token,
    create_pairing_code,
    get_active_user_clipboard,
    issue_device_credential,
    pair_android_device,
    resolve_device_and_user,
    revoke_device_credential,
    set_user_clipboard,
)


class DeviceCredentialTests(TestCase):
    def setUp(self) -> None:
        self.user_a = User.objects.create_user("cred_user_a")
        self.device_a = Device.objects.create(
            user=self.user_a, device_id="desktop-cred-A", device_type=DeviceType.DESKTOP
        )

    def test_credential_generated_securely(self) -> None:
        cred, raw_token = issue_device_credential(self.device_a)
        self.assertTrue(raw_token.startswith("devtok_"))
        self.assertGreaterEqual(len(raw_token), 30)

    def test_raw_credential_not_stored_in_database(self) -> None:
        cred, raw_token = issue_device_credential(self.device_a)
        db_cred = DeviceCredential.objects.get(id=cred.id)
        self.assertNotEqual(db_cred.token_hash, raw_token)
        self.assertEqual(db_cred.token_hash, DeviceCredential.hash_token(raw_token))

    def test_credential_hash_can_authenticate(self) -> None:
        cred, raw_token = issue_device_credential(self.device_a)
        auth_cred, auth_device, auth_user = authenticate_device_token(raw_token)
        self.assertEqual(auth_cred, cred)
        self.assertEqual(auth_device, self.device_a)
        self.assertEqual(auth_user, self.user_a)

    def test_revoked_credential_cannot_authenticate(self) -> None:
        cred, raw_token = issue_device_credential(self.device_a)
        revoke_device_credential(cred)

        auth_cred, auth_device, auth_user = authenticate_device_token(raw_token)
        self.assertIsNone(auth_cred)
        self.assertIsNone(auth_device)
        self.assertIsNone(auth_user)

    def test_invalid_credential_rejected(self) -> None:
        auth_cred, auth_device, auth_user = authenticate_device_token("devtok_invalid123")
        self.assertIsNone(auth_cred)
        self.assertIsNone(auth_device)
        self.assertIsNone(auth_user)


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


class ClipboardStateTests(TestCase):
    def setUp(self) -> None:
        self.user_a = User.objects.create_user("user_a")
        self.user_b = User.objects.create_user("user_b")

    def test_one_clipboard_state_per_user(self) -> None:
        state_a = set_user_clipboard(self.user_a, "Hello User A")
        self.assertEqual(ClipboardState.objects.filter(user=self.user_a).count(), 1)
        self.assertEqual(state_a.user, self.user_a)

    def test_new_clipboard_replaces_existing_clipboard(self) -> None:
        set_user_clipboard(self.user_a, "First Text")
        self.assertEqual(ClipboardState.objects.count(), 1)

        set_user_clipboard(self.user_a, "Second Text")
        self.assertEqual(ClipboardState.objects.count(), 1)

        state = get_active_user_clipboard(self.user_a)
        self.assertIsNotNone(state)
        self.assertEqual(state.content, "Second Text")

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


class PairingCodeTests(TestCase):
    def setUp(self) -> None:
        self.user_a = User.objects.create_user("pair_user_a")
        self.desktop_a = Device.objects.create(
            user=self.user_a, device_id="desktop-A", device_type=DeviceType.DESKTOP
        )
        self.user_b = User.objects.create_user("pair_user_b")
        self.desktop_b = Device.objects.create(
            user=self.user_b, device_id="desktop-B", device_type=DeviceType.DESKTOP
        )

    def test_pairing_code_generated(self) -> None:
        pairing_code = create_pairing_code(self.desktop_a)
        self.assertIsNotNone(pairing_code)
        self.assertEqual(pairing_code.desktop_device, self.desktop_a)

    def test_android_successfully_pairs_and_receives_credential(self) -> None:
        pairing_code = create_pairing_code(self.desktop_a)
        android_device, raw_token, error = pair_android_device(pairing_code.code, "android-A")
        self.assertIsNotNone(android_device)
        self.assertIsNotNone(raw_token)
        self.assertTrue(raw_token.startswith("devtok_"))
        self.assertIsNone(error)
        self.assertEqual(android_device.user, self.user_a)


class AuthenticatedRestApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()
        self.user_a = User.objects.create_user("rest_user_a")
        self.device_a = Device.objects.create(user=self.user_a, device_id="desktop-rest-A")
        self.cred_a, self.token_a = issue_device_credential(self.device_a)

        self.user_b = User.objects.create_user("rest_user_b")
        self.device_b = Device.objects.create(user=self.user_b, device_id="desktop-rest-B")
        self.cred_b, self.token_b = issue_device_credential(self.device_b)

    def test_missing_credential_rejected(self) -> None:
        response = self.client.get("/api/clipboard/latest/")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_invalid_credential_rejected(self) -> None:
        response = self.client.get("/api/clipboard/latest/", HTTP_AUTHORIZATION="Bearer devtok_invalid")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_revoked_credential_rejected(self) -> None:
        revoke_device_credential(self.cred_a)
        response = self.client.get("/api/clipboard/latest/", HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_valid_bearer_token_accepted(self) -> None:
        set_user_clipboard(self.user_a, "User A Auth Content")
        response = self.client.get("/api/clipboard/latest/", HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "User A Auth Content")

    def test_user_a_token_cannot_access_user_b_clipboard(self) -> None:
        set_user_clipboard(self.user_b, "User B Secret")
        response = self.client.get("/api/clipboard/latest/", HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_device_id_spoofing_does_not_bypass_auth(self) -> None:
        set_user_clipboard(self.user_a, "User A Real Data")
        set_user_clipboard(self.user_b, "User B Real Data")
        response = self.client.get(
            f"/api/clipboard/latest/?device_id=desktop-rest-B",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["content"], "User A Real Data")

    def test_pairing_response_contains_credential(self) -> None:
        pairing_code = create_pairing_code(self.device_a)
        response = self.client.post(
            "/api/device/pair/",
            {"code": pairing_code.code, "android_device_id": "android-new-pair"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("credential", response.data)
        self.assertTrue(response.data["credential"].startswith("devtok_"))

    def test_unpair_endpoint_revokes_token(self) -> None:
        unpair_resp = self.client.post(
            "/api/device/unpair/",
            HTTP_AUTHORIZATION=f"Bearer {self.token_a}",
        )
        self.assertEqual(unpair_resp.status_code, status.HTTP_200_OK)
        self.assertEqual(unpair_resp.data["status"], "unpaired")

        get_resp = self.client.get("/api/clipboard/latest/", HTTP_AUTHORIZATION=f"Bearer {self.token_a}")
        self.assertEqual(get_resp.status_code, status.HTTP_401_UNAUTHORIZED)
