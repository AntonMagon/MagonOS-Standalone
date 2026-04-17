# Runbook: foundation skeleton первой волны

## Что это

Этот runbook описывает новый foundation-контур первой волны:

- FastAPI modular monolith
- PostgreSQL-ready schema через Alembic
- Redis/Celery skeleton
- Caddy/Docker Compose skeleton
- минимальный auth/authz
- базовый audit/health/telemetry
- optional legacy standalone runtime как совместимый mount только по явному opt-in

## Подготовка

```bash
cd /Users/anton/Desktop/MagonOS-Standalone
python3 -m venv .venv
./.venv/bin/pip install -U pip setuptools wheel
./.venv/bin/pip install -e .
```

Для локального web-shell базовая ветка Node должна быть `22.x`.

Если foundation/compose запускается через Docker на macOS с `colima`, по умолчанию поднимай компактный runtime:

```bash
colima start --cpu 2 --memory 2 --disk 20 --vm-type vz
```

Расширяй память только если текущая задача реально упирается в лимит.

## Базовая матрица версий

- web runtime: `Node 22.x`
- web package manager: `npm 10.x`
- api/core runtime: `Python 3.10.x`
- DB: `PostgreSQL 16`
- Redis: `Redis 7`
- Celery: `5.6.x`

Если локальный host новее по Python, это допустимо. Каноничный foundation runtime всё равно должен совпадать с контейнерным слоем и `pyproject.toml`, то есть с веткой `Python 3.10`.

## Подтверждённые версии на живом compose runtime

- `Node v22.22.2`
- `npm 10.9.7`
- `Next 15.5.15`
- `React 19.2.5`
- `Python 3.10.20`
- `FastAPI 0.136.0`
- `SQLAlchemy 2.0.49`
- `Alembic 1.18.4`
- `Celery 5.6.3`
- `redis-py 7.4.0`
- `psycopg 3.3.3`
- `uvicorn 0.44.0`
- `PostgreSQL 16.13`
- `Redis 7.4.8`
- `Caddy 2.8.4`

RU: Политика версий для первой волны сейчас консервативная — не обновлять стек ради самого факта обновления, пока подтверждённый runtime остаётся зелёным и согласованным.

## Подтверждённый ресурсный профиль

- Текущий профиль `Colima`: `2 CPU / 2 GB RAM / 20 GB disk`
- Подтверждённое steady-state потребление compose runtime сейчас около `430-450 MiB`
- Значит `2 GB` хватает для:
  - обычного локального runtime
  - login/health smoke
  - routine rebuilds текущего contour
- Когда расширять:
  - до `3 GB`, если одновременно идут rebuild + браузерно-тяжёлая работа на том же хосте
  - до `4 GB`, если подключается Playwright, дополнительные сервисы или заметно более тяжёлые frontend-build задачи
- До `6 GB` поднимать текущий contour первой волны не нужно

## Local foundation path

Скопируй env skeleton:

```bash
cp .env.local.example .env
```

Прогони миграции:

```bash
./scripts/run_foundation_migrations.sh
```

Залей seed:

```bash
./.venv/bin/python scripts/seed_foundation.py
```

Подними FastAPI foundation API:

```bash
./.venv/bin/python scripts/run_foundation_api.py --host 127.0.0.1 --port 8091
```

## Единый local-up путь

Если нужен сразу `backend + web shell`, используй:

```bash
./scripts/run_foundation_unified.sh --fresh
```

Он делает:

1. прогоняет `alembic upgrade head`
2. выполняет seed
3. поднимает foundation backend
4. поднимает Next.js shell
5. ждёт готовности страницы `/login`

## Health / observability

Проверка liveness:

```bash
curl -s http://127.0.0.1:8091/health/live
```

Проверка readiness:

```bash
curl -s http://127.0.0.1:8091/health/ready
```

Проверка telemetry summary:

```bash
curl -s http://127.0.0.1:8091/observability/summary
```

Проверка текущего system mode:

```bash
curl -s http://127.0.0.1:8091/api/v1/meta/system-mode
```

