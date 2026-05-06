"""Purchase history endpoint."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Query

from app.models import PurchaseStatus
from app.modules.purchases import PurchaseService
from app.schemas.common import AssetSymbol
from app.schemas.purchase import PurchaseListOut, PurchaseOut


router = APIRouter(tags=["history"])


@router.get("/history", response_model=PurchaseListOut)
async def list_history(
    asset: AssetSymbol | None = Query(
        default=None,
        description="Optional asset filter.",
    ),
    mode: Literal["all", "dry_run", "live"] = Query(
        default="all",
        description="Filter to all buys, only dry-run buys, or only live buys.",
    ),
    limit: int = Query(default=50, ge=1, le=500),
) -> PurchaseListOut:
    statuses: list[str] | None = None
    if mode == "dry_run":
        statuses = [PurchaseStatus.DRY_RUN]
    elif mode == "live":
        statuses = [PurchaseStatus.FILLED]

    purchases = await PurchaseService.list(
        asset=asset.value if asset is not None else None,
        statuses=statuses,
        limit=limit,
    )
    items = [PurchaseOut.model_validate(p) for p in purchases]
    return PurchaseListOut(items=items, count=len(items))
