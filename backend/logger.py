"""Logging setup for XMDeck daemon and Decky Loader runtime."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler

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


def _get_log_level() -> int:
    """Determine log level from environment variables, defaulting to INFO to reduce SSD wear."""
    if os.environ.get("XMDECK_DEBUG", "").lower() in ("1", "true", "yes"):
        return logging.DEBUG
    level_name = os.environ.get("XMDECK_LOG_LEVEL", "INFO").upper()
    return getattr(logging, level_name, logging.INFO)


logger.setLevel(_get_log_level())


def setup_logging() -> None:
    """Initialize file, console, and Decky handlers for XMDeck logging."""
    if logger.handlers:
        return

    log_level = _get_log_level()

    formatter = logging.Formatter(
        "[%(asctime)s] [%(name)s] [%(levelname)s] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # Console / stdout handler for journalctl capture
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(log_level)
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
            # Limit file size and rotate to cap disk usage and reduce SSD wear
            file_handler = RotatingFileHandler(
                log_file,
                maxBytes=512 * 1024,  # 512 KB cap
                backupCount=1,
                encoding="utf-8",
            )
            file_handler.setFormatter(formatter)
            file_handler.setLevel(log_level)
            logger.addHandler(file_handler)
            logger.info(
                "XMDeck logging initialized at %s (level=%s)",
                log_file,
                logging.getLevelName(log_level),
            )
            break
        except (OSError, PermissionError):
            continue


# Run initialization on import
setup_logging()
