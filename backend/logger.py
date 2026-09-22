"""Logging setup for XMDeck daemon and Decky Loader runtime."""

from __future__ import annotations

import logging
import os
import sys

# Attempt importing Decky runtime module
try:
    import decky

    _decky_logger: logging.Logger | None = getattr(decky, "logger", None)
except ImportError:
    try:
        import decky_plugin as decky  # type: ignore[import-not-found,no-redef]

        _decky_logger = getattr(decky, "logger", None)
    except ImportError:
        decky = None  # type: ignore[assignment]
        _decky_logger = None

logger = logging.getLogger("xmdeck")
logger.setLevel(logging.DEBUG)


def setup_logging() -> None:
    """Initialize file, console, and Decky handlers for XMDeck logging."""
    if logger.handlers:
        return

    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console / stdout handler for journalctl capture
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(logging.INFO)
    logger.addHandler(console_handler)

    # Determine log destination directory
    candidate_dirs: list[str] = [
        os.environ.get("DECKY_PLUGIN_LOG_DIR", ""),
        "/home/deck/homebrew/logs/XMDeck",
        os.path.expanduser("~/.local/share/decky/logs/XMDeck"),
        "/tmp",
    ]

    for log_dir in candidate_dirs:
        if not log_dir:
            continue
        try:
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, "plugin.log")
            file_handler = logging.FileHandler(log_file, encoding="utf-8")
            file_handler.setFormatter(formatter)
            file_handler.setLevel(logging.DEBUG)
            logger.addHandler(file_handler)
            logger.info("XMDeck logging initialized at %s", log_file)
            break
        except (OSError, PermissionError):
            continue


# Run initialization on import
setup_logging()
