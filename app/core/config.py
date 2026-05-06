"""Centralized application configuration via pydantic-settings.

Loads from `environment/.env` by default; override path via the `ENV_FILE`
environment variable (used by tests to point at fixtures or to skip).
"""

from __future__ import annotations

import os
from decimal import Decimal
from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ENV_FILE = PROJECT_ROOT / "environment" / ".env"


class Settings(BaseSettings):
    """Application settings.

    Per-asset DCA plans (e.g. `DCA_BTC_USD_AMOUNT`, `DCA_BTC_USD_CRON`) are
    resolved at runtime by `app.utils.parsers.parse_dca_plans` because their
    keys are dynamic. They are therefore not declared as fields here.
    """

    model_config = SettingsConfigDict(
        env_file=os.getenv("ENV_FILE", str(DEFAULT_ENV_FILE)),
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    coinbase_api_key: str = ""
    coinbase_api_secret: str = ""

    dry_run: bool = True
    database_url: str = "sqlite://data/dca.db"
    timezone: str = "America/New_York"
    log_level: str = "INFO"

    dca_daily_cap_usd: Decimal = Decimal("100")

    @property
    def is_live(self) -> bool:
        return not self.dry_run


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Cached accessor for application settings."""

    return Settings()


def reload_settings() -> Settings:
    """Force a fresh read from the environment (useful for tests)."""

    get_settings.cache_clear()
    return get_settings()
