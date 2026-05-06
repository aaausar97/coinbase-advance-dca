"""Tortoise ORM model for crypto purchases (DCA + future strategies)."""

from __future__ import annotations

from tortoise import fields
from tortoise.models import Model


class PurchaseStatus:
    """Status string constants for the `Purchase.status` column."""

    FILLED = "filled"
    FAILED = "failed"
    DRY_RUN = "dry_run"


class Purchase(Model):
    """Records a single crypto buy attempt (real or simulated)."""

    id = fields.IntField(pk=True)
    created_at = fields.DatetimeField(auto_now_add=True, index=True)

    asset = fields.CharField(max_length=10, index=True)
    product_id = fields.CharField(max_length=20)

    usd_amount = fields.DecimalField(max_digits=18, decimal_places=8)
    filled_size = fields.DecimalField(max_digits=24, decimal_places=12, null=True)
    avg_price = fields.DecimalField(max_digits=18, decimal_places=8, null=True)
    fees_usd = fields.DecimalField(max_digits=18, decimal_places=8, null=True)

    order_id = fields.CharField(max_length=64, null=True, unique=True)
    client_order_id = fields.CharField(max_length=64, index=True)

    strategy = fields.CharField(max_length=32, default="dca")
    status = fields.CharField(max_length=16)
    error = fields.TextField(null=True)
    raw_response = fields.JSONField(null=True)

    class Meta:
        table = "purchases"
        ordering = ["-created_at"]

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return (
            f"<Purchase id={self.id} asset={self.asset} usd={self.usd_amount} "
            f"status={self.status}>"
        )
