"""Asset allowlist + simple numeric validators."""

from __future__ import annotations

from decimal import Decimal

from app.core.exceptions import InvalidPlanError, UnknownAssetError


SUPPORTED_ASSETS: dict[str, str] = {
    "BTC": "BTC-USD",
    "ETH": "ETH-USD",
    "SOL": "SOL-USD",
    "USDC": "USDC-USD"
}


def asset_to_product_id(asset: str) -> str:
    """Normalize an asset symbol (e.g. ``btc``) to its Coinbase product id."""

    key = asset.strip().upper()
    if key not in SUPPORTED_ASSETS:
        raise UnknownAssetError(
            f"Unsupported asset '{asset}'. Allowed: {sorted(SUPPORTED_ASSETS)}"
        )
    return SUPPORTED_ASSETS[key]


def validate_amount(amount: Decimal) -> Decimal:
    """Coerce + sanity-check a USD amount."""

    if amount is None:
        raise InvalidPlanError("Amount is required.")
    value = Decimal(amount)
    if value <= 0:
        raise InvalidPlanError("Amount must be positive.")
    if value > Decimal("100000"):
        raise InvalidPlanError("Amount exceeds sanity ceiling of $100,000.")
    return value
