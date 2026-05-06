"""Core DCA orchestration: validate -> cap check -> Coinbase buy -> persist."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from decimal import Decimal

from app.core.config import Settings, get_settings
from app.core.exceptions import CapExceededError, CoinbaseError
from app.models import Purchase, PurchaseStatus
from app.modules.coinbase import CoinbaseClient, CoinbaseService
from app.modules.purchases import PurchaseService
from app.utils.parsers import find_plan, parse_dca_plans
from app.utils.validators import asset_to_product_id, validate_amount


logger = logging.getLogger(__name__)


def _build_client_order_id(asset: str, now: datetime | None = None) -> str:
    moment = now or datetime.now(timezone.utc)
    return f"{asset.upper()}-{moment.strftime('%Y%m%d%H%M')}"


class DCAService:
    """Executes a single DCA buy and persists the result."""

    @classmethod
    async def execute_buy(
        cls,
        asset: str,
        usd: Decimal | None = None,
        *,
        client: CoinbaseClient | None = None,
        settings: Settings | None = None,
    ) -> Purchase:
        """Execute a single buy.

        ``client`` and ``settings`` are accepted for explicit injection (used
        by tests and CLI scripts). When omitted they are resolved from the
        application's cached settings; the scheduler passes its own client
        explicitly so it does not depend on FastAPI lifespans.
        """

        settings = settings or get_settings()
        if client is None:
            client = CoinbaseClient(
                api_key=settings.coinbase_api_key,
                api_secret=settings.coinbase_api_secret,
                dry_run=settings.dry_run,
            )

        normalized_asset = asset.strip().upper()
        product_id = asset_to_product_id(normalized_asset)

        if usd is None:
            plans = parse_dca_plans()
            plan = find_plan(normalized_asset, plans)
            if plan is None:
                raise CoinbaseError(
                    f"No amount provided and no DCA plan configured for {normalized_asset}."
                )
            usd = plan.amount

        usd = validate_amount(Decimal(usd))

        cap = settings.dca_daily_cap_usd
        if cap is not None and cap > 0:
            spent_today = await PurchaseService.daily_total_usd(normalized_asset)
            if spent_today + usd > cap:
                raise CapExceededError(
                    f"Daily cap exceeded for {normalized_asset}: "
                    f"already spent ${spent_today}, attempted ${usd}, cap ${cap}."
                )

        client_order_id = _build_client_order_id(normalized_asset)

        try:
            result = await CoinbaseService.place_market_buy(
                client=client,
                asset=normalized_asset,
                usd=usd,
                client_order_id=client_order_id,
            )
        except Exception as exc:  # noqa: BLE001
            logger.exception("Buy failed for %s $%s", normalized_asset, usd)
            await PurchaseService.create(
                asset=normalized_asset,
                product_id=product_id,
                usd_amount=usd,
                client_order_id=client_order_id,
                status=PurchaseStatus.FAILED,
                error=str(exc),
            )
            if isinstance(exc, CoinbaseError):
                raise
            raise CoinbaseError(str(exc)) from exc

        status = PurchaseStatus.DRY_RUN if result.get("dry_run") else PurchaseStatus.FILLED

        purchase = await PurchaseService.create(
            asset=normalized_asset,
            product_id=product_id,
            usd_amount=usd,
            client_order_id=client_order_id,
            status=status,
            filled_size=result.get("filled_size"),
            avg_price=result.get("avg_price"),
            fees_usd=result.get("fees_usd"),
            order_id=result.get("order_id"),
            raw_response=_jsonable(result.get("raw")),
        )

        logger.info(
            "Buy recorded: id=%s asset=%s usd=%s size=%s price=%s status=%s",
            purchase.id,
            normalized_asset,
            usd,
            purchase.filled_size,
            purchase.avg_price,
            purchase.status,
        )
        return purchase


def _jsonable(value):
    """Coerce Decimals (and nested) into JSON-serializable types."""

    if value is None:
        return None
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: _jsonable(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_jsonable(v) for v in value]
    return value