RU: Для wave1 это coarse-grained operational guard. В `maintenance` режутся write-path операции, в `emergency` почти весь traffic кроме health/meta.

## Login smoke

Admin login:

```bash
curl -s -X POST http://127.0.0.1:8091/api/v1/auth/login \
  -H 'content-type: application/json' \
  -d '{"email":"admin@example.com","password":"admin123"}'
```

Web smoke через Next shell:

- foundation login page: `http://127.0.0.1:3000/login`

## Автоматический smoke-check

```bash
./scripts/foundation_smoke_check.sh
```

Он делает:

1. поднимает временную sqlite foundation DB
2. прогоняет `alembic upgrade head`
3. выполняет seed
4. стартует FastAPI foundation server
5. проверяет `/health/live`
6. проверяет `/health/ready`
7. логинится под seeded admin
8. дергает `/api/v1/auth/me`

## Supplier contour: demo pipeline и smoke

Запустить fixture-based supplier ingest прямо в текущую foundation DB:

```bash
./.venv/bin/python scripts/run_supplier_demo_pipeline.py --source-code SRC-00001 --idempotency-key demo-suppliers-001
```

Отдельный supplier smoke-check:

```bash
./scripts/foundation_supplier_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. логинится под operator
5. читает seeded supplier source registry
6. запускает inline ingest
7. проверяет supplier list
8. проверяет raw layer

Проверка failure/retry сценария supplier ingest идёт отдельным acceptance suite:

```bash
./.venv/bin/python -m unittest tests.test_foundation_acceptance
```

Внутри него подтверждается:

- ingest может упасть с сохранением `failed` state;
- ошибка остаётся видимой через API;
- retry переводит тот же ingest в `completed`, если источник снова стал валидным.

## Supplier workbench surfaces

- supplier list / workbench: `http://127.0.0.1:3000/suppliers`
- supplier card: `http://127.0.0.1:3000/suppliers/{supplierCode}`
- supplier site card: `http://127.0.0.1:3000/supplier-sites/{siteCode}`
- supplier raw ingest: `http://127.0.0.1:3000/supplier-ingests/{ingestCode}`

## Catalog / showcase surfaces

- public showcase: `http://127.0.0.1:3000/catalog`
- showcase item detail: `http://127.0.0.1:3000/catalog/{itemCode}`
- public RFQ entry: `http://127.0.0.1:3000/rfq`
- public draft editor: `http://127.0.0.1:3000/drafts/{draftCode}`
- customer request view: `http://127.0.0.1:3000/requests/{customerRef}`
- operator request workbench: `http://127.0.0.1:3000/request-workbench`
- operator request detail: `http://127.0.0.1:3000/request-workbench/{requestCode}`
- customer compare block предложений: `http://127.0.0.1:3000/requests/{customerRef}`
- operator compare / revision block предложений: `http://127.0.0.1:3000/request-workbench/{requestCode}`
- managed files/documents в request: `http://127.0.0.1:3000/request-workbench/{requestCode}` и `http://127.0.0.1:3000/requests/{customerRef}`
- operator workbench: `http://127.0.0.1:3000/ops-workbench`
- admin dashboard: `http://127.0.0.1:3000/admin-dashboard`
- supply dashboard: `http://127.0.0.1:3000/supply-dashboard`
- processing dashboard: `http://127.0.0.1:3000/processing-dashboard`

## Catalog smoke

```bash
./scripts/foundation_catalog_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. читает public directions
5. читает public items и item detail
6. создаёт guest draft из витрины
7. логинится под operator
8. переводит draft в request

## Draft / Request smoke

```bash
./scripts/foundation_request_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. создаёт public draft
5. переводит draft в request
6. логинится под operator
7. переводит request в `needs_review`

## Offer smoke

