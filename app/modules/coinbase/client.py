"""Thin wrapper around the official ``coinbase-advanced-py`` SDK.

The wrapper:
  * Exposes a small async-friendly surface (the SDK is sync, so calls run in
    the default executor).
  * Implements a DRY_RUN mode that fetches the live ticker price from a
    public endpoint (no auth) and simulates a fill, so testing is realistic
    without spending real money.
"""

from __future__ import annotations

import asyncio
import logging
import uuid
from decimal import Decimal
from typing import Any

import httpx

from app.core.exceptions import CoinbaseError


logger = logging.getLogger(__name__)

PUBLIC_TICKER_URL = "https://api.coinbase.com/api/v3/brokerage/market/products/{product_id}/ticker?limit=1"

ADVANCED_TRADE_TAKER_FEE_RATE = Decimal("0.006")


class CoinbaseClient:
    """Lightweight async-friendly wrapper around the Coinbase Advanced SDK."""

    def __init__(self, api_key: str, api_secret: str, dry_run: bool) -> None:
        self.dry_run = dry_run
        self._api_key = api_key
        self._api_secret = api_secret
        self._sdk: Any = None

        if not dry_run:
            try:
                from coinbase.rest import RESTClient
            except ImportError as exc:  # pragma: no cover
                raise CoinbaseError(
                    "coinbase-advanced-py is not installed."
                ) from exc

            if not api_key or not api_secret:
                raise CoinbaseError(
                    "COINBASE_API_KEY and COINBASE_API_SECRET are required "
                    "when DRY_RUN is false."
                )
            self._sdk = RESTClient(api_key=api_key, api_secret=api_secret)

    @staticmethod
    def _to_decimal(value: Any, default: Decimal | None = None) -> Decimal | None:
        if value is None or value == "":
            return default
        try:
            return Decimal(str(value))
        except Exception:  # noqa: BLE001
            return default

    async def get_ticker_price(self, product_id: str) -> Decimal:
        """Return the current best price for ``product_id``."""

        if self._sdk is not None:
            data = await asyncio.to_thread(
                self._sdk.get_product, product_id=product_id
            )
            payload = data.to_dict() if hasattr(data, "to_dict") else dict(data)
            price = self._to_decimal(payload.get("price"))
            if price is None or price <= 0:
                raise CoinbaseError(
                    f"Invalid ticker response for {product_id}: {payload}"
                )
            return price

        async with httpx.AsyncClient(timeout=10.0) as client:
            try:
                resp = await client.get(
                    PUBLIC_TICKER_URL.format(product_id=product_id)
                )
                resp.raise_for_status()
            except httpx.HTTPError as exc:
                raise CoinbaseError(
                    f"Failed to fetch public ticker for {product_id}: {exc}"
                ) from exc

        payload = resp.json()
        trades = payload.get("trades") or []
        price_raw = payload.get("price") or (trades[0].get("price") if trades else None)
        price = self._to_decimal(price_raw)
        if price is None or price <= 0:
            raise CoinbaseError(
                f"Could not parse a price from public ticker for {product_id}: {payload}"
            )
        return price

    async def get_accounts(self) -> list[dict[str, Any]]:
        """Return raw account dicts from the SDK (or empty list in DRY_RUN)."""

        if self._sdk is None:
            return []

        data = await asyncio.to_thread(self._sdk.get_accounts)
        payload = data.to_dict() if hasattr(data, "to_dict") else dict(data)
        return list(payload.get("accounts") or [])

    async def get_fills(self, order_id: str) -> dict[str, Any]:
        if self._sdk is None:
            return {}
        data = await asyncio.to_thread(self._sdk.get_fills, order_id=order_id)
        return data.to_dict() if hasattr(data, "to_dict") else dict(data)

    async def market_buy(
        self,
        product_id: str,
        usd: Decimal,
        client_order_id: str,
    ) -> dict[str, Any]:
        """Place a market buy spending ``usd`` USD on ``product_id``.

        Returns a normalized dict with at least:
          - success: bool
          - order_id: str | None
          - filled_size: Decimal | None
          - avg_price: Decimal | None
          - fees_usd: Decimal | None
          - dry_run: bool
          - raw: original SDK / simulator payload
        """

        if self.dry_run:
            return await self._simulate_market_buy(product_id, usd, client_order_id)

        return await self._live_market_buy(product_id, usd, client_order_id)

    async def _simulate_market_buy(
        self,
        product_id: str,
        usd: Decimal,
        client_order_id: str,
    ) -> dict[str, Any]:
        price = await self.get_ticker_price(product_id)
        estimated_fees = (usd * ADVANCED_TRADE_TAKER_FEE_RATE).quantize(Decimal("0.00000001"))
        effective_usd = usd - estimated_fees
        filled_size = (effective_usd / price).quantize(Decimal("0.000000000001"))
        simulated = {
            "success": True,
            "dry_run": True,
            "order_id": f"dryrun-{uuid.uuid4()}",
            "filled_size": filled_size,
            "avg_price": price,
            "fees_usd": estimated_fees,
            "raw": {
                "simulator": True,
                "product_id": product_id,
                "usd": str(usd),
                "client_order_id": client_order_id,
                "price": str(price),
                "filled_size": str(filled_size),
                "estimated_fees": str(estimated_fees),
            },
        }
        logger.info(
            "DRY_RUN buy: %s $%s @ ~$%s (~%s)",
            product_id,
            usd,
            price,
            filled_size,
        )
        return simulated

    async def _live_market_buy(
        self,
        product_id: str,
        usd: Decimal,
        client_order_id: str,
    ) -> dict[str, Any]:
        logger.info("LIVE buy: %s $%s (client_order_id=%s)", product_id, usd, client_order_id)
        try:
            response = await asyncio.to_thread(
                self._sdk.market_order_buy,
                client_order_id=client_order_id,
                product_id=product_id,
                quote_size=str(usd),
            )
        except Exception as exc:  # noqa: BLE001
            raise CoinbaseError(f"market_order_buy failed: {exc}") from exc

        payload = response.to_dict() if hasattr(response, "to_dict") else dict(response)

        if not payload.get("success"):
            err = payload.get("error_response") or {}
            raise CoinbaseError(
                f"Coinbase rejected order: {err.get('error') or err.get('message') or err}"
            )

        order_id = (payload.get("success_response") or {}).get("order_id")

        filled_size: Decimal | None = None
        avg_price: Decimal | None = None
        fees_usd: Decimal | None = None
        fills_payload: dict[str, Any] = {}
        if order_id:
            await asyncio.sleep(1.0)
            fills_payload = await self.get_fills(order_id)
            fills = fills_payload.get("fills") or []
            if fills:
                total_size = Decimal("0")
                total_value = Decimal("0")
                total_fees = Decimal("0")
                for fill in fills:
                    size = self._to_decimal(fill.get("size"), Decimal("0")) or Decimal("0")
                    price = self._to_decimal(fill.get("price"), Decimal("0")) or Decimal("0")
                    fee = self._to_decimal(fill.get("commission"), Decimal("0")) or Decimal("0")
                    total_size += size
                    total_value += size * price
                    total_fees += fee
                if total_size > 0:
                    filled_size = total_size
                    avg_price = total_value / total_size
                fees_usd = total_fees

        return {
            "success": True,
            "dry_run": False,
            "order_id": order_id,
            "filled_size": filled_size,
            "avg_price": avg_price,
            "fees_usd": fees_usd,
            "raw": {"order": payload, "fills": fills_payload},
        }
