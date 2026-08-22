"""Command-line entry point for the desktop clipboard agent."""

from __future__ import annotations

import argparse
import logging

import pyperclip

from clipboard_agent.config import load_config
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


def main() -> None:
    """Run the local clipboard monitoring loop."""
    arguments = parse_arguments()
    logger = configure_logging()
    try:
        config = load_config()
    except ValueError as error:
        logger.error("Invalid desktop-agent configuration: %s", error)
        return

    ws_client = ClipboardWebSocketClient(
        ws_url=config.ws_url,
        device_id=config.device_id,
        logger=logger,
    )
    try:
        ClipboardMonitor(
            read_clipboard=read_clipboard_text,
            logger=logger,
            interval_seconds=arguments.interval,
            on_text_change=ws_client.send,
        ).run_forever()
    finally:
        ws_client.close()
