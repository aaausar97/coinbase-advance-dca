"""Smoke tests for HTTP routes."""

from __future__ import annotations

from decimal import Decimal

import pytest
from httpx import ASGITransport, AsyncClient

from app.core.config import get_settings
from app.modules.dca import service as dca_service_module
from app.utils.parsers import Plan


pytestmark = pytest.mark.asyncio


async def test_health_route(init_db, fake_client):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["status"] == "ok"
    assert payload["dry_run"] is True
    assert "BTC" in payload["active_assets"]


async def test_buy_route_dry_run(init_db, fake_client, monkeypatch):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/buy/BTC", params={"amount": "5"})
        assert resp.status_code == 201, resp.text
        body = resp.json()
        assert body["asset"] == "BTC"
        assert body["status"] == "dry_run"
        assert Decimal(body["usd_amount"]) == Decimal("5")

        history = await client.get("/history?asset=BTC")
        assert history.status_code == 200
        history_body = history.json()
        assert history_body["count"] == 1
        assert history_body["items"][0]["asset"] == "BTC"


async def test_buy_route_rejects_non_enum_asset(init_db, fake_client):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/buy/DOGE", params={"amount": "5"})
    assert resp.status_code == 422


async def test_balances_route_includes_simulated_dry_run_holdings(init_db, fake_client):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        buy = await client.post("/buy/BTC", params={"amount": "5"})
        assert buy.status_code == 201, buy.text

        balances = await client.get("/balances")
        assert balances.status_code == 200, balances.text
        body = balances.json()
        assert body["dry_run"] is True
        assert body["balances"][0]["asset"] == "BTC"
        assert Decimal(body["balances"][0]["available"]) > Decimal("0")


async def test_balances_route_allows_live_override_from_query(
    init_db, fake_client, monkeypatch
):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router
    from app.routes import balances as balances_route

    class LiveClientStub:
        def __init__(self, api_key: str, api_secret: str, dry_run: bool) -> None:
            assert dry_run is False
            self.dry_run = False

        async def get_accounts(self):
            return [
                {
                    "currency": "BTC",
                    "available_balance": {"value": "0.50"},
                    "hold": {"value": "0.10"},
                }
            ]

    monkeypatch.setattr(balances_route, "CoinbaseClient", LiveClientStub)

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/balances", params={"live": "true"})
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["dry_run"] is False
    assert payload["balances"][0]["asset"] == "BTC"
    assert Decimal(payload["balances"][0]["available"]) == Decimal("0.50")


async def test_buy_route_allows_live_override_from_query(
    init_db, fake_client, monkeypatch
):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router
    from app.routes import buys as buys_route

    class LiveClientStub:
        def __init__(self, api_key: str, api_secret: str, dry_run: bool) -> None:
            assert dry_run is False
            self.dry_run = False

        async def market_buy(self, product_id, usd, client_order_id):
            size = (Decimal(usd) / Decimal("50000")).quantize(Decimal("0.000000000001"))
            return {
                "success": True,
                "dry_run": False,
                "order_id": "live-order-1",
                "filled_size": size,
                "avg_price": Decimal("50000"),
                "fees_usd": Decimal("1.25"),
                "raw": {"fake_live": True},
            }

    monkeypatch.setattr(buys_route, "CoinbaseClient", LiveClientStub)

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post("/buy/BTC", params={"amount": "5", "live": "true"})
    assert resp.status_code == 201, resp.text
    payload = resp.json()
    assert payload["status"] == "filled"
    assert payload["order_id"] == "live-order-1"


