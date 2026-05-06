"""High-level orchestration over `CoinbaseClient`.

Routes and other services should depend on this rather than the raw client.
"""

from __future__ import annotations

import logging
from decimal import Decimal
from typing import Any

from app.core.exceptions import CoinbaseError
from app.modules.coinbase.client import CoinbaseClient
from app.utils.validators import asset_to_product_id


logger = logging.getLogger(__name__)


class CoinbaseService:
    """High-level Coinbase operations used by routes/services."""

    @staticmethod
    async def place_market_buy(
        client: CoinbaseClient,
        asset: str,
        usd: Decimal,
        client_order_id: str,
    ) -> dict[str, Any]:
        product_id = asset_to_product_id(asset)
        return await client.market_buy(
            product_id=product_id,
            usd=usd,
            client_order_id=client_order_id,
        )

    @staticmethod
    async def get_ticker_price(client: CoinbaseClient, asset: str) -> Decimal:
        product_id = asset_to_product_id(asset)
        return await client.get_ticker_price(product_id)

    @staticmethod
    async def get_balances(client: CoinbaseClient) -> list[dict[str, Any]]:
        """Return a normalized list of account balances.

        In DRY_RUN we return an empty list (no auth available).
        Each entry has shape: {"asset": str, "available": Decimal, "hold": Decimal}.
        """

        if client.dry_run:
            logger.debug("get_balances called in DRY_RUN mode; returning [].")
            return []

        try:
            accounts = await client.get_accounts()
        except Exception as exc:  # noqa: BLE001
            raise CoinbaseError(f"get_accounts failed: {exc}") from exc

        balances: list[dict[str, Any]] = []
        for account in accounts:
            currency = account.get("currency") or account.get("asset")
            available_value = (account.get("available_balance") or {}).get("value")
            hold_value = (account.get("hold") or {}).get("value")
            if not currency:
                continue
            balances.append(
                {
                    "asset": currency,
                    "available": Decimal(str(available_value or "0")),
                    "hold": Decimal(str(hold_value or "0")),
                }
            )
        return balances
