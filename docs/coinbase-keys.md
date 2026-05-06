# Provisioning Coinbase Advanced API Keys

This bot uses the **Coinbase Advanced Trade API** (the successor to Coinbase Pro). Coinbase Pro was retired on December 1, 2023 and its API keys can no longer trade. You **must** generate a new key in the Coinbase Developer Platform (CDP) portal.

## Steps

1. Go to [https://portal.cdp.coinbase.com/](https://portal.cdp.coinbase.com/) and sign in with the Coinbase account that holds funds.
2. Navigate to **API Keys** -> **Create API key**.
3. Name the key something memorable (e.g. `dca-bot`).
4. Permissions required (minimum):
  - `View` — read accounts, products, balances
  - `Trade` — place buy orders
  - **Do not** enable `Transfer` unless you want the bot to move funds between portfolios.
5. (Optional but recommended) restrict the key to a portfolio that holds only the funds you want the bot to use.
6. Set an IP allowlist if your bot will run from a stable IP (your home, a VPS, etc.). Skip this if running from rotating IPs.
7. Click **Create & Download**. Coinbase shows the secret only once.

## Where to put them

Coinbase returns two values:

- **API Key Name** — looks like `organizations/<org-id>/apiKeys/<key-id>`
- **Private Key (PEM)** — a multi-line `-----BEGIN EC PRIVATE KEY-----` block

Place them in `environment/.env`:

```dotenv
COINBASE_API_KEY=organizations/abc-123/apiKeys/xyz-789
COINBASE_API_SECRET="-----BEGIN EC PRIVATE KEY-----\nMIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQg...\n-----END EC PRIVATE KEY-----\n"
```

The secret must be a single env-var line. Use `\n` for line breaks (they will be parsed by the SDK). Keep the surrounding double quotes.

## Verify

Start the bot in **DRY_RUN** mode first:

```bash
cd environment
docker compose up --build
```

Then in another terminal:

```bash
curl -X POST http://localhost:8000/buy/BTC?amount=5
curl http://localhost:8000/history
```

You should see a `dry_run` purchase recorded with the live BTC price. When you flip `DRY_RUN=false`, the same call hits Coinbase for real.

## Security tips

- Never commit `environment/.env` to git. (It is already in `.gitignore` and `.dockerignore`.)
- Rotate keys if the file ever leaks.
- Set the daily cap (`DCA_DAILY_CAP_USD`) low while you are testing.
- Keep the bot behind localhost or a private network — there is no auth on the FastAPI endpoints.

