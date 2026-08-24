"""WebSocket client for sending and receiving clipboard updates with Django backend."""

from __future__ import annotations

import json
import logging
import queue
import threading
import time
from collections.abc import Callable

from websockets.sync.client import ClientConnection, connect

# Reconnection backoff delays in seconds. Each failure advances to the next
# delay (capped at the last value), so the sequence is 2 → 5 → 15 → 30 s.
_BACKOFF_DELAYS = (2, 5, 15, 30)

RemoteUpdateHandler = Callable[[str, str], object]


class ClipboardWebSocketClient:
    """Send clipboard.update messages and receive clipboard.remote_update messages.

    Connection lifecycle:
    - Established lazily on the first send() or connect call.
    - Runs a background listener thread to receive incoming server messages.
    - Reconnection uses bounded backoff: 2 s → 5 s → 15 s → 30 s.
    - Clean thread shutdown on close().
    """

    def __init__(
        self,
        ws_url: str,
        device_id: str,
        logger: logging.Logger,
        on_remote_update: RemoteUpdateHandler | None = None,
    ) -> None:
        self._base_url = ws_url.rstrip("/") + "/"
        self._device_id = device_id
        self._logger = logger
        self._on_remote_update = on_remote_update

        self._connection: ClientConnection | None = None
        self._connection_lock = threading.RLock()
        self._listen_thread: threading.Thread | None = None
        self._running = False

        self._ack_queue: queue.Queue[dict] = queue.Queue()

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

        # Clear any stale ACKs before sending
        while not self._ack_queue.empty():
            try:
                self._ack_queue.get_nowait()
            except queue.Empty:
                break

        with self._connection_lock:
            if self._connection is None:
                return False
            try:
                self._connection.send(payload)
            except Exception as error:
                self._logger.warning("WebSocket send failed: %s", error)
                self._close_connection()
                self._advance_backoff()
                return False

        try:
            response = self._ack_queue.get(timeout=10.0)
        except queue.Empty:
            self._logger.warning("WebSocket send timed out waiting for ACK.")
            self._close_connection()
            self._advance_backoff()
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
        """Close the WebSocket connection gracefully and stop the listener thread."""
        self._running = False
        self._close_connection()
        if self._listen_thread is not None and self._listen_thread.is_alive():
            self._listen_thread.join(timeout=2.0)

    # ------------------------------------------------------------------
    # Internal helpers & listener loop
    # ------------------------------------------------------------------

    def _ensure_connected(self) -> bool:
        """Return True if a connection is available or was just established."""
        with self._connection_lock:
            if self._connection is not None:
                return True

        if time.monotonic() < self._retry_after:
            return False

        return self._connect()

    def _connect(self) -> bool:
        """Try to open a new connection; return True on success."""
        url = self._build_url()
        try:
            conn = connect(url)
            with self._connection_lock:
                self._connection = conn
                self._running = True
                self._listen_thread = threading.Thread(
                    target=self._listen_loop,
                    daemon=True,
                    name="ws-listener",
                )
                self._listen_thread.start()
            self._logger.info("WebSocket connection established to %s.", url)
            return True
        except Exception as error:
            self._logger.warning("WebSocket connection failed: %s", error)
            with self._connection_lock:
                self._connection = None
            self._advance_backoff()
            return False

    def _listen_loop(self) -> None:
        """Background listener thread reading incoming WebSocket messages."""
        while self._running:
            conn = self._connection
            if conn is None:
                break

            try:
                raw = conn.recv()
            except Exception:
                if self._running:
                    self._logger.debug("WebSocket connection closed in listener thread.")
                    self._advance_backoff()
                break

            try:
                message = json.loads(raw)
            except json.JSONDecodeError:
                self._logger.warning("WebSocket received non-JSON message.")
                continue

            msg_type = message.get("type")
            if msg_type in ("clipboard.ack", "error"):
                self._ack_queue.put(message)
            elif msg_type == "clipboard.remote_update":
                sender_id = message.get("device_id", "unknown")
                content = message.get("content", "")
                self._logger.info(
                    "Received remote clipboard update from %s (%d chars).",
                    sender_id,
                    len(content),
                )
                if self._on_remote_update is not None:
                    try:
                        self._on_remote_update(sender_id, content)
                    except Exception:
                        self._logger.exception("Error in on_remote_update handler.")
            else:
                self._logger.debug("Unhandled WebSocket message type: %s", msg_type)

        with self._connection_lock:
            self._close_connection()

        if self._running and self._ack_queue.empty():
            self._ack_queue.put({"type": "error", "code": "disconnected", "detail": "Connection closed"})

    def _close_connection(self) -> None:
        with self._connection_lock:
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
