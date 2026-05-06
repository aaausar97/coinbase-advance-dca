"""Pydantic schemas for the Purchase resource."""

from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, ConfigDict


class PurchaseCreate(BaseModel):
    """Input shape used internally when persisting a purchase."""

    asset: str
    product_id: str
    usd_amount: Decimal
    client_order_id: str
    status: str
    strategy: str = "dca"
    filled_size: Decimal | None = None
    avg_price: Decimal | None = None
    fees_usd: Decimal | None = None
    order_id: str | None = None
    error: str | None = None
    raw_response: dict[str, Any] | None = None


class PurchaseOut(BaseModel):
    """Public response shape for a purchase record."""

    model_config = ConfigDict(from_attributes=True)

    id: int
    created_at: datetime
    asset: str
    product_id: str
    usd_amount: Decimal
    filled_size: Decimal | None = None
    avg_price: Decimal | None = None
    fees_usd: Decimal | None = None
    order_id: str | None = None
    client_order_id: str
    strategy: str
    status: str
    error: str | None = None


class PurchaseListOut(BaseModel):
    items: list[PurchaseOut]
    count: int
