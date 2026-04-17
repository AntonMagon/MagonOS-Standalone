# Текущее состояние проекта

## Где главный репозиторий

- Активный продуктовый репозиторий: `/Users/anton/Desktop/MagonOS-Standalone`
- Donor / bridge-репозиторий: `/Users/anton/Desktop/MagonOS/MagonOS`

## Что является плановой истиной

- Жёсткая спецификация первой волны: `gpt_doc/codex_wave1_spec_ru.docx`
- PDF-экспорт той же спецификации для чтения без редактора: `gpt_doc/codex_wave1_spec_ru.pdf`
- Других активных planning-doc в `gpt_doc/` сейчас нет; этот файл остаётся правдой по runtime и проверке, а плановую архитектуру нового контура нужно читать из указанной wave1-спецификации.

## Что является правдой рантайма

- `Standalone` — основной platform-of-record.
- Odoo — только donor / bridge, но не целевой runtime.
- По умолчанию работа и изменения идут только в standalone-репозитории.
- Целевой runtime первой волны — новый стек `FastAPI + PostgreSQL + Redis + Celery + Caddy + Docker Compose`.
- По умолчанию runtime первой волны стартует без legacy standalone WSGI bridge.
- Legacy standalone WSGI runtime может жить только как явный compatibility bridge через `MAGON_FOUNDATION_LEGACY_ENABLED=true`, но это не целевая execution-модель первой волны.

## Какая baseline-версия стека подтверждена

- web runtime: `Node v22.22.2`
- web package manager: `npm 10.9.7`
- web app layer: `Next 15.5.15`, `React 19.2.5`, `React DOM 19.2.5`
- api/core runtime: `Python 3.10.20`
- api/core packages: `FastAPI 0.136.0`, `SQLAlchemy 2.0.49`, `Alembic 1.18.4`, `Celery 5.6.3`, `redis-py 7.4.0`, `psycopg 3.3.3`, `uvicorn 0.44.0`, `sentry-sdk 2.58.0`
- infra images: `PostgreSQL 16.13`, `Redis 7.4.8`, `Caddy 2.8.4`
- Политика обновления: принудительно обновлять стек прямо сейчас не нужно, потому что подтверждённый contour согласован и зелёный на живом compose runtime. Обновление делаем только при явной причине: совместимость, безопасность или реальная runtime-проблема.

## Какой ресурсный baseline подтверждён

- Текущий профиль `Colima`: `2 CPU / 2 GB RAM / 20 GB disk`
- Подтверждённое steady-state потребление compose runtime сейчас около `430-450 MiB` суммарно по `api + worker + web + db + redis + caddy`
- Значит внутри VM сейчас остаётся примерно `1.4 GiB` живого запаса
- Рекомендованный sizing:
  - `2 GB`: обычный локальный runtime, smoke-check, login/health, обычные rebuild
  - `3 GB`: параллельные rebuild плюс тяжёлая локальная работа в браузере на том же хосте
  - `4 GB`: Playwright/браузерная автоматизация, дополнительные сервисы или заметно более тяжёлые frontend-build задачи
  - `6 GB`: для текущего contour первой волны не нужно

## Что уже подтверждено в standalone-контуре

- компания
- граница черновика запроса / intake-заявки
- коммерческий контекст клиента
- сделка
- заявка на расчёт / граница RFQ
- передача в производство
- производственная доска

## Что уже принадлежит standalone

