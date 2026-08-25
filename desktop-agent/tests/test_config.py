"""Tests for desktop-agent environment configuration and pairing helper."""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from clipboard_agent.cli import request_pairing_code
from clipboard_agent.config import (
    DEFAULT_API_URL,
    DEFAULT_PAIRING_URL,
    DEFAULT_REST_LATEST_URL,
    DEFAULT_TIMEOUT_SECONDS,
    DEFAULT_WS_URL,
    get_persistent_device_id,
    load_config,
)


class AgentConfigTests(unittest.TestCase):
    def test_uses_development_defaults(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = load_config({}, storage_dir=Path(tmp_dir))

            self.assertEqual(config.api_url, DEFAULT_API_URL)
            self.assertEqual(config.rest_latest_url, DEFAULT_REST_LATEST_URL)
            self.assertEqual(config.pairing_url, DEFAULT_PAIRING_URL)
            self.assertEqual(config.ws_url, DEFAULT_WS_URL)
            self.assertTrue(config.device_id.startswith("desktop-"))
            self.assertEqual(config.timeout_seconds, DEFAULT_TIMEOUT_SECONDS)

    def test_uses_environment_overrides(self) -> None:
        config = load_config(
            {
                "CLIPBOARD_API_URL": "http://example.test/api/clipboard/",
                "CLIPBOARD_REST_LATEST_URL": "http://example.test/api/clipboard/latest/",
                "CLIPBOARD_PAIRING_URL": "http://example.test/api/device/pairing/create/",
                "CLIPBOARD_WS_URL": "ws://example.test/ws/clipboard/",
                "CLIPBOARD_DEVICE_ID": "desktop-test",
                "CLIPBOARD_API_TIMEOUT_SECONDS": "2.5",
            }
        )

        self.assertEqual(config.api_url, "http://example.test/api/clipboard/")
        self.assertEqual(config.rest_latest_url, "http://example.test/api/clipboard/latest/")
        self.assertEqual(config.pairing_url, "http://example.test/api/device/pairing/create/")
        self.assertEqual(config.ws_url, "ws://example.test/ws/clipboard/")
        self.assertEqual(config.device_id, "desktop-test")
        self.assertEqual(config.timeout_seconds, 2.5)

    def test_persistent_device_id_generated_and_reused(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            id_1 = get_persistent_device_id(storage_dir=tmp_path)
            id_2 = get_persistent_device_id(storage_dir=tmp_path)

            self.assertTrue(id_1.startswith("desktop-"))
            self.assertEqual(id_1, id_2)

    def test_rejects_invalid_timeout(self) -> None:
        with self.assertRaises(ValueError):
            load_config({"CLIPBOARD_API_TIMEOUT_SECONDS": "0"})

    def test_rejects_empty_ws_url(self) -> None:
        with self.assertRaises(ValueError):
            load_config({"CLIPBOARD_WS_URL": ""})

    def test_rejects_empty_rest_latest_url(self) -> None:
        with self.assertRaises(ValueError):
            load_config({"CLIPBOARD_REST_LATEST_URL": ""})

    def test_rejects_empty_pairing_url(self) -> None:
        with self.assertRaises(ValueError):
            load_config({"CLIPBOARD_PAIRING_URL": ""})

    def test_ws_url_default_is_local_ws_endpoint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            config = load_config({}, storage_dir=Path(tmp_dir))
            self.assertTrue(config.ws_url.startswith("ws://"))
            self.assertIn("ws/clipboard", config.ws_url)

    def test_request_pairing_code_parses_json_response(self) -> None:
        response_mock = Mock()
        response_mock.status = 201
        response_mock.read.return_value = json.dumps(
            {"code": "AB7K-29XM", "expires_at": "2026-08-25T18:05:00Z"}
        ).encode("utf-8")
        response_mock.__enter__ = Mock(return_value=response_mock)
        response_mock.__exit__ = Mock(return_value=None)

        with patch("urllib.request.urlopen", return_value=response_mock):
            result = request_pairing_code("http://127.0.0.1:8000/api/device/pairing/create/", "desktop-001")
            self.assertIsNotNone(result)
            self.assertEqual(result["code"], "AB7K-29XM")