async def test_history_route_can_filter_dry_run_vs_live(init_db, fake_client, monkeypatch):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router
    from app.routes import buys as buys_route

    class LiveClientStub:
        def __init__(self, api_key: str, api_secret: str, dry_run: bool) -> None:
            assert dry_run is False
            self.dry_run = False

        async def market_buy(self, product_id, usd, client_order_id):
            size = (Decimal(usd) / Decimal("50000")).quantize(Decimal("0.000000000001"))
            return {
                "success": True,
                "dry_run": False,
                "order_id": "live-order-2",
                "filled_size": size,
                "avg_price": Decimal("50000"),
                "fees_usd": Decimal("1.25"),
                "raw": {"fake_live": True},
            }

    monkeypatch.setattr(buys_route, "CoinbaseClient", LiveClientStub)

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        dry = await client.post("/buy/BTC", params={"amount": "5"})
        live = await client.post("/buy/BTC", params={"amount": "5", "live": "true"})
        assert dry.status_code == 201, dry.text
        assert live.status_code == 201, live.text

        dry_history = await client.get("/history", params={"mode": "dry_run"})
        live_history = await client.get("/history", params={"mode": "live"})
        all_history = await client.get("/history", params={"mode": "all"})

    assert dry_history.status_code == 200, dry_history.text
    assert live_history.status_code == 200, live_history.text
    assert all_history.status_code == 200, all_history.text
    assert dry_history.json()["count"] == 1
    assert live_history.json()["count"] == 1
    assert all_history.json()["count"] == 2
    assert dry_history.json()["items"][0]["status"] == "dry_run"
    assert live_history.json()["items"][0]["status"] == "filled"


async def test_history_route_rejects_non_enum_asset(init_db, fake_client):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/history", params={"asset": "DOGE"})
    assert resp.status_code == 422


async def test_balances_route_can_order_by_usd_value(init_db, fake_client, monkeypatch):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router
    from app.routes import balances as balances_route

    async def _mock_price(product_id: str):
        prices = {"BTC-USD": Decimal("50000"), "ETH-USD": Decimal("4000")}
        if product_id not in prices:
            raise RuntimeError("unsupported product")
        return prices[product_id]

    monkeypatch.setattr(fake_client, "get_ticker_price", _mock_price)

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        btc = await client.post("/buy/BTC", params={"amount": "5"})
        eth = await client.post("/buy/ETH", params={"amount": "20"})
        assert btc.status_code == 201, btc.text
        assert eth.status_code == 201, eth.text

        balances = await client.get("/balances", params={"order_by": "usd_value"})
        assert balances.status_code == 200, balances.text
        payload = balances.json()
        usd_values = [Decimal(entry["usd_value"]) for entry in payload["balances"]]
        assert usd_values == sorted(usd_values, reverse=True)


async def test_balances_route_defaults_to_core_assets_only(init_db, fake_client, monkeypatch):
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router
    from app.routes import balances as balances_route

    class LiveClientStub:
        def __init__(self, api_key: str, api_secret: str, dry_run: bool) -> None:
            assert dry_run is False
            self.dry_run = False

        async def get_accounts(self):
            return [
                {
                    "currency": "BTC",
                    "available_balance": {"value": "0.10"},
                    "hold": {"value": "0"},
                },
                {
                    "currency": "USDC",
                    "available_balance": {"value": "3"},
                    "hold": {"value": "0"},
                },
                {
                    "currency": "ANKR",
                    "available_balance": {"value": "25"},
                    "hold": {"value": "0"},
                },
            ]

        async def get_ticker_price(self, product_id: str):
            prices = {"BTC-USD": Decimal("50000"), "ANKR-USD": Decimal("0.03")}
            return prices[product_id]

    monkeypatch.setattr(balances_route, "CoinbaseClient", LiveClientStub)

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        default_balances = await client.get("/balances", params={"live": "true"})
        assert default_balances.status_code == 200, default_balances.text
        default_assets = {entry["asset"] for entry in default_balances.json()["balances"]}
        assert default_assets == {"BTC", "USDC"}

        full_balances = await client.get(
            "/balances",
            params={"live": "true", "full_portfolio": "true"},
        )
        assert full_balances.status_code == 200, full_balances.text
        full_assets = {entry["asset"] for entry in full_balances.json()["balances"]}
        assert full_assets == {"BTC", "USDC", "ANKR"}


# ---------- Fee Comparison Analytics ----------


async def test_fees_comparison_returns_correct_structure(init_db, fake_client):
    """Endpoint returns well-formed response even with zero purchases."""
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/analytics/fees-comparison")
    assert resp.status_code == 200
    body = resp.json()
    assert body["assumptions"]["recurring_buy_fee_rate"] == "0.0149"
    assert body["granularity"] == "month"
    assert body["series"] == []
    assert body["totals"]["usd_invested"] == "0"
    assert body["totals"]["total_savings_usd"] == "0"


