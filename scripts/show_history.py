"""Print recent purchases from the local database.

Usage:
    python scripts/show_history.py            # last 20, all assets
    python scripts/show_history.py BTC        # last 20 for BTC
    python scripts/show_history.py BTC 50     # last 50 for BTC
"""

from __future__ import annotations

import asyncio
import sys

from _bootstrap import db_session


async def main(asset: str | None, limit: int) -> int:
    from app.modules.purchases import PurchaseService

    async with db_session():
        purchases = await PurchaseService.list(asset=asset, limit=limit)
        if not purchases:
            print("(no purchases)")
            return 0

        print(
            f"{'id':>4}  {'when':<19}  {'asset':<5}  {'usd':>8}  "
            f"{'size':>14}  {'price':>10}  {'status':<8}"
        )
        for p in purchases:
            print(
                f"{p.id:>4}  {p.created_at.strftime('%Y-%m-%d %H:%M:%S')}  "
                f"{p.asset:<5}  {str(p.usd_amount):>8}  "
                f"{str(p.filled_size or '-'):>14}  "
                f"{str(p.avg_price or '-'):>10}  {p.status:<8}"
            )
    return 0


if __name__ == "__main__":
    asset_arg = sys.argv[1] if len(sys.argv) > 1 else None
    limit_arg = int(sys.argv[2]) if len(sys.argv) > 2 else 20
    sys.exit(asyncio.run(main(asset_arg, limit_arg)))
