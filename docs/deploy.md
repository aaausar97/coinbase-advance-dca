# Deployment

This bot is designed to run as a single Docker container. The same image is used for development and production — the difference is the compose file.

## Local development (port 8000, hot reload)

```bash
cd environment
cp .env.example .env       # fill in keys, leave DRY_RUN=true while testing
docker compose up --build  # http://localhost:8000
```

`docker-compose.yml` mounts `../app` into the container so editing files on your laptop triggers Uvicorn's `--reload`. The SQLite database lives in `../data/dca.db` on the host.

## Production / VPS / EC2 (port 8001, no reload)

```bash
cd environment
cp .env.example .env       # set DRY_RUN=false when you are ready
docker compose -f docker-compose-deploy.yml up -d --build
```

The deploy compose file:

- exposes `8001` on the host (so it can sit alongside other services on `8000`)
- does NOT mount `../app` (image is the source of truth)
- still mounts `../data` so the SQLite file persists across rebuilds
- uses `restart: unless-stopped` so it survives reboots

To update after a code change:

```bash
cd environment
docker compose -f docker-compose-deploy.yml pull   # if using a registry
docker compose -f docker-compose-deploy.yml up -d --build
```

## Putting it behind a reverse proxy

The bot has no auth — keep it bound to localhost or a private network. Common options:

- **Caddy / nginx** with HTTP basic auth or mTLS in front of port 8001
- **Tailscale** sidecar so the bot is reachable only on your tailnet
- **SSH tunnel** from your laptop: `ssh -L 8001:localhost:8001 user@host`

## Operating

- Logs: `docker compose logs -f dca-bot`
- DB shell: `sqlite3 data/dca.db 'select * from purchases order by created_at desc limit 20;'`
- Manual buy: `curl -X POST http://localhost:8001/buy/BTC?amount=10`
- Update plans: edit `environment/.env`, then `docker compose restart dca-bot`

## Backups

The SQLite database is a single file at `data/dca.db`. Regular file-level backups (rsync, restic, etc.) are sufficient.