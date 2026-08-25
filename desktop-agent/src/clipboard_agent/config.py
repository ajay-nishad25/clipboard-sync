"""Environment-based configuration for the desktop agent."""

from __future__ import annotations

import os
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

DEFAULT_API_URL = "http://127.0.0.1:8000/api/clipboard/"
DEFAULT_REST_LATEST_URL = "http://127.0.0.1:8000/api/clipboard/latest/"
DEFAULT_WS_URL = "ws://127.0.0.1:8000/ws/clipboard/"
DEFAULT_TIMEOUT_SECONDS = 5.0


@dataclass(frozen=True)
class AgentConfig:
    """Connection settings for the development backend."""

    api_url: str
    rest_latest_url: str
    ws_url: str
    device_id: str
    timeout_seconds: float


def get_persistent_device_id(storage_dir: Path | None = None) -> str:
    """Return a stored device ID, or generate and persist a new desktop UUID."""
    if storage_dir is None:
        storage_dir = Path.home() / ".clipboard_sync"

    file_path = storage_dir / "device_id.txt"
    if file_path.exists():
        try:
            device_id = file_path.read_text("utf-8").strip()
            if device_id:
                return device_id
        except Exception:
            pass

    device_id = f"desktop-{uuid.uuid4().hex[:8]}"
    try:
        storage_dir.mkdir(parents=True, exist_ok=True)
        file_path.write_text(device_id, "utf-8")
    except Exception:
        pass

    return device_id


def load_config(
    environ: Mapping[str, str] | None = None,
    storage_dir: Path | None = None,
) -> AgentConfig:
    """Load and validate optional environment configuration."""
    source = os.environ if environ is None else environ
    api_url = source.get("CLIPBOARD_API_URL", DEFAULT_API_URL).strip()
    rest_latest_url = source.get("CLIPBOARD_REST_LATEST_URL", DEFAULT_REST_LATEST_URL).strip()
    ws_url = source.get("CLIPBOARD_WS_URL", DEFAULT_WS_URL).strip()

    if not api_url:
        raise ValueError("CLIPBOARD_API_URL must not be empty")
    if not rest_latest_url:
        raise ValueError("CLIPBOARD_REST_LATEST_URL must not be empty")
    if not ws_url:
        raise ValueError("CLIPBOARD_WS_URL must not be empty")

    env_device_id = source.get("CLIPBOARD_DEVICE_ID")
    if env_device_id is not None:
        device_id = env_device_id.strip()
        if not device_id:
            raise ValueError("CLIPBOARD_DEVICE_ID must not be empty")
    else:
        device_id = get_persistent_device_id(storage_dir=storage_dir)

    timeout_value = source.get("CLIPBOARD_API_TIMEOUT_SECONDS", str(DEFAULT_TIMEOUT_SECONDS))
    try:
        timeout_seconds = float(timeout_value)
    except ValueError as error:
        raise ValueError("CLIPBOARD_API_TIMEOUT_SECONDS must be a number") from error

    if timeout_seconds <= 0:
        raise ValueError("CLIPBOARD_API_TIMEOUT_SECONDS must be greater than zero")

    return AgentConfig(
        api_url=api_url,
        rest_latest_url=rest_latest_url,
        ws_url=ws_url,
        device_id=device_id,
        timeout_seconds=timeout_seconds,
    )