```bash
./scripts/foundation_offer_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. создаёт public draft и переводит его в request
5. переводит request в `needs_review -> supplier_search`
6. создаёт `offer v1`
7. отправляет `v1` клиенту и фиксирует accept
8. делает критичную правку в `v2` и проверяет reset confirmation
9. повторно отправляет `v2`, получает accept и конвертирует именно эту подтверждённую версию в `Order`

## Order / payment skeleton surfaces

- operator order workbench: `http://127.0.0.1:3000/orders`
- operator order detail: `http://127.0.0.1:3000/orders/{orderCode}`
- managed files/documents в order: `http://127.0.0.1:3000/orders/{orderCode}`
- customer request view с order summary: `http://127.0.0.1:3000/requests/{customerRef}`

## Files / Documents smoke

```bash
./scripts/foundation_files_documents_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. создаёт public draft и переводит его в request
5. загружает managed file в request
6. создаёт новую версию файла, делает review и finalize
7. создаёт offer и генерирует document version
8. переводит документ через `send -> confirm -> replace`
9. конвертирует accepted offer в order
10. генерирует internal job document на order и проверяет request/order/customer views

Archive path для managed files/documents теперь отдельный рабочий операторский сценарий:

- `POST /api/v1/operator/files/{asset_code}/archive`
- `POST /api/v1/operator/documents/{document_code}/archive`

После архивации объект остаётся в истории и audit trail, но исчезает из active views.

## Order smoke

```bash
./scripts/foundation_order_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. создаёт public draft и переводит его в request
5. переводит request в `needs_review -> supplier_search`
6. создаёт offer, отправляет и подтверждает его
7. конвертирует accepted offer version в order
8. проходит order actions `assign_supplier -> confirm_start -> mark_production -> ready -> delivery -> complete -> dispute`
9. проходит payment transitions `pending -> confirmed -> partially_refunded`
10. проверяет operator order detail и customer request view с привязанным order summary

## Messages / dashboards smoke

```bash
./scripts/foundation_messages_dashboards_smoke_check.sh
```

Он делает:

1. поднимает временную foundation DB
2. применяет миграции и seed
3. стартует API
4. создаёт public draft и переводит его в request
5. переводит request в `needs_clarification`
6. добавляет blocker reason
7. читает customer dashboard
8. читает operator workbench
9. читает processing dashboard
10. читает admin dashboard
11. читает unified operator timeline по request

## Migration check

```bash
./scripts/foundation_migration_check.sh
```

Он подтверждает:

1. `alembic upgrade head` проходит на чистой БД;
2. head revision совпадает с актуальной wave1;
3. критичные acceptance-таблицы и поля реально существуют.

## Demo end-to-end smoke

```bash
./scripts/foundation_wave1_demo_smoke_check.sh
```

Он прогоняет единый демонстрационный поток:

1. supplier ingest
2. storefront -> draft
3. draft -> request
4. request -> versioned offer
5. accepted offer -> order
6. file/document version flow
7. timeline/audit/dashboard visibility

Этот smoke нужен именно для demo readiness, а не только для low-level API проверки.

## Полный verification path

```bash
./scripts/verify_workflow.sh
```

Сейчас он покрывает:

- unit/API tests по foundation contour;
- acceptance tests;
- migration gate;
- shell/smoke script syntax;
- существующие repo verification checks.

## Compose skeleton

В репозитории добавлен `docker-compose.yml`:

- `db` — PostgreSQL
- `redis` — Redis
- `api` — FastAPI foundation API
- `worker` — Celery worker
- `web` — Next.js shell
- `caddy` — reverse proxy

Запуск в среде, где есть Docker:

```bash
cp .env.prod.example .env
docker compose up --build
```

## Что важно помнить

- по умолчанию foundation contour идёт без legacy mount;
- legacy `/status`, `/companies`, `/ui/*` доступны только если явно включить `MAGON_FOUNDATION_LEGACY_ENABLED=true`;
- foundation API живёт отдельно под `/api/v1/*`, `/health*`, `/observability/*`;
- system mode доступен через `/api/v1/meta/system-mode`;
- draft/request/offer/order разведены в разные таблицы и разные переходы;
- тяжёлые ERP/payment/MES контуры сюда не добавлялись.

Сводный as-built map смотри в `docs/ru/foundation-architecture-as-built.md`, а текущие границы wave1 — в `docs/ru/wave1-known-limitations.md`.