- контур реестра компаний / поставщиков / площадок со слоями `raw -> normalized -> confirmed`
- конвейер проверки и обогащения поставщиков
- реестр источников поставщиков с двумя режимами первой волны: повторяемый fixture-ingest для demo/тестов и выбираемый live parsing ingest поверх существующего supplier-intelligence discovery
- операторский контроль источников поставщиков: health адаптера, последний успех/сбой, queued parsing jobs, retry и повторный запуск прямо из UI standalone-контура
- header и operator shell очищены до компактной рабочей навигации; вторичные разделы вынесены в панель `Ещё`, а supplier-экран локализован и визуально уплотнён под реальную операторскую работу
- нормализация / обогащение / дедупликация / скоринг
- лёгкий marketing/conversion-layer поверх витрины, RFQ и гостевого draft-входа
- ограниченный контур каталога / витрины с гостевым входом в draft и RFQ
- autosave / abandoned / archive-ready слой Draft
- центральная операторская очередь Review для Request с blocker/clarification flow
- переход `draft -> request` с блокировкой по обязательным полям
- versioned-коммерческий слой Offer с compare, reset confirmation и отдельной конвертацией в Order
- слой `Order` с `OrderLine`, внутренним payment skeleton, ledger trail и operator workbench
- управляемый файловый и документный контур со storage abstraction, versioning, checks, templates и role-based download flow
- foundation-скелет FastAPI с отдельными сущностями `draft / request / offer / order`
- маршрутизация / квалификационные решения
- журнал обратной связи / проекция
- оценка трудозатрат

## Где сейчас опасный overlap

Главный незакрытый overlap сейчас в этих зонах:
- идентичность клиента / аккаунта
- владение сделкой / лидом
- граница RFQ / расчёта

Нельзя делать вид, что уже есть полный CRM/quote parity.

## Что по умолчанию вне scope

- бухгалтерия
- счета / оплаты
- полное ERP-управление заказами
- огромная универсальная CRM
- широкое зеркалирование сущностей Odoo
- рост функциональности donor-репозитория

## Канонические команды

- поднять foundation backend:
  - `./.venv/bin/python scripts/run_foundation_api.py --host 127.0.0.1 --port 8091`
- поднять unified foundation локально:
  - `./scripts/run_foundation_unified.sh --fresh`
- desktop launcher для того же локального контура:
  - `./Start_Platform.command`
- hourly self-heal watchdog для launcher:
  - `./scripts/install_launchd_launcher_watchdog.sh --interval 3600`
  - `./scripts/launchd_launcher_watchdog_status.sh`
- foundation migrate + seed:
  - `./scripts/run_foundation_migrations.sh`
  - `./.venv/bin/python scripts/seed_foundation.py`
- прогнать supplier demo pipeline:
  - `./.venv/bin/python scripts/run_supplier_demo_pipeline.py --source-code SRC-00001 --idempotency-key demo-suppliers-001`
