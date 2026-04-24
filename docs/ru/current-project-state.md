# Текущее состояние проекта

## Где главный репозиторий

- Активный продуктовый репозиторий: `/Users/anton/Desktop/MagonOS-Standalone`
- Исторический source-репозиторий только для сверки: `/Users/anton/Desktop/MagonOS/MagonOS`

## Что является плановой истиной

- Жёсткая спецификация первой волны: `gpt_doc/codex_wave1_spec_ru.docx`
- PDF-экспорт той же спецификации для чтения без редактора: `gpt_doc/codex_wave1_spec_ru.pdf`
- Расширенный продуктовый канон для текущего standalone-контура также включает:
  - `gpt_doc/platform_documentation_pack_ru_v3.docx`
  - `gpt_doc/platform_documentation_pack_ru_with_marketing.docx`
  - `gpt_doc/project_marketing_research_vietnam_ru.docx`
- Этот файл остаётся правдой по runtime и проверке, но продуктовый UX, IA, фронтовые формулировки и role-based экраны теперь нужно сверять со всем этим пакетом, а не читать wave1-спецификацию в отрыве от архитектурного и маркетингового слоя.

## Что является правдой рантайма

- `Standalone` — основной platform-of-record.
- Исторический source-репозиторий нужен только для сверки и не входит в активный runtime.
- По умолчанию работа и изменения идут только в standalone-репозитории.
- Целевой runtime первой волны — новый стек `FastAPI + PostgreSQL + Redis + Celery + Caddy + Docker Compose`.
- Истина рантайма первой волны теперь одна: активный foundation contour без старого compatibility bridge.

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
- scenario-driven live parsing теперь различает статические каталоги, рендеренные каталоги, обычные сайты компаний и JS-heavy сайты компаний; supplier-owned сайты с `browser_required` обязаны идти через browser-aware executor с реальным браузерным обходом, а не через старый requests-only path
- реестр источников поставщиков с двумя режимами первой волны: повторяемый fixture-ingest для demo/тестов и выбираемый live parsing ingest поверх существующего supplier-intelligence discovery
- операторский контроль источников поставщиков: health адаптера, последний успех/сбой, queued parsing jobs, retry и повторный запуск прямо из UI standalone-контура
- env-gated LLM-подключение для `ai_assisted` fallback внутри supplier parsing с явным operator status/test path вместо скрытой чёрной магии
- repo-aware периодический scheduler для live parsing/classification: fixture-источник остаётся manual-only, а `scenario_live` может работать постоянно через launchd cadence
- header и operator shell очищены до компактной рабочей навигации; вторичные разделы вынесены в панель `Ещё`, а supplier-экран локализован и визуально уплотнён под реальную операторскую работу
- нормализация / обогащение / дедупликация / скоринг
- лёгкий marketing/conversion-layer поверх витрины, RFQ и гостевого draft-входа
- ограниченный контур каталога / витрины с гостевым входом в draft и RFQ
- product-first public shell над `/`, `/marketing`, `/catalog` и `/rfq`: понятный managed-service оффер без архитектурного жаргона и случайных внутренних терминов
- autosave / abandoned / archive-ready слой Draft
- центральная операторская очередь Review для Request с blocker/clarification flow
- переход `draft -> request` с блокировкой по обязательным полям
- versioned-коммерческий слой Offer с compare, reset confirmation и отдельной конвертацией в Order
- слой `Order` с `OrderLine`, внутренним payment skeleton, ledger trail и operator workbench
- управляемый файловый и документный контур со storage abstraction, versioning, checks, templates и role-based download flow
- контур админ-настройки для reason codes, rules, rule versions, notification rules и supplier source settings через API/UI, а не только через сиды
- operator/admin-экраны теперь читают один стабильный session snapshot через `useFoundationSession()`, поэтому после гидратации нельзя возвращать старый эффект с гостевым gate поверх уже авторизованного UI
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
- широкое зеркалирование legacy-сущностей
- рост функциональности source-репозитория

## Канонические команды

- поднять foundation backend:
  - `./.venv/bin/python scripts/run_foundation_api.py --host 127.0.0.1 --port 8091`
- поднять unified foundation локально:
  - `./scripts/run_foundation_unified.sh --fresh`
  - local launcher/unified path теперь сам поднимает `db + redis` через `docker compose`/`colima` ещё до миграций и старта backend/web
  - launcher/unified web runtime теперь по умолчанию идёт через production `next start`; `MAGON_WEB_RUNTIME=dev` оставлен только как явный debug fallback
  - `scripts/ensure_web_build.sh` переиспользует текущий `.next` bundle, если web-исходники не менялись, поэтому обычный локальный рестарт не должен собирать всё заново без причины
- desktop launcher для того же локального контура:
  - `./Start_Platform.command`
  - `./Start_Platform.command --detach --no-open --keep-db --no-seed`
  - detach-режим теперь опирается на локальный double-fork helper `scripts/run_detached_command.py`, поэтому backend/web обязаны оставаться живыми и после завершения launcher shell, а не зависеть от родительского терминала
  - detached path подтверждён живой проверкой: backend `/health/ready` и web `/login` остаются на `200` после выхода launcher shell
  - detached launcher тоже должен поднимать production web через `scripts/ensure_web_build.sh`, если ты явно не просишь `MAGON_WEB_RUNTIME=dev`
