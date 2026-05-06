"""Fee comparison analytics endpoint."""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from fastapi import APIRouter, Query

from app.modules.purchases import PurchaseService
from app.schemas.analytics import FeeComparisonOut
from app.schemas.common import AssetSymbol

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/fees-comparison", response_model=FeeComparisonOut)
async def fees_comparison(
    asset: AssetSymbol | None = Query(
        default=None,
        description="Filter to a single asset (BTC, ETH, SOL). Omit for all.",
    ),
    granularity: Literal["day", "week", "month"] = Query(
        default="month",
        description="Time bucket size for the series.",
    ),
    limit: int = Query(
        default=52,
        ge=1,
        le=520,
        description="Max number of period buckets to return.",
    ),
    since: datetime | None = Query(
        default=None,
        description="Only include purchases on or after this UTC datetime.",
    ),
) -> FeeComparisonOut:
    data = await PurchaseService.fee_comparison(
        asset=asset.value if asset else None,
        granularity=granularity,
        limit=limit,
        since=since,
    )
    return FeeComparisonOut(**data)
