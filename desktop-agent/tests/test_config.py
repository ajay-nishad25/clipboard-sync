"""Tests for desktop-agent environment configuration."""

from __future__ import annotations

import unittest

from clipboard_agent.config import (
    DEFAULT_API_URL,
    DEFAULT_DEVICE_ID,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_WS_URL,
    load_config,
)


class AgentConfigTests(unittest.TestCase):
    def test_uses_development_defaults(self) -> None:
        config = load_config({})

        self.assertEqual(config.api_url, DEFAULT_API_URL)
        self.assertEqual(config.ws_url, DEFAULT_WS_URL)
        self.assertEqual(config.device_id, DEFAULT_DEVICE_ID)
        self.assertEqual(config.timeout_seconds, DEFAULT_TIMEOUT_SECONDS)

    def test_uses_environment_overrides(self) -> None:
        config = load_config(
            {
                "CLIPBOARD_API_URL": "http://example.test/api/clipboard/",
                "CLIPBOARD_WS_URL": "ws://example.test/ws/clipboard/",
                "CLIPBOARD_DEVICE_ID": "desktop-test",
                "CLIPBOARD_API_TIMEOUT_SECONDS": "2.5",
            }
        )

        self.assertEqual(config.api_url, "http://example.test/api/clipboard/")
        self.assertEqual(config.ws_url, "ws://example.test/ws/clipboard/")
        self.assertEqual(config.device_id, "desktop-test")
        self.assertEqual(config.timeout_seconds, 2.5)

    def test_rejects_invalid_timeout(self) -> None:
        with self.assertRaises(ValueError):
            load_config({"CLIPBOARD_API_TIMEOUT_SECONDS": "0"})

    def test_rejects_empty_ws_url(self) -> None:
        with self.assertRaises(ValueError):
            load_config({"CLIPBOARD_WS_URL": ""})

    def test_ws_url_default_is_local_ws_endpoint(self) -> None:
        config = load_config({})
        self.assertTrue(config.ws_url.startswith("ws://"))
        self.assertIn("ws/clipboard", config.ws_url)
