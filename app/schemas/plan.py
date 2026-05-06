"""Pydantic schemas for DCA plans."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel


class PlanOut(BaseModel):
    """A single DCA plan resolved from environment variables."""

    asset: str
    product_id: str
    amount: Decimal
    cron: str
    next_run_at: datetime | None = None


class PlanListOut(BaseModel):
    plans: list[PlanOut]
    count: int
    dry_run: bool
