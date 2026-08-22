"""Unit tests for clipboard polling behavior."""

from __future__ import annotations

import logging
import unittest

from clipboard_agent.monitor import ClipboardMonitor


class ClipboardMonitorTests(unittest.TestCase):
    """Test clipboard events without requiring an operating-system clipboard."""

    def setUp(self) -> None:
        self.logger = logging.getLogger(f"clipboard_agent.tests.{self.id()}")
        self.logger.setLevel(logging.DEBUG)
        self.logger.propagate = False

    def create_monitor(self, reader):
        return ClipboardMonitor(read_clipboard=reader, logger=self.logger)

    def test_logs_new_text_once(self) -> None:
        monitor = self.create_monitor(lambda: "Hello World")

        with self.assertLogs(self.logger, "INFO") as logs:
            monitor.poll_once()
            monitor.poll_once()

        self.assertEqual(len(logs.output), 1)
        self.assertIn("Hello World", logs.output[0])

    def test_logs_each_distinct_text_value(self) -> None:
        values = iter(["First", "Second"])
        monitor = self.create_monitor(lambda: next(values))

        with self.assertLogs(self.logger, "INFO") as logs:
            monitor.poll_once()
            monitor.poll_once()

        self.assertEqual(len(logs.output), 2)
        self.assertIn("First", logs.output[0])
        self.assertIn("Second", logs.output[1])

    def test_empty_clipboard_is_ignored_safely(self) -> None:
        monitor = self.create_monitor(lambda: "")

        with self.assertLogs(self.logger, "DEBUG") as logs:
            monitor.poll_once()

        self.assertIn("Clipboard is empty", logs.output[0])

    def test_reader_error_is_logged_once_until_a_successful_read(self) -> None:
        def failing_reader() -> str:
            raise RuntimeError("clipboard unavailable")

        monitor = self.create_monitor(failing_reader)

        with self.assertLogs(self.logger, "WARNING") as logs:
            monitor.poll_once()
            monitor.poll_once()

        self.assertEqual(len(logs.output), 1)
        self.assertIn("Unable to access the clipboard", logs.output[0])

    def test_non_text_content_is_ignored(self) -> None:
        monitor = self.create_monitor(lambda: None)  # type: ignore[return-value]

        with self.assertLogs(self.logger, "WARNING") as logs:
            monitor.poll_once()

        self.assertIn("not text", logs.output[0])

    def test_rejects_non_positive_interval(self) -> None:
        with self.assertRaises(ValueError):
            ClipboardMonitor(lambda: "text", self.logger, interval_seconds=0)

    def test_sends_each_distinct_value_to_change_handler_once(self) -> None:
        handler = unittest.mock.Mock()
        monitor = ClipboardMonitor(
            read_clipboard=lambda: "Hello World",
            logger=self.logger,
            on_text_change=handler,
        )

        monitor.poll_once()
        monitor.poll_once()

        handler.assert_called_once_with("Hello World")

    def test_monitor_continues_after_change_handler_failure(self) -> None:
        values = iter(["First", "Second"])
        handler = unittest.mock.Mock(side_effect=[RuntimeError("server unavailable"), None])
        monitor = ClipboardMonitor(
            read_clipboard=lambda: next(values),
            logger=self.logger,
            on_text_change=handler,
        )

        with self.assertLogs(self.logger, "ERROR"):
            monitor.poll_once()
            monitor.poll_once()

        self.assertEqual(handler.call_count, 2)
