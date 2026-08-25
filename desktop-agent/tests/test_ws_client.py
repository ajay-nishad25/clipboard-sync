"""Unit tests for the desktop agent's WebSocket client."""

from __future__ import annotations

import json
import logging
import time
import unittest
from unittest.mock import MagicMock, Mock, call, patch

from clipboard_agent.cli import fetch_latest_clipboard_text
from clipboard_agent.monitor import ClipboardMonitor
from clipboard_agent.ws_client import ClipboardWebSocketClient, _BACKOFF_DELAYS


def _make_client(ws_url: str = "ws://127.0.0.1:8000/ws/clipboard/", on_remote_update=None, on_connected=None) -> ClipboardWebSocketClient:
    logger = logging.getLogger(f"test.ws_client.{ws_url}")
    logger.propagate = False
    return ClipboardWebSocketClient(
        ws_url=ws_url,
        device_id="desktop-001",
        credential="desktop-001",
        logger=logger,
        on_remote_update=on_remote_update,
        on_connected=on_connected,
    )


def _ack_connection(content: str = "Hello") -> Mock:
    """Return a mock connection that responds with clipboard.ack."""
    conn = Mock()
    conn.recv.side_effect = lambda: json.dumps(
        {"type": "clipboard.ack", "device_id": "desktop-001", "status": "stored"}
    )
    return conn


def _error_connection(code: str = "invalid_content", detail: str = "bad") -> Mock:
    """Return a mock connection that responds with an error."""
    conn = Mock()
    conn.recv.side_effect = lambda: json.dumps(
        {"type": "error", "code": code, "detail": detail}
    )
    return conn


class ClipboardWebSocketClientSendTests(unittest.TestCase):
    def test_sends_correct_clipboard_update_payload(self) -> None:
        client = _make_client()
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            client.send("Hello")

        expected_payload = json.dumps(
            {"type": "clipboard.update", "device_id": "desktop-001", "content": "Hello"}
        )
        conn.send.assert_called_once_with(expected_payload)
        client.close()

    def test_url_includes_device_id_query_param(self) -> None:
        client = _make_client()
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn) as mock_connect:
            client.send("Hello")

        mock_connect.assert_called_once_with(
            "ws://127.0.0.1:8000/ws/clipboard/?token=desktop-001&device_id=desktop-001"
        )
        client.close()

    def test_ack_response_returns_true(self) -> None:
        client = _make_client()
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            result = client.send("Hello")

        self.assertTrue(result)
        client.close()

    def test_server_error_response_returns_false(self) -> None:
        client = _make_client()
        conn = _error_connection("invalid_content", "Clipboard content must be a non-empty string.")

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            result = client.send("Hello")

        self.assertFalse(result)
        client.close()

    def test_reuses_existing_connection_on_second_send(self) -> None:
        client = _make_client()
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn) as mock_connect:
            client.send("First")
            client.send("Second")

        mock_connect.assert_called_once()
        self.assertEqual(conn.send.call_count, 2)
        client.close()

    def test_non_json_server_response_returns_false(self) -> None:
        client = _make_client()
        conn = Mock()
        conn.recv.side_effect = ["not-json", Exception("closed")]

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            result = client.send("Hello")

        self.assertFalse(result)
        client.close()

    def test_remote_update_invokes_callback(self) -> None:
        handler = Mock()
        client = _make_client(on_remote_update=handler)
        conn = Mock()
        conn.recv.side_effect = [
            json.dumps({"type": "clipboard.remote_update", "device_id": "android-001", "content": "Hello from Android"}),
            Exception("closed"),
        ]

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            self.assertTrue(client._ensure_connected())
            time.sleep(0.1)

        handler.assert_called_once_with("android-001", "Hello from Android")
        client.close()

    def test_on_connected_invoked_on_connection(self) -> None:
        handler = Mock()
        client = _make_client(on_connected=handler)
        conn = Mock()
        conn.recv.side_effect = Exception("closed")

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            self.assertTrue(client._ensure_connected())
            time.sleep(0.1)

        handler.assert_called_once()
        client.close()

    def test_fetch_latest_clipboard_text_parses_json(self) -> None:
        response_mock = Mock()
        response_mock.status = 200
        response_mock.read.return_value = json.dumps({"content": "Recovered text"}).encode("utf-8")
        response_mock.__enter__ = Mock(return_value=response_mock)
        response_mock.__exit__ = Mock(return_value=None)

        with patch("urllib.request.urlopen", return_value=response_mock):
            content = fetch_latest_clipboard_text("http://127.0.0.1:8000/api/clipboard/latest/", "devtok_123")
            self.assertEqual(content, "Recovered text")


