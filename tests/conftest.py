"""Test fixtures: in-memory Tortoise DB + a fake Coinbase client."""

from __future__ import annotations

import os
import sys
import uuid
from decimal import Decimal
from pathlib import Path

import pytest
import pytest_asyncio


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Make sure config doesn't try to load a real .env during tests.
os.environ.setdefault("ENV_FILE", "/dev/null")
os.environ.setdefault("DRY_RUN", "true")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("DCA_DAILY_CAP_USD", "100")
# Default plan amounts for tests; routes/services may override at runtime.
os.environ.setdefault("DCA_BTC_USD_AMOUNT", "10")
os.environ.setdefault("DCA_BTC_USD_CRON", "0 9 * * *")


pytestmark = pytest.mark.asyncio


class FakeCoinbaseClient:
    """A drop-in `CoinbaseClient` substitute for tests."""

    def __init__(self, price: Decimal = Decimal("50000")) -> None:
        self.dry_run = True
        self._price = price
        self.calls: list[dict] = []

    async def get_ticker_price(self, product_id: str) -> Decimal:
        return self._price

    async def market_buy(self, product_id, usd, client_order_id):
        self.calls.append(
            {
                "product_id": product_id,
                "usd": Decimal(usd),
                "client_order_id": client_order_id,
            }
        )
        size = (Decimal(usd) / self._price).quantize(Decimal("0.000000000001"))
        return {
            "success": True,
            "dry_run": True,
            "order_id": f"fake-{uuid.uuid4()}",
            "filled_size": size,
            "avg_price": self._price,
            "fees_usd": Decimal("0"),
            "raw": {"fake": True},
        }

    async def get_accounts(self):
        return []

    async def get_fills(self, order_id):
        return {"fills": []}


@pytest_asyncio.fixture
async def init_db():
    from tortoise import Tortoise

    await Tortoise.init(
        db_url="sqlite://:memory:",
        modules={"models": ["app.models"]},
    )
    await Tortoise.generate_schemas()
    try:
        yield
    finally:
        await Tortoise.close_connections()


@pytest.fixture
def fake_client() -> FakeCoinbaseClient:
    return FakeCoinbaseClient()


@pytest.fixture
def fresh_settings(monkeypatch):
    """Reload settings each test to pick up monkeypatched env vars."""

    from app.core.config import reload_settings

    return reload_settings()
