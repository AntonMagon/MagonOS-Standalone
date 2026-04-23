# Deployment

## Production truth

The standalone VPS/server path is the foundation compose contour only:

- `db` - PostgreSQL
- `redis` - Redis
- `api` - FastAPI foundation app
- `worker` - Celery worker
- `web` - production Next.js app
- `caddy` - reverse proxy on `:3000`

Old gunicorn/WSGI/SQLite deploy paths are not the current production contract.

## Required setup

1. Copy the production env template:

```bash
cd /Users/anton/Desktop/MagonOS-Standalone
cp .env.prod.example .env.prod
```

2. Replace placeholder passwords in `.env.prod`:

- `POSTGRES_PASSWORD`
- `MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD`
- `MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD`
- `MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD`

3. Make sure Docker with Compose is available on the server.

## Canonical commands

Start or update the production contour:

```bash
./scripts/run_deploy.sh
```

Explicit build/start:

```bash
./scripts/run_deploy.sh up --build
```

Status:

```bash
./scripts/run_deploy.sh status
```

Logs:

```bash
./scripts/run_deploy.sh logs --follow api web
```

Restart changed services:

```bash
./scripts/run_deploy.sh restart --build api web worker
```

Stop the contour:

```bash
./scripts/run_deploy.sh down
```

Render resolved config:

```bash
./scripts/run_deploy.sh config --env-file .env.prod
```

## Exposed surfaces

- public shell: `http://<server>:3000/`
- foundation login: `http://<server>:3000/login`
- backend readiness through proxy: `http://<server>:3000/health/ready`
- backend API through proxy prefix: `http://<server>:3000/platform-api/api/v1/...`

## Operational notes

- `scripts/run_deploy.sh` now wraps `docker compose`; it is no longer a gunicorn launcher.
- `Procfile` points at `scripts/run_deploy.sh`, so the default deploy entry stays aligned with the active compose contour.
- Local desktop shell and VPS deploy are intentionally different:
  - local product path: `./Start_Platform.command` or `./scripts/run_foundation_unified.sh`
  - VPS/server path: `./scripts/run_deploy.sh`
- If you need a non-default env file, pass `--env-file /absolute/path/to/.env.prod`.