class ClipboardWebSocketClientConnectionTests(unittest.TestCase):
    def test_connect_failure_returns_false(self) -> None:
        client = _make_client()

        with patch("clipboard_agent.ws_client.connect", side_effect=OSError("refused")):
            result = client.send("Hello")

        self.assertFalse(result)
        client.close()

    def test_connect_failure_schedules_backoff(self) -> None:
        client = _make_client()
        before = time.monotonic()

        with patch("clipboard_agent.ws_client.connect", side_effect=OSError("refused")):
            client.send("Hello")

        self.assertGreater(client._retry_after, before)
        self.assertAlmostEqual(
            client._retry_after - before, _BACKOFF_DELAYS[0], delta=0.1
        )
        client.close()

    def test_send_failure_closes_connection_and_schedules_backoff(self) -> None:
        client = _make_client()
        conn = Mock()
        conn.send.side_effect = OSError("broken pipe")
        conn.recv.side_effect = Exception("closed")

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            result = client.send("Hello")

        self.assertFalse(result)
        conn.close.assert_called()
        self.assertIsNone(client._connection)
        self.assertGreater(client._retry_after, 0.0)
        client.close()

    def test_no_reconnect_attempt_during_backoff_window(self) -> None:
        client = _make_client()
        client._retry_after = time.monotonic() + 100

        with patch("clipboard_agent.ws_client.connect") as mock_connect:
            result = client.send("Hello")

        mock_connect.assert_not_called()
        self.assertFalse(result)
        client.close()

    def test_reconnects_when_backoff_window_expires(self) -> None:
        client = _make_client()
        client._retry_after = time.monotonic() - 1
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn) as mock_connect:
            result = client.send("Hello")

        mock_connect.assert_called_once()
        self.assertTrue(result)
        client.close()

    def test_successful_send_resets_backoff(self) -> None:
        client = _make_client()
        client._backoff_index = 2
        client._retry_after = time.monotonic() - 1
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            client.send("Hello")

        self.assertEqual(client._backoff_index, 0)
        self.assertEqual(client._retry_after, 0.0)
        client.close()

    def test_backoff_index_advances_on_repeated_failures(self) -> None:
        client = _make_client()

        for expected_index in range(1, len(_BACKOFF_DELAYS)):
            client._retry_after = 0.0
            with patch("clipboard_agent.ws_client.connect", side_effect=OSError("refused")):
                client.send("Hello")
            self.assertEqual(client._backoff_index, expected_index)
        client.close()

    def test_backoff_index_caps_at_last_delay(self) -> None:
        client = _make_client()
        client._backoff_index = len(_BACKOFF_DELAYS) - 1

        client._retry_after = 0.0
        with patch("clipboard_agent.ws_client.connect", side_effect=OSError("refused")):
            client.send("Hello")

        self.assertEqual(client._backoff_index, len(_BACKOFF_DELAYS) - 1)
        client.close()

    def test_close_releases_connection(self) -> None:
        client = _make_client()
        conn = _ack_connection()

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            client.send("Hello")

        client.close()

        conn.close.assert_called()
        self.assertIsNone(client._connection)

    def test_close_when_not_connected_is_safe(self) -> None:
        client = _make_client()
        client.close()


class ClipboardWebSocketClientMonitorIntegrationTests(unittest.TestCase):
    """Verify ws_client integrates correctly with ClipboardMonitor."""

    def _make_monitor(self, client: ClipboardWebSocketClient, values: list[str]) -> ClipboardMonitor:
        logger = logging.getLogger("test.monitor.ws")
        logger.propagate = False
        values_iter = iter(values)
        return ClipboardMonitor(
            read_clipboard=lambda: next(values_iter, ""),
            logger=logger,
            on_text_change=client.send,
        )

    def test_monitor_continues_after_ws_failure(self) -> None:
        client = _make_client()
        conn = Mock()
        conn.send.side_effect = [OSError("broken"), None]
        conn.recv.side_effect = lambda: json.dumps(
            {"type": "clipboard.ack", "device_id": "desktop-001", "status": "stored"}
        )
        monitor = self._make_monitor(client, ["First", "Second"])

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            monitor.poll_once()  # First → send fails
            client._retry_after = 0.0
            client._connection = conn
            monitor.poll_once()  # Second → send succeeds

        self.assertEqual(conn.send.call_count, 2)
        client.close()

    def test_duplicate_clipboard_values_not_resent(self) -> None:
        client = _make_client()
        conn = _ack_connection()
        monitor = self._make_monitor(client, ["Hello", "Hello", "World"])

        with patch("clipboard_agent.ws_client.connect", return_value=conn):
            monitor.poll_once()  # Hello → sent
            monitor.poll_once()  # Hello → duplicate, skipped
            monitor.poll_once()  # World → sent

        self.assertEqual(conn.send.call_count, 2)
        payloads = [json.loads(c.args[0]) for c in conn.send.call_args_list]
        self.assertEqual(payloads[0]["content"], "Hello")
        self.assertEqual(payloads[1]["content"], "World")
        client.close()
