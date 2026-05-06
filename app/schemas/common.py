"""Shared response schemas (health, balances, errors)."""

from __future__ import annotations

from decimal import Decimal
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class AssetSymbol(str, Enum):
    BTC = "BTC"
    ETH = "ETH"
    SOL = "SOL"


class ErrorOut(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    error: ErrorOut


class HealthOut(BaseModel):
    """Returned by `GET /`."""

    status: str = "ok"
    version: str
    dry_run: bool
    timezone: str
    active_assets: list[str] = Field(default_factory=list)


class BalanceOut(BaseModel):
    """Single-asset Coinbase balance entry."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    asset: str
    available: Decimal
    hold: Decimal = Decimal("0")
    usd_value: Decimal | None = None


class BalancesOut(BaseModel):
    balances: list[BalanceOut]
    dry_run: bool