- прогнать fixture pipeline:
  - `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- проверить backend/workflow:
  - `./scripts/verify_workflow.sh`
- проверить foundation:
  - `./.venv/bin/python -m unittest tests.test_foundation_api`
  - `./.venv/bin/python -m unittest tests.test_foundation_suppliers`
  - `./.venv/bin/python -m unittest tests.test_foundation_catalog`
  - `./.venv/bin/python -m unittest tests.test_foundation_draft_request`
  - `./.venv/bin/python -m unittest tests.test_foundation_offers`
  - `./.venv/bin/python -m unittest tests.test_foundation_orders`
  - `./.venv/bin/python -m unittest tests.test_foundation_files_documents`
  - `./scripts/foundation_smoke_check.sh`
  - `./scripts/foundation_supplier_smoke_check.sh`
  - `./scripts/foundation_catalog_smoke_check.sh`
  - `./scripts/foundation_request_smoke_check.sh`
  - `./scripts/foundation_offer_smoke_check.sh`
  - `./scripts/foundation_order_smoke_check.sh`
  - `./scripts/foundation_files_documents_smoke_check.sh`
- compatibility-only запуск старого контура, если он реально нужен:
  - `MAGON_FOUNDATION_LEGACY_ENABLED=true ./scripts/run_foundation_unified.sh --fresh`
  - `./scripts/run_unified_platform.sh --fresh`
  - `./scripts/run_platform.sh --fresh --port 8091`
- если менялся web:
  - `./scripts/verify_workflow.sh --with-web`
  - `cd apps/web && npm run build`

## Правило по браузерам

- В этом репозитории browser automation жёстко фиксируется на `Google Chrome`.
- Канонический вход один: `./scripts/run_playwright_cli.sh`
- Firefox, WebKit и любые альтернативные Playwright browser runtimes для этого проекта не поднимаем.
- Если от старых прогонов остались browser caches, их удаляем, а не сохраняем как часть рабочего контура.

## Локальные поверхности

- public shell: `http://127.0.0.1:3000/`
- встроенная справка по сущностям и зависимостям: `http://127.0.0.1:3000/reference`
- header public shell теперь держит только ключевые рабочие разделы в верхней строке, а вторичные разделы и переключатели складывает в `Ещё`; возвращать перегруженную шапку нельзя.
- public shell и `/dashboard` должны определять online-state через foundation `GET /health` и `GET /api/v1/public/companies`; legacy `GET /status` нельзя считать каноническим контрактом при выключенном bridge
- marketing/conversion layer: `http://127.0.0.1:3000/marketing`
- public shell теперь использует визуальный режим `retro print lab + cyber accents`: маршрут `draft -> request -> offer -> order`, supplier routing и explainability показаны как единый editorial-operational слой, а не как dark SaaS hero
- public витрина: `http://127.0.0.1:3000/catalog`
- карточка витрины: `http://127.0.0.1:3000/catalog/{itemCode}`
- public RFQ-вход: `http://127.0.0.1:3000/rfq`
- public draft editor: `http://127.0.0.1:3000/drafts/{draftCode}`
- customer request view: `http://127.0.0.1:3000/requests/{customerRef}`
- customer compare block предложений: `http://127.0.0.1:3000/requests/{customerRef}`
- foundation login: `http://127.0.0.1:3000/login`
- успешный foundation login должен не просто показать token, а завершать вход переходом в рабочий контур: `admin/operator -> /dashboard`, `customer -> /catalog`
- client-shell читает foundation session через кэшированный snapshot store; повторный parse одного и того же `localStorage` значения считается регрессией, потому что ломает `useSyncExternalStore` и может зациклить header/runtime
- operator request workbench: `http://127.0.0.1:3000/request-workbench`
- operator request detail: `http://127.0.0.1:3000/request-workbench/{requestCode}`
- operator/admin/supply/processing dashboards должны вести дальше по клику: уведомления, блокировки, просрочки и счётчики нельзя оставлять purely informational карточками.
- пользовательский UI не должен рендерить служебные `RU:` комментарии, raw status labels или англоязычные оболочки вроде `login`, `Raw layer`, `Dedup review`, `ingest jobs`; это считается регрессией shell-качества
- operator compare / revision block предложений: `http://127.0.0.1:3000/request-workbench/{requestCode}`
- managed request files/documents: `http://127.0.0.1:3000/request-workbench/{requestCode}` и `http://127.0.0.1:3000/requests/{customerRef}`
- operator order workbench: `http://127.0.0.1:3000/orders`
- operator order detail: `http://127.0.0.1:3000/orders/{orderCode}`
- managed order files/documents: `http://127.0.0.1:3000/orders/{orderCode}`
- supplier workbench: `http://127.0.0.1:3000/suppliers`
- `supplier workbench` теперь является операторской консолью источников: health, последний ingest-результат, queued runs, retry и повторный запуск живут здесь, а не только в скрытых API-вызовах
- supplier site card: `http://127.0.0.1:3000/supplier-sites/{siteCode}`
- supplier raw ingest: `http://127.0.0.1:3000/supplier-ingests/{ingestCode}`
- страница `supplier raw ingest` теперь показывает explainable async-state (`queued/running/failed/completed`, task id, trigger mode, retry history, failure detail) и даёт оператору retry / повторный запуск источника
- direct backend debug: `http://127.0.0.1:8091/`
- legacy-поверхности только при явном `MAGON_FOUNDATION_LEGACY_ENABLED=true`:
  - `http://127.0.0.1:3000/ops-workbench`
  - `http://127.0.0.1:3000/ops`
  - `http://127.0.0.1:3000/ui/*`

## Где читать справку по сущностям

- Быстрый product-shell вход: `/reference`
- Командная русская версия: `docs/ru/platform-entity-reference.md`
- Эта справка объясняет:
  - какие сущности уже живут в standalone;
  - в каких экранах ими пользуются;
  - какие зависимости и boundaries нельзя ломать при доработке.
