# DCA Crypto Bot

A simple FastAPI service that places recurring market buys for BTC, ETH, and SOL on the Coinbase Advanced API. Built-in APScheduler runs autonomously; manual API endpoints let you trigger or inspect history. Runs in Docker for both local dev and deployment. Includes a `DRY_RUN` mode for safe testing.



Currently running 24/7 in Dry_Run mode. Plans to launch live and use for first purchases June 1st 2026!

## Quick start (Docker, recommended)

```bash
cd environment
cp .env.example .env       # fill in keys, keep DRY_RUN=true first
docker compose up --build  # http://localhost:8000
```

## Stack

- Python 3.11+, FastAPI, Uvicorn
- Tortoise ORM + aiosqlite (SQLite for v1, Postgres-ready)
- `coinbase-advanced-py` (official SDK)
- APScheduler (`AsyncIOScheduler`)
- pydantic-settings

## Project layout

See [docs/](docs/) for full details. Top-level:

```
app/        # application code (core/models/schemas/routes/modules/utils)
environment/  # Dockerfile + compose files + .env
scripts/    # CLI helpers (dryrun_buy, show_history, check_balances)
tests/      # smoke tests
docs/       # supporting documentation
```

## Configuration

Single `environment/.env` (copy from `environment/.env.example`).

Per-asset DCA plans are configured via env pairs:

```dotenv
DCA_BTC_USD_AMOUNT=10
DCA_BTC_USD_CRON=0 9 * * *      # daily 9am

DCA_ETH_USD_AMOUNT=20
DCA_ETH_USD_CRON=0 9 * * 1      # weekly Mon 9am

DCA_SOL_USD_AMOUNT=5
DCA_SOL_USD_CRON=0 9 1 * *      # monthly 1st 9am
```

An asset is "active" only if both `_AMOUNT` and `_CRON` are set.

## API endpoints

- `GET /` — health + dry-run flag + active plans
- `GET /plans` — configured plans + next-run times
- `POST /buy/{asset}?amount=10&live=true` — manual buy (`live=true` overrides `DRY_RUN` for this request)
- `GET /history?asset=BTC&mode=dry_run&limit=50` — recent purchases (`asset` supports BTC/ETH/SOL; `mode` supports `all`, `dry_run`, `live`)
- `GET /balances?live=true&order_by=usd_value&full_portfolio=true` — balances (defaults to `BTC/ETH/SOL/USD/USDC`; set `full_portfolio=true` to include all non-zero assets; `live=true` fetches real Coinbase balances even if `DRY_RUN=true`; supports sorting by `asset` or `usd_value`)

## Running locally without Docker

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp environment/.env.example environment/.env
uvicorn app.main:app --reload --env-file environment/.env
```

## Documentation

- [docs/coinbase-keys.md](docs/coinbase-keys.md) — provisioning Advanced API keys via the CDP portal
- [docs/cron-cheatsheet.md](docs/cron-cheatsheet.md) — quick cron reference for `DCA_*_CRON` values
- [docs/deploy.md](docs/deploy.md) — Docker deploy on a VPS / EC2
- [docs/architecture.md](docs/architecture.md) — directory layout, request flow, future extensibility

## Safety defaults

- `DRY_RUN=true` in `.env.example`
- Strict asset allowlist (`BTC-USD`, `ETH-USD`, `SOL-USD`)
- Daily USD cap (`DCA_DAILY_CAP_USD=100`)
- Idempotent `client_order_id` (per-minute granularity)

## Testing 

```bash
cd ../environment
docker compose run --rm -v ..:/app -w /app dca-bot python -m pytest -q
```