- VPS/server deploy contour:
  - `cp .env.prod.example .env.prod`
  - `./scripts/run_deploy.sh`
  - `./scripts/run_deploy.sh status`
  - `./scripts/run_deploy.sh logs --follow api web`
  - `scripts/run_deploy.sh` теперь оборачивает активный foundation `docker compose` runtime; старый gunicorn/WSGI/SQLite deploy path больше не является production-правдой
- hourly self-heal watchdog для launcher:
  - `./scripts/install_launchd_launcher_watchdog.sh --interval 3600`
  - `./scripts/launchd_launcher_watchdog_status.sh`
  - launchd repo-wrapper теперь shell-safe и под `bash`, и под bootstrap самого launchd, поэтому watchdog и periodic checks больше не зависят от bash-only `BASH_SOURCE`, если агент вызван через другой shell
  - bootstrap LaunchAgent теперь уходит в `~/.codex/launchd-support/<label>`, а не в repo-path на Desktop, поэтому `WorkingDirectory`, stdout и stderr больше не упираются в TCC-защищённую директорию репозитория
  - `com.magonos.launcher-watchdog` и `com.magonos.periodic-checks` теперь подтверждены через `launchctl print` с `last exit code = 0`; старый хвост про якобы «cached EX_CONFIG» больше не считается активным риском
- hourly scheduler для постоянного parser/classifier:
  - `./scripts/install_launchd_supplier_scheduler.sh --interval 3600`
  - `./scripts/launchd_supplier_scheduler_status.sh`
  - `./.venv/bin/python scripts/run_supplier_scheduler.py`
  - supplier-scheduler остаётся зелёным эталонным LaunchAgent, а watchdog и periodic checks теперь переведены на тот же домашний launchd-support pattern вместо зависимости от repo-path на Desktop
- perf smoke/load/stress:
  - `./scripts/run_perf_suite.sh smoke`
  - `./scripts/run_perf_suite.sh load`
  - `./scripts/run_perf_suite.sh stress`
  - perf warmup и k6-пробы обязаны бить только в живые foundation URL (`/health/live`, `/health/ready`, `/api/v1/meta/system-mode`, `/api/v1/public/catalog/items`, `/login`, `/marketing`, `/request-workbench`, `/orders`, `/suppliers`), а не в снятые legacy-поверхности вроде `/status` или `/ui/*`
- foundation migrate + seed:
  - `./scripts/run_foundation_migrations.sh`
  - `./.venv/bin/python scripts/seed_foundation.py`
  - миграции теперь опираются на тот же local PostgreSQL contour, что и launcher/unified, а не на отдельную SQLite-правду для dev-path
- repeatable `seed_foundation.py` на локальном PostgreSQL теперь тоже входит в проверенный contract: повторный migrate + seed не должен больше абортироваться на специальных scope вроде `users:USR` или `request_customer_refs`
- все foundation smoke-скрипты теперь тоже работают на отдельных временных PostgreSQL базах, а не на временных SQLite-файлах
- пустой `MAGON_FOUNDATION_REDIS_URL` в test/smoke и CI теперь считается явным отключением Redis, а не скрытым возвратом к `redis://127.0.0.1:6379/0`
- прогнать supplier demo pipeline:
  - `./.venv/bin/python scripts/run_supplier_demo_pipeline.py --source-code SRC-00001 --idempotency-key demo-suppliers-001`
