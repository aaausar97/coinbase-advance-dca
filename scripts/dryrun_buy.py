"""Trigger a single (forced) DRY_RUN buy from the CLI.

Usage:
    python scripts/dryrun_buy.py BTC 10
    python scripts/dryrun_buy.py ETH       # uses configured plan amount
"""

from __future__ import annotations

import asyncio
import os
import sys
from decimal import Decimal

from _bootstrap import db_session


async def main(asset: str, usd: Decimal | None) -> int:
    os.environ["DRY_RUN"] = "true"

    from app.core.config import reload_settings
    from app.modules.coinbase import CoinbaseClient
    from app.modules.dca import DCAService

    settings = reload_settings()
    settings.dry_run = True

    async with db_session():
        client = CoinbaseClient(
            api_key=settings.coinbase_api_key,
            api_secret=settings.coinbase_api_secret,
            dry_run=True,
        )
        purchase = await DCAService.execute_buy(
            asset=asset,
            usd=usd,
            client=client,
            settings=settings,
        )
        print(
            f"[DRY_RUN] {purchase.asset} ${purchase.usd_amount} -> "
            f"{purchase.filled_size} @ ${purchase.avg_price} "
            f"(status={purchase.status}, id={purchase.id})"
        )
    return 0


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python scripts/dryrun_buy.py <ASSET> [USD]", file=sys.stderr)
        sys.exit(2)

    asset_arg = sys.argv[1]
    usd_arg: Decimal | None = Decimal(sys.argv[2]) if len(sys.argv) > 2 else None
    sys.exit(asyncio.run(main(asset_arg, usd_arg)))
