"""CRUD service for `Purchase` records."""

from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Literal

from app.core.exceptions import NotFoundError
from app.models import Purchase, PurchaseStatus

RECURRING_BUY_FEE_RATE = Decimal("0.0149")


class PurchaseService:
    """All Purchase queries / writes are routed through here."""

    @staticmethod
    async def create(
        *,
        asset: str,
        product_id: str,
        usd_amount: Decimal,
        client_order_id: str,
        status: str,
        strategy: str = "dca",
        filled_size: Decimal | None = None,
        avg_price: Decimal | None = None,
        fees_usd: Decimal | None = None,
        order_id: str | None = None,
        error: str | None = None,
        raw_response: dict[str, Any] | None = None,
    ) -> Purchase:
        return await Purchase.create(
            asset=asset.upper(),
            product_id=product_id,
            usd_amount=usd_amount,
            client_order_id=client_order_id,
            status=status,
            strategy=strategy,
            filled_size=filled_size,
            avg_price=avg_price,
            fees_usd=fees_usd,
            order_id=order_id,
            error=error,
            raw_response=raw_response,
        )

    @staticmethod
    async def get(purchase_id: int) -> Purchase:
        purchase = await Purchase.get_or_none(id=purchase_id)
        if purchase is None:
            raise NotFoundError(f"Purchase {purchase_id} not found.")
        return purchase

    @staticmethod
    async def list(
        asset: str | None = None,
        statuses: list[str] | None = None,
        limit: int = 50,
    ) -> list[Purchase]:
        query = Purchase.all().order_by("-created_at")
        if asset:
            query = query.filter(asset=asset.upper())
        if statuses:
            query = query.filter(status__in=statuses)
        return await query.limit(max(1, min(limit, 500)))

    @staticmethod
    async def daily_total_usd(asset: str) -> Decimal:
        """Sum of `usd_amount` for non-failed purchases of `asset` since UTC midnight."""

        start = datetime.now(timezone.utc).replace(
            hour=0, minute=0, second=0, microsecond=0
        )
        purchases = await Purchase.filter(
            asset=asset.upper(),
            created_at__gte=start,
        ).exclude(status="failed")

        total = Decimal("0")
        for purchase in purchases:
            total += Decimal(purchase.usd_amount)
        return total

    @staticmethod
    async def simulated_balances() -> list[dict[str, Decimal | str]]:
        """Aggregate synthetic balances from recorded DRY_RUN purchases."""

        purchases = await Purchase.filter(status=PurchaseStatus.DRY_RUN).exclude(
            filled_size=None
        )
        totals: dict[str, Decimal] = {}
        for purchase in purchases:
            asset = purchase.asset.upper()
            totals.setdefault(asset, Decimal("0"))
            totals[asset] += Decimal(purchase.filled_size)

        return [
            {"asset": asset, "available": amount, "hold": Decimal("0")}
            for asset, amount in sorted(totals.items())
        ]

    @staticmethod
    async def fee_comparison(
        asset: str | None = None,
        granularity: Literal["day", "week", "month"] = "month",
        limit: int = 52,
        since: datetime | None = None,
    ) -> dict[str, Any]:
        """Compare actual Advanced Trade fees vs hypothetical 1.49% recurring-buy fees.

        Returns assumptions, time-bucketed series, and window-level totals.
        """

        query = Purchase.all().exclude(status=PurchaseStatus.FAILED).order_by("created_at")
        if asset:
            query = query.filter(asset=asset.upper())
        if since:
            query = query.filter(created_at__gte=since)

        purchases = await query

        def _bucket_key(dt: datetime) -> str:
            if granularity == "day":
                return dt.strftime("%Y-%m-%d")
            elif granularity == "week":
                iso = dt.isocalendar()
                return f"{iso[0]}-W{iso[1]:02d}"
            else:
                return dt.strftime("%Y-%m")

        buckets: dict[str, dict[str, Decimal]] = defaultdict(
            lambda: {
                "usd_invested": Decimal("0"),
                "actual_fees_usd": Decimal("0"),
                "recurring_fees_usd": Decimal("0"),
            }
        )

        for p in purchases:
            key = _bucket_key(p.created_at)
            usd = Decimal(p.usd_amount)
            buckets[key]["usd_invested"] += usd
            buckets[key]["actual_fees_usd"] += Decimal(p.fees_usd) if p.fees_usd else Decimal("0")
            buckets[key]["recurring_fees_usd"] += usd * RECURRING_BUY_FEE_RATE

        sorted_keys = sorted(buckets.keys())[-limit:]

        series = []
        cumulative_diff = Decimal("0")
        total_invested = Decimal("0")
        total_actual = Decimal("0")
        total_recurring = Decimal("0")

        for key in sorted_keys:
            b = buckets[key]
            period_diff = b["recurring_fees_usd"] - b["actual_fees_usd"]
            cumulative_diff += period_diff
            total_invested += b["usd_invested"]
            total_actual += b["actual_fees_usd"]
            total_recurring += b["recurring_fees_usd"]

            series.append({
                "period": key,
                "usd_invested": b["usd_invested"],
                "actual_fees_usd": b["actual_fees_usd"],
                "recurring_fees_usd": b["recurring_fees_usd"],
                "period_savings_usd": period_diff,
                "cumulative_savings_usd": cumulative_diff,
            })

        return {
            "assumptions": {
                "recurring_buy_fee_rate": RECURRING_BUY_FEE_RATE,
            },
            "granularity": granularity,
            "series": series,
            "totals": {
                "usd_invested": total_invested,
                "actual_fees_usd": total_actual,
                "recurring_fees_usd": total_recurring,
                "total_savings_usd": total_recurring - total_actual,
            },
        }
