"""WebSocket client for sending clipboard updates to the Django backend."""

from __future__ import annotations

import json
import logging
import time

from websockets.sync.client import connect

# Reconnection backoff delays in seconds. Each failure advances to the next
# delay (capped at the last value), so the sequence is 2 → 5 → 15 → 30 s.
_BACKOFF_DELAYS = (2, 5, 15, 30)


class ClipboardWebSocketClient:
    """Send clipboard.update messages over a persistent WebSocket connection.

    Connection lifecycle:
    - The connection is established lazily on the first send().
    - If the connection is lost, the client reconnects on the next send() call,
      provided the backoff window has elapsed.
    - Reconnection uses bounded exponential-ish backoff: 2 s → 5 s → 15 s →
      30 s. The backoff counter resets after a successful send.
    - A failed send returns False and schedules the next retry. The clipboard
      monitor continues running; the missed value is not queued or retried.

    Thread safety:
    - This client is not thread-safe. Use it from a single thread (the
      monitoring loop).
    """

    def __init__(
        self,
        ws_url: str,
        device_id: str,
        logger: logging.Logger,
    ) -> None:
        self._base_url = ws_url.rstrip("/") + "/"
        self._device_id = device_id
        self._logger = logger
        self._connection = None
        self._backoff_index = 0
        self._retry_after = 0.0  # time.monotonic() value

    def send(self, content: str) -> bool:
        """Send a clipboard.update for *content*; return True on ack.

        Returns False without raising if the connection is unavailable,
        the send fails, or the server returns an error response.
        """
        if not self._ensure_connected():
            return False

        payload = json.dumps(
            {
                "type": "clipboard.update",
                "device_id": self._device_id,
                "content": content,
            }
        )
        try:
            self._connection.send(payload)
            raw = self._connection.recv(timeout=10)
        except Exception as error:
            self._logger.warning("WebSocket send failed: %s", error)
            self._close_connection()
            self._advance_backoff()
            return False

        try:
            response = json.loads(raw)
        except json.JSONDecodeError:
            self._logger.warning("WebSocket received non-JSON acknowledgement.")
            return False

        if response.get("type") == "clipboard.ack":
            self._logger.info("Clipboard entry synchronized successfully via WebSocket.")
            self._reset_backoff()
            return True

        code = response.get("code", "unknown")
        detail = response.get("detail", "")
        self._logger.warning(
            "Server rejected clipboard update: %s — %s", code, detail
        )
        return False

    def close(self) -> None:
        """Close the WebSocket connection gracefully."""
        self._close_connection()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> bool:
        """Return True if a connection is available or was just established."""
        if self._connection is not None:
            return True

        if time.monotonic() < self._retry_after:
            return False

        return self._connect()

    def _connect(self) -> bool:
        """Try to open a new connection; return True on success."""
        url = self._build_url()
        try:
            self._connection = connect(url)
            self._logger.info("WebSocket connection established to %s.", url)
            return True
        except Exception as error:
            self._logger.warning("WebSocket connection failed: %s", error)
            self._connection = None
            self._advance_backoff()
            return False

    def _close_connection(self) -> None:
        if self._connection is not None:
            try:
                self._connection.close()
            except Exception:
                pass
            self._connection = None

    def _build_url(self) -> str:
        """Return the WebSocket URL with the device_id query parameter."""
        sep = "&" if "?" in self._base_url else "?"
        return f"{self._base_url}{sep}device_id={self._device_id}"

    def _advance_backoff(self) -> None:
        """Record the next earliest reconnection time and advance the index."""
        delay = _BACKOFF_DELAYS[self._backoff_index]
        self._retry_after = time.monotonic() + delay
        self._logger.info(
            "WebSocket reconnection scheduled in %d seconds.", delay
        )
        if self._backoff_index < len(_BACKOFF_DELAYS) - 1:
            self._backoff_index += 1

    def _reset_backoff(self) -> None:
        self._backoff_index = 0
        self._retry_after = 0.0
