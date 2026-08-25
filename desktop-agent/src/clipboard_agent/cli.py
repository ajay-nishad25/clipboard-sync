"""Command-line entry point for the desktop clipboard agent."""

from __future__ import annotations

import argparse
import json
import logging
import urllib.request

import pyperclip

from clipboard_agent.config import (
    DEFAULT_CREDENTIAL_REGISTER_URL,
    load_config,
    save_persistent_device_token,
)
from clipboard_agent.monitor import ClipboardMonitor
from clipboard_agent.ws_client import ClipboardWebSocketClient


def parse_arguments() -> argparse.Namespace:
    """Read command-line configuration for the polling interval."""
    parser = argparse.ArgumentParser(
        description="Log distinct non-empty text values copied to the clipboard."
    )
    parser.add_argument(
        "--interval",
        type=positive_float,
        default=0.5,
        help="Clipboard polling interval in seconds (default: 0.5).",
    )
    return parser.parse_args()


def positive_float(value: str) -> float:
    """Validate a positive command-line interval."""
    interval = float(value)
    if interval <= 0:
        raise argparse.ArgumentTypeError("interval must be greater than zero")
    return interval


def configure_logging() -> logging.Logger:
    """Configure concise logs for interactive use."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    return logging.getLogger("clipboard_agent")


def read_clipboard_text() -> str:
    """Return the current plain-text clipboard content through pyperclip."""
    return pyperclip.paste()


def fetch_latest_clipboard_text(
    rest_latest_url: str, credential: str = "", timeout_seconds: float = 5.0
) -> str | None:
    """Fetch the most recent clipboard text entry from the Django REST API with token authentication."""
    try:
        headers = {"User-Agent": "ClipboardDesktopAgent/1.0", "Accept": "application/json"}
        if credential:
            headers["Authorization"] = f"Bearer {credential}"

        request = urllib.request.Request(
            rest_latest_url,
            headers=headers,
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status == 200:
                data = json.loads(response.read().decode("utf-8"))
                if isinstance(data, dict):
                    content = data.get("content")
                    if isinstance(content, str) and content:
                        return content
    except Exception:
        pass
    return None


def register_device_credential(
    register_url: str, device_id: str, timeout_seconds: float = 5.0
) -> str | None:
    """Register or obtain an authentication credential for the desktop device."""
    try:
        data = json.dumps({"device_id": device_id}).encode("utf-8")
        request = urllib.request.Request(
            register_url,
            data=data,
            headers={
                "User-Agent": "ClipboardDesktopAgent/1.0",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status in (200, 201):
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict) and "credential" in payload:
                    return payload["credential"]
    except Exception:
        pass
    return None


def request_pairing_code(pairing_url: str, device_id: str, timeout_seconds: float = 5.0) -> dict | None:
    """Request a temporary pairing code from the backend."""
    try:
        data = json.dumps({"device_id": device_id}).encode("utf-8")
        request = urllib.request.Request(
            pairing_url,
            data=data,
            headers={
                "User-Agent": "ClipboardDesktopAgent/1.0",
                "Content-Type": "application/json",
                "Accept": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            if response.status in (200, 201):
                payload = json.loads(response.read().decode("utf-8"))
                if isinstance(payload, dict) and "code" in payload:
                    return payload
    except Exception:
        pass
    return None


def main() -> None:
    """Run the local clipboard monitoring loop."""
    arguments = parse_arguments()
    logger = configure_logging()
    try:
        config = load_config()
    except ValueError as error:
        logger.error("Invalid desktop-agent configuration: %s", error)
        return

    logger.info("Using device ID: %s", config.device_id)

    credential = config.credential
    if not credential or credential == config.device_id:
        reg_credential = register_device_credential(
            DEFAULT_CREDENTIAL_REGISTER_URL, config.device_id, config.timeout_seconds
        )
        if reg_credential:
            credential = reg_credential
            save_persistent_device_token(credential)

    # Request and display a pairing code for Android enrollment
    if config.pairing_url:
        pairing_info = request_pairing_code(config.pairing_url, config.device_id, config.timeout_seconds)
        if pairing_info and "code" in pairing_info:
            print("\n==================================================")
            print("Clipboard Sync Desktop Agent")
            print("==================================================")
            print("Pair your Android device using this code:\n")
            print(f"        {pairing_info['code']}\n")
            print("Code expires in 5 minutes.")
            print("==================================================\n")

    monitor: ClipboardMonitor | None = None

    def handle_remote_update(device_id: str, content: str) -> None:
        if monitor is not None:
            pyperclip.copy(content)
            monitor.set_last_content(content)
            logger.info("Updated Windows system clipboard from remote device %s.", device_id)

    def handle_connected() -> None:
        if monitor is not None and config.rest_latest_url:
            content = fetch_latest_clipboard_text(
                rest_latest_url=config.rest_latest_url,
                credential=credential,
                timeout_seconds=config.timeout_seconds,
            )
            if content:
                pyperclip.copy(content)
                monitor.set_last_content(content)
                logger.info("Recovered latest remote clipboard entry on connect (%d chars).", len(content))

    ws_client = ClipboardWebSocketClient(
        ws_url=config.ws_url,
        device_id=config.device_id,
        credential=credential,
        logger=logger,
        on_remote_update=handle_remote_update,
        on_connected=handle_connected,
    )
    monitor = ClipboardMonitor(
        read_clipboard=read_clipboard_text,
        logger=logger,
        interval_seconds=arguments.interval,
        on_text_change=ws_client.send,
    )

    try:
        monitor.run_forever()
    finally:
        ws_client.close()
