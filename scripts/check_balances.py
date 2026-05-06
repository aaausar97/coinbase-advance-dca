"""Print Coinbase account balances.

Usage:
    python scripts/check_balances.py

Note: requires DRY_RUN=false and valid API keys to fetch real balances.
"""

from __future__ import annotations

import asyncio
import sys

from _bootstrap import db_session


async def main() -> int:
    from app.core.config import get_settings
    from app.modules.coinbase import CoinbaseClient, CoinbaseService

    async with db_session():
        settings = get_settings()
        client = CoinbaseClient(
            api_key=settings.coinbase_api_key,
            api_secret=settings.coinbase_api_secret,
            dry_run=settings.dry_run,
        )
        if client.dry_run:
            print(
                "DRY_RUN is enabled; balances are unavailable. "
                "Set DRY_RUN=false to fetch live balances."
            )
            return 0

        balances = await CoinbaseService.get_balances(client)
        if not balances:
            print("(no balances)")
            return 0

        print(f"{'asset':<8}  {'available':>20}  {'hold':>20}")
        for entry in balances:
            print(
                f"{entry['asset']:<8}  {str(entry['available']):>20}  "
                f"{str(entry['hold']):>20}"
            )
    return 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
