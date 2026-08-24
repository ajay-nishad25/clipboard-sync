"""Polling-based text clipboard monitoring."""

from __future__ import annotations

import logging
import time
from collections.abc import Callable

ClipboardReader = Callable[[], str]
ClipboardChangeHandler = Callable[[str], object]


class ClipboardMonitor:
    """Log distinct non-empty text values returned by a clipboard reader."""

    def __init__(
        self,
        read_clipboard: ClipboardReader,
        logger: logging.Logger,
        interval_seconds: float = 0.5,
        on_text_change: ClipboardChangeHandler | None = None,
    ) -> None:
        if interval_seconds <= 0:
            raise ValueError("interval_seconds must be greater than zero")

        self._read_clipboard = read_clipboard
        self._logger = logger
        self._interval_seconds = interval_seconds
        self._on_text_change = on_text_change
        self._last_content: str | None = None
        self._last_error: str | None = None

    def set_last_content(self, content: str) -> None:
        """Update last_content to prevent triggering a local change for remote updates."""
        self._last_content = content

    def poll_once(self) -> None:
        """Read and process one clipboard value without stopping on failures."""
        try:
            content = self._read_clipboard()
        except Exception as error:
            self._log_clipboard_error(error)
            return

        self._last_error = None

        if not isinstance(content, str):
            self._logger.warning("Ignoring clipboard content because it is not text.")
            return

        if not content:
            if content != self._last_content:
                self._last_content = content
                self._logger.debug("Clipboard is empty; waiting for text.")
            return

        if content == self._last_content:
            return

        self._last_content = content
        self._logger.info("Clipboard changed:\n%s", content)
        self._notify_text_change(content)

    def run_forever(self) -> None:
        """Poll until interrupted, logging an unexpected monitoring failure."""
        self._logger.info("Desktop Clipboard Agent started.")
        try:
            while True:
                self.poll_once()
                time.sleep(self._interval_seconds)
        except KeyboardInterrupt:
            self._logger.info("Desktop Clipboard Agent stopped.")
        except Exception:
            self._logger.exception("Desktop Clipboard Agent stopped unexpectedly.")

    def _log_clipboard_error(self, error: Exception) -> None:
        message = f"{type(error).__name__}: {error}"
        if message == self._last_error:
            return

        self._last_error = message
        self._logger.warning("Unable to access the clipboard: %s", message)

    def _notify_text_change(self, content: str) -> None:
        if self._on_text_change is None:
            return

        try:
            self._on_text_change(content)
        except Exception:
            self._logger.exception("Unable to handle clipboard change.")
