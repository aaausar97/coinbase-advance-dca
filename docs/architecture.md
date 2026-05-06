# Architecture

## Directory layout

```
app/
  core/        application factory, config, exceptions, logging
  models/      Tortoise ORM models
  schemas/     Pydantic request/response models
  routes/      FastAPI route handlers (thin)
  modules/     business logic (one folder per domain)
    coinbase/    SDK wrapper + high-level service
    purchases/   CRUD on the Purchase model
    dca/         orchestrates a single buy
    scheduler/   APScheduler wrapper
  utils/       parsers + validators
environment/   Dockerfile + compose files + .env
scripts/       CLI helpers
tests/         smoke tests
docs/          this folder
data/          SQLite file (mounted as a Docker volume)
```

Key conventions:

- **Routes never touch the DB or the Coinbase SDK directly.** They call services.
- **Services are class-based with classmethods/staticmethods.** No instance state. Settings + clients are passed in or resolved from `app.state`.
- **One Purchase model.** Future strategies (e.g. pool rebalancing) reuse it via the `strategy` column.

## Request flow

```
client request
  -> routes/<resource>.py        (validation, response shaping)
       -> modules/<domain>/service.py   (business logic)
            -> modules/coinbase/{client,service}  (external API)
            -> modules/purchases/service          (DB writes)
```

## Scheduled buy flow

```
APScheduler cron trigger
  -> SchedulerService._run_job(asset)
       -> DCAService.execute_buy(asset)
            -> validators (asset allowlist)
            -> PurchaseService.daily_total_usd (cap check)
            -> CoinbaseService.place_market_buy
                 -> CoinbaseClient.market_buy (DRY_RUN or live)
            -> PurchaseService.create
```

## Future: pool rebalancing

Add `app/modules/pool/service.py`:

```python
class PoolService:
    @classmethod
    async def rebalance(cls, client, settings) -> list[Purchase]:
        # 1. read POOL_TARGETS + POOL_CASH_USD from settings
        # 2. fetch current balances via CoinbaseService.get_balances
        # 3. compute deltas vs targets
        # 4. call CoinbaseService.place_market_buy for each
        # 5. PurchaseService.create(strategy="pool_rebalance", ...)
```

Register a `POOL_CRON` job in `SchedulerService.register_jobs`. No changes to existing models, routes, or core required.