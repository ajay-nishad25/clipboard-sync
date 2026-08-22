"""Environment-based configuration for the desktop agent."""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Mapping

DEFAULT_API_URL = "http://127.0.0.1:8000/api/clipboard/"
DEFAULT_DEVICE_ID = "desktop-001"
DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class AgentConfig:
    """Connection settings for the development backend."""

    api_url: str
    device_id: str
    timeout_seconds: float


def load_config(environ: Mapping[str, str] | None = None) -> AgentConfig:
    """Load and validate optional environment configuration."""
    source = os.environ if environ is None else environ
    api_url = source.get("CLIPBOARD_API_URL", DEFAULT_API_URL).strip()
    device_id = source.get("CLIPBOARD_DEVICE_ID", DEFAULT_DEVICE_ID).strip()
    timeout_value = source.get("CLIPBOARD_API_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))

    if not api_url:
        raise ValueError("CLIPBOARD_API_URL must not be empty")
    if not device_id:
        raise ValueError("CLIPBOARD_DEVICE_ID must not be empty")

    try:
        timeout_seconds = float(timeout_value)
    except ValueError as error:
        raise ValueError("CLIPBOARD_API_TIMEOUT_SECONDS must be a number") from error

    if timeout_seconds <= 0:
        raise ValueError("CLIPBOARD_API_TIMEOUT_SECONDS must be greater than zero")

    return AgentConfig(
        api_url=api_url,
        device_id=device_id,
        timeout_seconds=timeout_seconds,
    )
