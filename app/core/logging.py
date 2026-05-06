"""Logging configuration."""

from __future__ import annotations

import logging
import sys

from app.core.config import Settings


def configure_logging(settings: Settings) -> None:
    """Configure root logger with a sensible format and level from settings."""

    root = logging.getLogger()
    if root.handlers:
        return

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        logging.Formatter(
            fmt="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
    )
    root.addHandler(handler)
    root.setLevel(settings.log_level.upper())

    logging.getLogger("apscheduler").setLevel("INFO")
    logging.getLogger("tortoise").setLevel("WARNING")
    logging.getLogger("uvicorn.access").setLevel("INFO")
