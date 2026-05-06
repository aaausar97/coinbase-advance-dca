"""Smoke tests for DCAService."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.core.exceptions import CapExceededError, UnknownAssetError
from app.modules.dca import DCAService
from app.modules.purchases import PurchaseService


pytestmark = pytest.mark.asyncio


async def test_execute_buy_happy_path(init_db, fake_client, fresh_settings):
    purchase = await DCAService.execute_buy(
        asset="BTC",
        usd=Decimal("10"),
        client=fake_client,
        settings=fresh_settings,
    )

    assert purchase.id is not None
    assert purchase.asset == "BTC"
    assert purchase.product_id == "BTC-USD"
    assert Decimal(purchase.usd_amount) == Decimal("10")
    assert purchase.status == "dry_run"
    assert purchase.filled_size > 0
    assert len(fake_client.calls) == 1


async def test_execute_buy_unknown_asset_raises(init_db, fake_client, fresh_settings):
    with pytest.raises(UnknownAssetError):
        await DCAService.execute_buy(
            asset="DOGE",
            usd=Decimal("10"),
            client=fake_client,
            settings=fresh_settings,
        )


async def test_execute_buy_cap_exceeded(init_db, fake_client, fresh_settings, monkeypatch):
    monkeypatch.setattr(fresh_settings, "dca_daily_cap_usd", Decimal("15"))

    await DCAService.execute_buy(
        asset="BTC",
        usd=Decimal("10"),
        client=fake_client,
        settings=fresh_settings,
    )

    with pytest.raises(CapExceededError):
        await DCAService.execute_buy(
            asset="BTC",
            usd=Decimal("10"),
            client=fake_client,
            settings=fresh_settings,
        )

    history = await PurchaseService.list(asset="BTC", limit=10)
    assert len(history) == 1