async def test_fees_comparison_math_with_purchases(init_db, fake_client):
    """Verify per-period and cumulative savings math against known values."""
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.models import Purchase
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    await Purchase.create(
        asset="BTC",
        product_id="BTC-USD",
        usd_amount=Decimal("100"),
        client_order_id="test-order-1",
        status="filled",
        fees_usd=Decimal("0.60"),
        filled_size=Decimal("0.002"),
        avg_price=Decimal("50000"),
    )
    await Purchase.create(
        asset="BTC",
        product_id="BTC-USD",
        usd_amount=Decimal("200"),
        client_order_id="test-order-2",
        status="filled",
        fees_usd=Decimal("1.20"),
        filled_size=Decimal("0.004"),
        avg_price=Decimal("50000"),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/analytics/fees-comparison", params={"granularity": "day"})
    assert resp.status_code == 200
    body = resp.json()

    totals = body["totals"]
    assert Decimal(totals["usd_invested"]) == Decimal("300")
    assert Decimal(totals["actual_fees_usd"]) == Decimal("1.80")
    expected_recurring = Decimal("300") * Decimal("0.0149")
    assert Decimal(totals["recurring_fees_usd"]) == expected_recurring
    assert Decimal(totals["total_savings_usd"]) == expected_recurring - Decimal("1.80")


async def test_fees_comparison_filters_by_asset(init_db, fake_client):
    """Asset filter narrows results to only the requested asset."""
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.models import Purchase
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    await Purchase.create(
        asset="BTC",
        product_id="BTC-USD",
        usd_amount=Decimal("50"),
        client_order_id="btc-order-1",
        status="filled",
        fees_usd=Decimal("0.30"),
        filled_size=Decimal("0.001"),
        avg_price=Decimal("50000"),
    )
    await Purchase.create(
        asset="ETH",
        product_id="ETH-USD",
        usd_amount=Decimal("80"),
        client_order_id="eth-order-1",
        status="filled",
        fees_usd=Decimal("0.48"),
        filled_size=Decimal("0.02"),
        avg_price=Decimal("4000"),
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/analytics/fees-comparison", params={"asset": "BTC"})
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["totals"]["usd_invested"]) == Decimal("50")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp_all = await client.get("/analytics/fees-comparison")
    assert Decimal(resp_all.json()["totals"]["usd_invested"]) == Decimal("130")


async def test_fees_comparison_excludes_failed_purchases(init_db, fake_client):
    """Failed purchases are not included in fee comparison data."""
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.models import Purchase
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    await Purchase.create(
        asset="BTC",
        product_id="BTC-USD",
        usd_amount=Decimal("100"),
        client_order_id="good-order",
        status="filled",
        fees_usd=Decimal("0.60"),
        filled_size=Decimal("0.002"),
        avg_price=Decimal("50000"),
    )
    await Purchase.create(
        asset="BTC",
        product_id="BTC-USD",
        usd_amount=Decimal("100"),
        client_order_id="bad-order",
        status="failed",
        fees_usd=None,
        error="Insufficient funds",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/analytics/fees-comparison")
    assert resp.status_code == 200
    body = resp.json()
    assert Decimal(body["totals"]["usd_invested"]) == Decimal("100")


async def test_fees_comparison_rejects_invalid_asset(init_db, fake_client):
    """Non-allowlisted asset returns 422."""
    from fastapi import FastAPI

    from app.core.exceptions import register_exception_handlers
    from app.routes import api_router

    app = FastAPI(title="DCA Test")
    app.version = "test"
    app.state.settings = get_settings()
    app.state.coinbase = fake_client
    app.state.plans = [Plan(asset="BTC", product_id="BTC-USD", amount=Decimal("10"), cron="0 9 * * *")]
    app.state.scheduler = None
    register_exception_handlers(app)
    app.include_router(api_router)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/analytics/fees-comparison", params={"asset": "DOGE"})
    assert resp.status_code == 422
