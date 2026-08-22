from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIClient

from clipboard.models import ClipboardEntry


class ClipboardEntryModelTests(TestCase):
    def test_creates_clipboard_entry(self) -> None:
        entry = ClipboardEntry.objects.create(device_id="desktop-001", content="Hello World")
        self.assertEqual(entry.device_id, "desktop-001")
        self.assertEqual(entry.content, "Hello World")
        self.assertIsNotNone(entry.created_at)


class ClipboardApiTests(TestCase):
    def setUp(self) -> None:
        self.client = APIClient()

    def test_post_creates_clipboard_entry(self) -> None:
        response = self.client.post(
            "/api/clipboard/",
            {"device_id": "desktop-001", "content": "Hello World"},
            format="json",
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["device_id"], "desktop-001")
        self.assertEqual(response.data["content"], "Hello World")
        self.assertEqual(ClipboardEntry.objects.count(), 1)

    def test_post_rejects_missing_or_non_text_fields(self) -> None:
        missing_device = self.client.post("/api/clipboard/", {"content": "Hello World"}, format="json")
        non_text_content = self.client.post(
            "/api/clipboard/",
            {"device_id": "desktop-001", "content": 123},
            format="json",
        )
        self.assertEqual(missing_device.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("device_id", missing_device.data)
        self.assertEqual(non_text_content.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("content", non_text_content.data)
        self.assertEqual(ClipboardEntry.objects.count(), 0)

    def test_latest_returns_most_recent_entry(self) -> None:
        older_entry = ClipboardEntry.objects.create(device_id="desktop-001", content="Older text")
        latest_entry = ClipboardEntry.objects.create(device_id="desktop-001", content="Latest text")
        response = self.client.get("/api/clipboard/latest/")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["id"], latest_entry.id)
        self.assertNotEqual(response.data["id"], older_entry.id)
        self.assertEqual(response.data["content"], "Latest text")

    def test_latest_returns_not_found_without_entries(self) -> None:
        response = self.client.get("/api/clipboard/latest/")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(response.data["detail"], "No clipboard entries found.")
