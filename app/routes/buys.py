"""Manual buy trigger endpoint."""

from __future__ import annotations

from decimal import Decimal

from fastapi import APIRouter, Query, Request

from app.modules.coinbase import CoinbaseClient
from app.modules.dca import DCAService
from app.schemas.common import AssetSymbol
from app.schemas.purchase import PurchaseOut


router = APIRouter(tags=["buys"])


@router.post("/buy/{asset}", response_model=PurchaseOut, status_code=201)
async def buy_asset(
    asset: AssetSymbol,
    request: Request,
    amount: Decimal | None = Query(
        default=None,
        gt=0,
        description="USD amount to spend. Defaults to the configured plan amount.",
    ),
    live: bool = Query(
        default=False,
        description="Set true to place a live buy, even if DRY_RUN=true.",
    ),
) -> PurchaseOut:
    settings = request.app.state.settings
    client = request.app.state.coinbase
    if live and client.dry_run:
        client = CoinbaseClient(
            api_key=settings.coinbase_api_key,
            api_secret=settings.coinbase_api_secret,
            dry_run=False,
        )

    purchase = await DCAService.execute_buy(
        asset=asset.value,
        usd=amount,
        client=client,
        settings=settings,
    )
    return PurchaseOut.model_validate(purchase)