- прогнать fixture pipeline:
  - `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- проверить backend/workflow:
  - `./scripts/verify_workflow.sh`
- проверить foundation:
  - `./scripts/verify_workflow.sh` теперь умеет падать обратно на системный `python3`/`python`, если repo-venv отсутствует, поэтому GitHub Actions проверяет тот же контракт, а не ломается на поиске `.venv`
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
  - `./scripts/foundation_messages_dashboards_smoke_check.sh`
  - канонический `./scripts/verify_workflow.sh` теперь реально исполняет эти foundation smoke-скрипты на временных PostgreSQL БД, а не держит их как manual-only хвост
  - foundation smoke/demo-скрипты теперь сами выбирают свободный localhost-порт и используют bounded health-probe, поэтому старый зависший temp listener должен падать быстро, а не вешать весь verify
- проверить web runtime smoke:
  - `./scripts/platform_smoke_check.sh`
  - `platform_smoke_check.sh` теперь обязан проверять живой `/project-map` вместе с `/`, `/login`, `/marketing`, `/request-workbench`, `/orders` и `/suppliers`, потому что визуальная карта проекта является частью рабочего shell, а не «просто документацией»
- если менялся web:
  - `./scripts/verify_workflow.sh --with-web`
  - `cd apps/web && npm run build`
  - `sync_operating_docs.py --check` должен быть детерминирован даже на CI runner без `~/.codex/автоматизаций`; корневые `AGENTS.md/README.md` в этом случае собираются из repo truth, а не из отсутствующего локального каталога автоматизаций

## Правило по браузерам

- В этом репозитории browser automation жёстко фиксируется на `Google Chrome`.
- Канонический вход один: `./scripts/run_playwright_cli.sh`
- Chrome pinning применяется только к browser-driven командам; meta-команды вроде `list`, `close-all` и `kill-all` обязаны работать без принудительного `--browser`.
- Firefox, WebKit и любые альтернативные Playwright browser runtimes для этого проекта не поднимаем.
- Если от старых прогонов остались browser caches, их удаляем, а не сохраняем как часть рабочего контура.

## Локальные поверхности

- public shell: `http://127.0.0.1:3000/`
- public shell теперь по умолчанию идёт из production Next bundle; главная больше не должна жить на постоянном `no-store` и dev-компиляции при каждом заходе
- public shell, marketing, каталог, RFQ, заявки, заказы, поставщики и admin-config повторно проверены в браузере после product/UI cleanup; регрессиями считаются технические дампы, RU/EN-смесь и hydration mismatch в авторизованном shell
- локально после оптимизации подтверждены такие времена detached production shell:
  - `/` около `0.40s` вместо прежних `~2.60s` на старом `next dev` path
  - `/marketing` около `0.37s` вместо `~0.85s`
  - `/catalog` около `0.06s` вместо `~0.66s`
  - `/request-workbench` около `0.04s` вместо `~0.59s`
  - `/orders` около `0.12s` вместо `~0.37s`
  - после прогрева production bundle steady-state ещё быстрее:
    - `/` около `0.04s`
    - `/marketing` около `0.02s`
    - `/catalog` около `0.01s`
    - `/request-workbench` около `0.01s`
    - `/orders` около `0.01s`
    - `/suppliers` около `0.01s`
    - backend `/health/ready` около `0.01s`
- встроенная справка по сущностям и зависимостям: `http://127.0.0.1:3000/reference`
- visual map проекта: `http://127.0.0.1:3000/project-map`
- `/project-map` теперь сначала читает канонический repo visual payload и использует RU-JSON только как совместимый fallback; `500` на этом маршруте считается живой shell-регрессией, а не допустимым расхождением документации
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
- admin config: `http://127.0.0.1:3000/admin-config`
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
- для администратора тот же `/suppliers` теперь даёт inline-управление operational-настройками source: включение, расписание, интервал и режим классификации больше не требуют отдельного похода в `/admin-config` для рутинного parser-контроля
- supplier site card: `http://127.0.0.1:3000/supplier-sites/{siteCode}`
- supplier raw ingest: `http://127.0.0.1:3000/supplier-ingests/{ingestCode}`
- страница `supplier raw ingest` теперь показывает explainable async-state (`queued/running/failed/completed`, task id, trigger mode, retry history, failure detail) и даёт оператору retry / повторный запуск источника
- API источников поставщиков теперь также отдаёт schedule/classification state: какой source идёт постоянно, когда следующее due-window и включён ли LLM-assisted fallback
- admin configuration UI/API теперь владеет базовой wave1-настройкой: каталоги причин, workflow rules, notification rules и supplier source schedule/classification больше не требуют правки кода
- operator LLM status/test surface: `http://127.0.0.1:8091/api/v1/operator/llm/status`
- direct backend debug: `http://127.0.0.1:8091/`
## Где читать справку по сущностям

- Быстрый product-shell вход: `/reference`
- Командная русская версия: `docs/ru/platform-entity-reference.md`
- Эта справка объясняет:
  - какие сущности уже живут в standalone;
  - в каких экранах ими пользуются;
  - какие зависимости и boundaries нельзя ломать при доработке.

## Заметка про CI parity

- Foundation smoke и migration scripts обязаны работать и с repo `.venv`, и на чистом CI runner через системный `python3`.
- Если smoke-скрипт безусловно требует `./.venv/bin/python`, это считается repo drift, потому что GitHub Actions может запускать проверки без локального repo-venv.

## Истина по GitHub-веткам

- Основная GitHub-ветка проекта — `main`.
- Для защищённых веток должны использоваться только живые имена проверок:
  - `foundation-quality`
  - `foundation-smoke`
  - `web-quality`
- Старые protection contexts вроде `python-tests`, `smoke-runtime` и `web-build` считаются drift и не должны больше висеть в настройках репозитория.

## Истина по automation-layer

- Все repo-local recurring автоматизации обязаны восстанавливать контекст через `skills/automation-context-guard/SKILL.md`.
- Все recurring автоматизации обязаны читать только активный foundation contour из этого файла и `docs/current-project-state.md`.
- Повторяющиеся platform/browser проверки должны ходить только по живым поверхностям:
  - `/`
  - `/login`
  - `/dashboard`
  - `/request-workbench`
  - `/orders`
  - `/suppliers`
  - `/admin-config`
- Recurring автоматизации нельзя молча отправлять в удалённые или compatibility-only поверхности вроде `/ops-workbench`, `/ui/companies`, `./scripts/run_platform.sh` или `./scripts/run_unified_platform.sh --fresh`, если задача не состоит именно в фиксации drift.
