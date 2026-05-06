"""FastAPI application factory + lifespan."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from tortoise import Tortoise

from app.core.config import Settings, get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging


logger = logging.getLogger(__name__)

TORTOISE_MODELS = ["app.models"]


def _resolve_db_url(settings: Settings) -> str:
    """Tortoise expects URLs like `sqlite://path/to.db`. We accept either
    `sqlite://...` or `sqlite:///...` in env (the latter is SQLAlchemy-style)
    and normalize for Tortoise.
    """

    url = settings.database_url
    if url.startswith("sqlite:///"):
        return "sqlite://" + url[len("sqlite:///") :]
    return url


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = get_settings()

    db_url = _resolve_db_url(settings)
    logger.info("Initializing Tortoise ORM (%s)", db_url)
    await Tortoise.init(db_url=db_url, modules={"models": TORTOISE_MODELS})
    await Tortoise.generate_schemas(safe=True)

    # Lazy imports to avoid circulars during module loading.
    from app.modules.coinbase.client import CoinbaseClient
    from app.modules.scheduler.service import SchedulerService
    from app.utils.parsers import parse_dca_plans

    app.state.settings = settings
    app.state.coinbase = CoinbaseClient(
        api_key=settings.coinbase_api_key,
        api_secret=settings.coinbase_api_secret,
        dry_run=settings.dry_run,
    )

    plans = parse_dca_plans()
    app.state.plans = plans
    app.state.scheduler = SchedulerService(settings, client=app.state.coinbase)
    app.state.scheduler.register_jobs(plans)
    app.state.scheduler.start()

    logger.info(
        "DCA bot started (dry_run=%s, plans=%s)",
        settings.dry_run,
        [p.asset for p in plans],
    )

    try:
        yield
    finally:
        logger.info("Shutting down DCA bot")
        try:
            app.state.scheduler.shutdown()
        except Exception:  # noqa: BLE001
            logger.exception("Scheduler shutdown failed")
        await Tortoise.close_connections()


def create_app() -> FastAPI:
    """Application factory."""

    settings = get_settings()
    configure_logging(settings)

    app = FastAPI(
        title="DCA Crypto Bot",
        description=(
            "A simple DCA bot for BTC/ETH/SOL on the Coinbase Advanced API."
        ),
        version="0.1.0",
        lifespan=lifespan,
    )

    register_exception_handlers(app)

    from app.routes import api_router

    app.include_router(api_router)

    return app
