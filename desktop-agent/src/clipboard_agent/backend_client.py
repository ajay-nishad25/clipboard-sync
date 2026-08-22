"""HTTP client for sending local clipboard entries to the Django backend."""

from __future__ import annotations

import logging
from collections.abc import Callable
from typing import Any

import requests

HttpPost = Callable[..., requests.Response]


class ClipboardBackendClient:
    """Send clipboard text to the Phase 2 REST API."""

    def __init__(
        self,
        api_url: str,
        device_id: str,
        timeout_seconds: float,
        logger: logging.Logger,
        post: HttpPost = requests.post,
    ) -> None:
        self._api_url = api_url
        self._device_id = device_id
        self._timeout_seconds = timeout_seconds
        self._logger = logger
        self._post = post

    def send(self, content: str) -> bool:
        """Send one text entry and report whether the backend confirmed it."""
        payload = {"device_id": self._device_id, "content": content}
        self._logger.info("Sending clipboard entry to backend.")

        try:
            response = self._post(
                self._api_url,
                json=payload,
                timeout=self._timeout_seconds,
            )
        except requests.RequestException as error:
            self._logger.error("Unable to synchronize clipboard entry: %s", error)
            return False
        except Exception:
            self._logger.exception("Unexpected error while sending clipboard entry.")
            return False

        if response.status_code != requests.codes.created:
            self._logger.warning(
                "Backend rejected clipboard entry with HTTP status %s.",
                response.status_code,
            )
            return False

        if not self._is_expected_response(response, content):
            self._logger.warning("Backend returned an unexpected clipboard entry response.")
            return False

        self._logger.info("Clipboard entry synchronized successfully.")
        return True

    @staticmethod
    def _is_expected_response(response: requests.Response, content: str) -> bool:
        try:
            data: Any = response.json()
        except ValueError:
            return False

        return (
            isinstance(data, dict)
            and isinstance(data.get("id"), int)
            and data.get("content") == content
        )
