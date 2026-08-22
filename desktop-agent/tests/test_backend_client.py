"""Unit tests for the desktop agent's Django API client."""

from __future__ import annotations

import logging
import unittest
from unittest.mock import Mock

import requests

from clipboard_agent.backend_client import ClipboardBackendClient
from clipboard_agent.monitor import ClipboardMonitor


class FakeResponse:
    """Small response double with the interface used by the client."""

    def __init__(self, status_code: int, data: object | None = None) -> None:
        self.status_code = status_code
        self._data = data

    def json(self) -> object:
        if isinstance(self._data, Exception):
            raise self._data
        return self._data


class ClipboardBackendClientTests(unittest.TestCase):
    def setUp(self) -> None:
        self.logger = logging.getLogger(f"clipboard_agent.tests.{self.id()}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False
        self.post = Mock()
        self.client = ClipboardBackendClient(
            api_url="http://127.0.0.1:8000/api/clipboard/",
            device_id="desktop-001",
            timeout_seconds=5,
            logger=self.logger,
            post=self.post,
        )

    def test_sends_expected_json_payload_on_success(self) -> None:
        self.post.return_value = FakeResponse(201, {"id": 1, "content": "Hello"})

        result = self.client.send("Hello")

        self.assertTrue(result)
        self.post.assert_called_once_with(
            "http://127.0.0.1:8000/api/clipboard/",
            json={"device_id": "desktop-001", "content": "Hello"},
            timeout=5,
        )

    def test_returns_false_for_backend_failure(self) -> None:
        self.post.return_value = FakeResponse(500, {"detail": "Server error"})

        with self.assertLogs(self.logger, "WARNING") as logs:
            result = self.client.send("Hello")

        self.assertFalse(result)
        self.assertIn("HTTP status 500", logs.output[-1])

    def test_returns_false_for_network_failure(self) -> None:
        self.post.side_effect = requests.ConnectionError("connection refused")

        with self.assertLogs(self.logger, "ERROR") as logs:
            result = self.client.send("Hello")

        self.assertFalse(result)
        self.assertIn("Unable to synchronize", logs.output[-1])

    def test_returns_false_for_timeout(self) -> None:
        self.post.side_effect = requests.Timeout("request timed out")

        self.assertFalse(self.client.send("Hello"))

    def test_returns_false_for_unexpected_success_response(self) -> None:
        self.post.return_value = FakeResponse(201, {"id": "wrong", "content": "Hello"})

        with self.assertLogs(self.logger, "WARNING") as logs:
            result = self.client.send("Hello")

        self.assertFalse(result)
        self.assertIn("unexpected", logs.output[-1])

    def test_monitor_continues_after_failed_send_and_posts_next_value(self) -> None:
        values = iter(["First", "Second"])
        self.post.side_effect = [
            requests.ConnectionError("connection refused"),
            FakeResponse(201, {"id": 2, "content": "Second"}),
        ]
        monitor = ClipboardMonitor(
            read_clipboard=lambda: next(values),
            logger=self.logger,
            on_text_change=self.client.send,
        )

        monitor.poll_once()
        monitor.poll_once()

        self.assertEqual(self.post.call_count, 2)
        self.assertEqual(self.post.call_args.kwargs["json"]["content"], "Second")
