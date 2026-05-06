"""Coinbase balances endpoint."""

from __future__ import annotations

import asyncio
from decimal import Decimal
from typing import Literal

from fastapi import APIRouter, Query, Request

from app.modules.coinbase import CoinbaseClient, CoinbaseService
from app.modules.purchases import PurchaseService
from app.schemas.common import BalanceOut, BalancesOut


router = APIRouter(tags=["balances"])
CORE_ASSETS = {"BTC", "ETH", "SOL", "USD", "USDC"}


@router.get("/balances", response_model=BalancesOut)
async def get_balances(
    request: Request,
    live: bool = Query(
        default=False,
        description="Set true to fetch live Coinbase balances, even if DRY_RUN=true.",
    ),
    order_by: Literal["asset", "usd_value"] = Query(
        default="asset",
        description="Sort balances by asset symbol or estimated USD value.",
    ),
    full_portfolio: bool = Query(
        default=False,
        description="Set true to include all non-zero assets in your portfolio.",
    ),
) -> BalancesOut:
    settings = request.app.state.settings
    client = request.app.state.coinbase
    if live and client.dry_run:
        client = CoinbaseClient(
            api_key=settings.coinbase_api_key,
            api_secret=settings.coinbase_api_secret,
            dry_run=False,
        )

    if client.dry_run:
        raw = await PurchaseService.simulated_balances()
    else:
        raw = await CoinbaseService.get_balances(client)

    visible = [
        item
        for item in raw
        if item["available"] > 0
        and (full_portfolio or item["asset"].upper() in CORE_ASSETS)
    ]
    usd_values = await asyncio.gather(
        *[
            _estimate_usd_value(
                client=client,
                asset=item["asset"],
                available=item["available"],
            )
            for item in visible
        ]
    )
    balances = [
        BalanceOut(
            asset=item["asset"],
            available=item["available"],
            hold=item["hold"],
            usd_value=usd_value,
        )
        for item, usd_value in zip(visible, usd_values, strict=True)
    ]
    if order_by == "usd_value":
        balances.sort(
            key=lambda balance: balance.usd_value or Decimal("-1"),
            reverse=True,
        )
    else:
        balances.sort(key=lambda balance: balance.asset)
    return BalancesOut(balances=balances, dry_run=client.dry_run)


async def _estimate_usd_value(
    client: CoinbaseClient,
    asset: str,
    available: Decimal,
) -> Decimal | None:
    if available <= 0:
        return Decimal("0")
    symbol = asset.upper()
    if symbol in {"USD", "USDC"}:
        return available

    price = await _resolve_usd_price(client=client, asset=symbol)
    if price is None:
        return None
    return available * price


async def _resolve_usd_price(client: CoinbaseClient, asset: str) -> Decimal | None:
    # Try direct USD market first, then USDC as a fallback quote currency.
    for quote in ("USD", "USDC"):
        try:
            return await client.get_ticker_price(f"{asset}-{quote}")
        except Exception:  # noqa: BLE001
            continue
    return None
