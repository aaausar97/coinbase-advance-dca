"""Parse per-asset DCA plans from environment variables.

Looks for `DCA_<ASSET>_USD_AMOUNT` and `DCA_<ASSET>_USD_CRON` pairs and
returns one `Plan` per supported asset where both are set.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from app.core.exceptions import InvalidPlanError
from app.utils.validators import SUPPORTED_ASSETS


logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class Plan:
    """A single DCA plan resolved from environment variables."""

    asset: str
    product_id: str
    amount: Decimal
    cron: str


def _amount_var(asset: str) -> str:
    return f"DCA_{asset}_USD_AMOUNT"


def _cron_var(asset: str) -> str:
    return f"DCA_{asset}_USD_CRON"


def parse_dca_plans(env: dict[str, str] | None = None) -> list[Plan]:
    """Build a list of plans from the current environment.

    Both `DCA_<ASSET>_USD_AMOUNT` and `DCA_<ASSET>_USD_CRON` must be set for
    the asset to be considered active. Partial configurations raise
    `InvalidPlanError`.
    """

    source = env if env is not None else os.environ
    plans: list[Plan] = []

    for asset, product_id in SUPPORTED_ASSETS.items():
        amount_raw = source.get(_amount_var(asset))
        cron_raw = source.get(_cron_var(asset))

        if amount_raw is None and cron_raw is None:
            continue

        if amount_raw is None or cron_raw is None:
            raise InvalidPlanError(
                f"Plan for {asset} is incomplete: both "
                f"{_amount_var(asset)} and {_cron_var(asset)} must be set."
            )

        try:
            amount = Decimal(str(amount_raw).strip())
        except InvalidOperation as exc:
            raise InvalidPlanError(
                f"{_amount_var(asset)} must be numeric, got '{amount_raw}'."
            ) from exc

        if amount <= 0:
            raise InvalidPlanError(
                f"{_amount_var(asset)} must be positive (got {amount})."
            )

        cron = cron_raw.strip()
        if len(cron.split()) != 5:
            raise InvalidPlanError(
                f"{_cron_var(asset)} must be a 5-field cron expression "
                f"(got '{cron}')."
            )

        plans.append(
            Plan(
                asset=asset,
                product_id=product_id,
                amount=amount,
                cron=cron,
            )
        )

    if not plans:
        logger.warning(
            "No DCA plans configured. Set DCA_<ASSET>_USD_AMOUNT and "
            "DCA_<ASSET>_USD_CRON for at least one asset."
        )

    return plans


def find_plan(asset: str, plans: list[Plan]) -> Plan | None:
    """Return the plan for ``asset`` if present (case-insensitive)."""

    key = asset.strip().upper()
    for plan in plans:
        if plan.asset == key:
            return plan
    return None
