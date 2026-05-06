"""Pydantic schemas for analytics endpoints."""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel


class FeeAssumptions(BaseModel):
    recurring_buy_fee_rate: Decimal


class FeeComparisonBucket(BaseModel):
    period: str
    usd_invested: Decimal
    actual_fees_usd: Decimal
    recurring_fees_usd: Decimal
    period_savings_usd: Decimal
    cumulative_savings_usd: Decimal


class FeeComparisonTotals(BaseModel):
    usd_invested: Decimal
    actual_fees_usd: Decimal
    recurring_fees_usd: Decimal
    total_savings_usd: Decimal


class FeeComparisonOut(BaseModel):
    assumptions: FeeAssumptions
    granularity: str
    series: list[FeeComparisonBucket]
    totals: FeeComparisonTotals
