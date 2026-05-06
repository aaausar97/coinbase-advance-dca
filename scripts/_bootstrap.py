"""Shared helpers for one-off CLI scripts."""

from __future__ import annotations

import sys
from contextlib import asynccontextmanager
from pathlib import Path

from tortoise import Tortoise


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))


@asynccontextmanager
async def db_session():
    """Init Tortoise for a single CLI run, then close cleanly."""

    from app.core.app import _resolve_db_url, TORTOISE_MODELS
    from app.core.config import get_settings
    from app.core.logging import configure_logging

    settings = get_settings()
    configure_logging(settings)

    db_url = _resolve_db_url(settings)
    await Tortoise.init(db_url=db_url, modules={"models": TORTOISE_MODELS})
    await Tortoise.generate_schemas(safe=True)
    try:
        yield settings
    finally:
        await Tortoise.close_connections()
