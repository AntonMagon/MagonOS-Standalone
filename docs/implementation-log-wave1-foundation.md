# Журнал реализации foundation-скелета первой волны

## Аудит до изменений

### Что уже было в репозитории
- Живой standalone supplier-intelligence runtime на WSGI + SQLite.
- Next.js web shell с proxy/rewrite в backend.
- Локальная observability wiring через Sentry env gates.
- Отдельные standalone сущности для company / request-draft-intake boundary / quote-intent / production handoff в legacy контуре.

### Что не соответствовало foundation-скелету первой волны
- Не было отдельного FastAPI modular-monolith слоя.
- Не было PostgreSQL/Alembic foundation schema.
- Не было общего auth/authz слоя с ролями `guest / customer / operator / admin`.
- Не было общего audit-event base для нового wave1 foundation contour.
- Не было unified foundation health/readiness/telemetry layer.
- Не было compose skeleton c `db + redis + api + worker + web + caddy`.

## Что реализовано

### Архитектура
- Добавлен новый пакет `src/magon_standalone/foundation/`.
- Новый backend — FastAPI modular monolith.
- Legacy WSGI bridge сохранён только как опциональный compatibility layer и больше не является default runtime для wave1 foundation.

### Модули
- `UsersAccess`
- `Companies`
- `Suppliers`
- `Catalog`
- `DraftsRequests`
- `Offers`
- `Orders`
- `FilesMedia`
- `Documents`
- `Comms`
- `RulesEngine`
- `AuditDashboards`

### Messages / Rules / Dashboards contour
- Добавлен единый `MessageEvent` timeline-слой для `Request / Offer / Order / Supplier / File / Document`.
- Добавлены baseline-справочники:
  - `ReasonCodeCatalog`
  - `NotificationRule`
  - `RuleVersion`
  - `EscalationHint`
- RulesEngine доведён до explainable-first поведения:
  - transition guards
  - blocker reasons
  - critical action checks
  - versioned rules metadata
  - explainability payloads в ошибках
- Уведомления первой волны генерируются по правилам и сохраняются как role-scoped inbox events с антиспам suppression по `dedupe_key + min_interval_seconds`.
- Добавлены минимальные рабочие панели:
  - customer dashboard
  - operator workbench
  - admin dashboard
  - supply dashboard
  - processing dashboard

## 2026-04-18 — Supplier source operator contour and async parsing acceptance pass

### Что было найдено
- `supplier_sources` уже существовали как backend-реестр, но оператор не видел health адаптеров и последний успешный/failed ingest прямо в UI.
- `enqueue` путь для supplier parsing был неполным: async job мог существовать без явного queued-state в foundation DB, значит operator panel не имел надёжной explainable точки правды.
- `/suppliers` и `/supplier-ingests/{code}` не давали полноценного retry / rerun flow и оставляли заметный RU/EN drift в рабочем интерфейсе.

### Что изменено
- `SupplierSourceRegistry` API обогащён runtime health и `latest_ingest` summary.
- Async parsing contour доведён до управляемого состояния:
  - `enqueue` теперь создаёт или переводит ingest в `queued` ещё до worker execution;
  - worker/runtime path корректно подхватывает `queued` ingest и переводит его в `running`;
  - operator detail page показывает `task_id`, `trigger_mode`, `retry_count`, `failure_code`, `failure_detail`, timestamps.
- `/suppliers` теперь даёт:
  - health source adapters;
  - last success/failure;
  - queue run;
  - retry failed ingest;
  - force rerun.
- `/supplier-ingests/{code}` теперь даёт explainable async status и action buttons для retry/rerun.
- Вычищен видимый RU/EN drift на audited supplier/request surfaces.

## 2026-04-18 — Cleanup рабочего shell и supplier operator UI

### Что было найдено
- Desktop header был перегружен: слишком много primary-nav элементов, длинный подзаголовок бренда и активная сессия дрались за одно место.
- `/suppliers` визуально шумел: тяжёлый background mesh, жирные action pills, англоязычные `ingest/jobs` лейблы и слабая иерархия карточек.

### Что изменено
- Header ужат до короткого рабочего брендинга, компактной primary-nav и отдельной панели `Ещё` для вторичных разделов.
- Supplier screen переведён на более чистую paper-panel иерархию:
  - `Источник импорта`
  - `Последние запуски импорта`
  - локализованные source labels и adapter labels
  - кнопка `Детали импорта` вместо сырого `Raw-слой`
- Глобальный background shell ослаблен, чтобы сетка не спорила с содержимым.

### Что проверено
- `cd apps/web && npm run lint`
- `cd apps/web && npm run typecheck`
- browser-open:
  - `/login`
  - `/suppliers`

## 2026-04-18 — Chrome-only browser automation policy

### Что было найдено
- Playwright wrapper уже был project-safe, но жёсткое правило про единственный браузер не было зафиксировано.
- Из-за старых Playwright caches можно было решить, что репозиторий тащит Firefox/WebKit как часть обязательного рантайма.

### Что изменено
- `scripts/run_playwright_cli.sh` теперь всегда форсирует `Google Chrome`.
- Попытки явно передать другой браузер или поставить другой browser runtime режутся с ошибкой.
- Runtime-docs и RU docs теперь фиксируют правило: для этого репозитория browser automation допускается только через Chrome.

### Что проверено
- `bash -n scripts/run_playwright_cli.sh`
- `bash scripts/run_playwright_cli.sh --help`

## 2026-04-18 — Postgres-first local runtime and policy cleanup

### Что было найдено
- Active docs уже называли PostgreSQL целевым runtime, но `settings.py`, launcher, unified path и smoke/migration checks всё ещё по умолчанию уходили в SQLite.
- `docker-compose.yml` не публиковал `5432/6379` на host, поэтому локальный FastAPI runtime физически не мог стабильно жить на `127.0.0.1` с Postgres/Redis.
- В active policy/UI слое ещё оставались прямые Odoo- и SQLite-формулировки, хотя текущий product contract уже donor/bridge-first и Postgres-first.

### Что изменено
- Local foundation runtime переведён в Postgres-first:
  - `settings.py` по умолчанию использует `postgresql+psycopg://magon:magon@127.0.0.1:5432/magon`
  - Redis/Celery defaults теперь тоже локальные host URLs
- Добавлены helper scripts:
  - `scripts/ensure_foundation_infra.sh`
  - `scripts/reset_foundation_database.py`
  - `scripts/manage_temp_foundation_db.py`
- `Start_Platform.command`, `run_foundation_unified.sh` и `run_foundation_migrations.sh` теперь сами поднимают local infra и больше не держат SQLite как default-path.
- `docker-compose.yml` публикует `127.0.0.1:5432` и `127.0.0.1:6379` для host runtime.
- Канонические `foundation_smoke_check.sh`, `foundation_migration_check.sh` и `foundation_wave1_demo_smoke_check.sh` переведены на временные PostgreSQL БД.
- Active docs, README, AGENTS и web copy очищены от Odoo/Odu как от текущей продуктовой правды; в active contract остался только `legacy donor / bridge`.

### Что проверено
- `./.venv/bin/python -m unittest tests.test_foundation_suppliers`
- `cd apps/web && npm run lint`
- `cd apps/web && npm run typecheck`
- browser-pass:
  - `/login`
  - `/suppliers`
  - `/supplier-ingests/ING-00001`
  - `/request-workbench`
- `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — Foundation smoke parity moved to PostgreSQL

### Что было найдено
- После перевода launcher и полного bootstrap на PostgreSQL большинство foundation smoke-скриптов всё ещё поднимали временные SQLite БД.
- Из-за этого канонический verify path и реальный runtime продолжали жить в разных persistence-контурах.

### Что изменено
- `foundation_catalog_smoke_check.sh`
- `foundation_supplier_smoke_check.sh`
- `foundation_request_smoke_check.sh`
- `foundation_offer_smoke_check.sh`
- `foundation_order_smoke_check.sh`
- `foundation_files_documents_smoke_check.sh`
- `foundation_messages_dashboards_smoke_check.sh`

Все эти smoke-скрипты теперь:
- поднимают infra через `ensure_foundation_infra.sh`;
- создают отдельную временную PostgreSQL БД через `manage_temp_foundation_db.py`;
- чисто удаляют эту БД после завершения;
- больше не используют временные SQLite-файлы.

Дополнительно:
- `verify_workflow.sh` теперь реально выполняет foundation smoke scripts и migration/demo smoke в рамках канонического verify path;
- `foundation_files_documents_smoke_check.sh` выровнен под текущий file review state `passed` вместо старого `approved`.

### Что проверено
- `./scripts/foundation_smoke_check.sh`
- `./scripts/foundation_supplier_smoke_check.sh`
- `./scripts/foundation_catalog_smoke_check.sh`
- `./scripts/foundation_request_smoke_check.sh`
- `./scripts/foundation_offer_smoke_check.sh`
- `./scripts/foundation_order_smoke_check.sh`
- `./scripts/foundation_files_documents_smoke_check.sh`
- `./scripts/foundation_messages_dashboards_smoke_check.sh`
- `./scripts/foundation_migration_check.sh`
- `./scripts/foundation_wave1_demo_smoke_check.sh`
- `./scripts/verify_workflow.sh --with-web`

### Persistence / миграции
- SQLAlchemy foundation models.
- Alembic bootstrap + initial revision `20260417_0001`.
- Foundation tables для ролей, пользователей, сессий, компаний, поставщиков, каталога, draft/request/offer/order, файлов, документов, comms, rules, audit.
- Дополнительная revision `20260417_0008` добавила:
  - `message_events`
  - `reason_codes`
  - `rules_engine_rule_versions`
  - `notification_rules`
  - `escalation_hints`
  - новые поля `rule_kind`, `latest_version_no`, `metadata_json` в `rules_engine_rules`
  - backfill существующих `audit_events` в unified `message_events`

### Безопасность
- DB-backed opaque session auth.
- Role restriction dependencies.
- Seed users for admin/operator/customer.

### Наблюдаемость
- `/health/live`
- `/health/ready`
- `/health`
- `/observability/summary`
- request logging + in-process telemetry counters
- existing Sentry env-gated wiring preserved

### Операционный контур
- `scripts/run_foundation_api.py`
- `scripts/seed_foundation.py`
- `scripts/run_foundation_migrations.sh`
- `scripts/run_foundation_unified.sh`
- `scripts/run_foundation_worker.sh`
- `scripts/foundation_smoke_check.sh`
- `docker-compose.yml`
- `deploy/backend.Dockerfile`
- `deploy/web.Dockerfile`
- `deploy/Caddyfile`

## Сводка API-контрактов

### Auth
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Public
- `GET /api/v1/public/companies`
- `GET /api/v1/public/catalog/items`
- `POST /api/v1/public/draft-requests`
- `GET /api/v1/public/draft-requests/{draft_code}`

### Operator/Admin
- `GET /api/v1/operator/companies`
- `GET /api/v1/operator/suppliers`
- `GET /api/v1/operator/catalog/items`
- `GET /api/v1/operator/draft-requests`
- `POST /api/v1/operator/draft-requests/{draft_code}/submit`
- `GET /api/v1/operator/requests`
- `POST /api/v1/operator/requests/{request_code}/offers`
- `GET /api/v1/operator/offers`
- `GET /api/v1/operator/offers/{offer_code}`
- `GET /api/v1/operator/requests/{request_code}/offers/compare`
- `POST /api/v1/operator/offers/{offer_code}/revise`
- `POST /api/v1/operator/offers/{offer_code}/send`
- `POST /api/v1/operator/offers/{offer_code}/accept`
- `POST /api/v1/operator/offers/{offer_code}/decline`
- `POST /api/v1/operator/offers/{offer_code}/expire`
- `POST /api/v1/operator/offers/{offer_code}/convert-to-order`
- `GET /api/v1/operator/orders`
- `GET /api/v1/operator/files`
- `GET /api/v1/operator/files/{asset_code}`
- `POST /api/v1/operator/files/upload`
- `POST /api/v1/operator/files/{asset_code}/versions`
- `POST /api/v1/operator/files/{asset_code}/review`
- `POST /api/v1/operator/files/{asset_code}/finalize`
- `GET /api/v1/operator/file-versions/{version_code}/download`
- `GET /api/v1/operator/document-templates`
- `GET /api/v1/operator/documents`
- `GET /api/v1/operator/documents/{document_code}`
- `POST /api/v1/operator/documents/generate`
- `POST /api/v1/operator/documents/{document_code}/send`
- `POST /api/v1/operator/documents/{document_code}/confirm`
- `POST /api/v1/operator/documents/{document_code}/replace`
- `GET /api/v1/operator/document-versions/{version_code}/download`
- `GET /api/v1/operator/comms/threads`
- `POST /api/v1/operator/comms/threads`
- `GET /api/v1/operator/comms/notifications`
- `GET /api/v1/operator/rules`
- `GET /api/v1/operator/rules/{rule_code}/versions`
- `GET /api/v1/operator/reason-codes`
- `GET /api/v1/operator/audit/events`
- `GET /api/v1/operator/timeline/{owner_type}/{owner_code}`
- `GET /api/v1/operator/workbench`
- `GET /api/v1/operator/dashboard/supply`
- `GET /api/v1/operator/dashboard/processing`
- `GET /api/v1/operator/dashboard/summary`
- `GET /api/v1/public/requests/{customer_ref}/dashboard`
- `GET /api/v1/public/requests/{customer_ref}/notifications`
- `GET /api/v1/meta/modules`

### Только admin
- `GET /api/v1/admin/users`
- `POST /api/v1/admin/companies`
- `POST /api/v1/admin/suppliers`
- `POST /api/v1/admin/rules`

## Критичные transition guards

- `draft -> request`: role-restricted, reason required, required-field validation, dual audit event.
- `request -> offer`: role-restricted, reason required, request state check, audit event.
- `offer(current_version_confirmed) -> order`: role-restricted, reason required, confirmed-version check, audit event.

## Files / Documents contour

### Что добавлено в schema
- `FileAsset` как управляемый asset layer на таблице `files_media`
- `FileVersion`
- `FileCheck`
- `Document`
- `DocumentVersion`
- сохранены compatibility-поля `visibility` в `files_media/documents`, но source-of-truth для нового контура теперь `visibility_scope`

### Что добавлено в поведение
- Файлы и документы стали частью единого managed contour вокруг `Request / Offer / Order`, а не "просто прикреплениями рядом".
- Добавлен storage abstraction layer:
  - `LocalFileStorageAdapter`
  - object-storage-ready adapter stub
- Поддержаны:
  - owner object refs
  - `file_type`
  - `version_no`
  - `check_state`
  - `visibility_scope`
  - `final_flag`
- Базовые file checks:
  - `presence`
  - `size`
  - `extension`
  - `type`
  - `manual_review`
- Документы поддерживают:
  - templates
  - generate version
  - `published -> sent -> confirmed -> replaced`
  - owner links
  - role visibility
- Базовые document templates первой волны:
  - `offer_proposal`
  - `offer_confirmation`
  - `invoice_like`
  - `internal_job`
- Request, Offer и Order detail views теперь возвращают связанные managed files/documents и download links.

### Что добавлено в API
- Operator:
  - `GET /api/v1/operator/files`
  - `GET /api/v1/operator/files/{asset_code}`
  - `POST /api/v1/operator/files/upload`
  - `POST /api/v1/operator/files/{asset_code}/versions`
  - `POST /api/v1/operator/files/{asset_code}/review`
  - `POST /api/v1/operator/files/{asset_code}/finalize`
  - `GET /api/v1/operator/file-versions/{version_code}/download`
  - `GET /api/v1/operator/document-templates`
  - `GET /api/v1/operator/documents`
  - `GET /api/v1/operator/documents/{document_code}`
  - `POST /api/v1/operator/documents/generate`
  - `POST /api/v1/operator/documents/{document_code}/send`
  - `POST /api/v1/operator/documents/{document_code}/confirm`
  - `POST /api/v1/operator/documents/{document_code}/replace`
  - `GET /api/v1/operator/document-versions/{version_code}/download`
- Customer/public:
  - `GET /api/v1/public/requests/{customer_ref}/files/{version_code}/download`
  - `GET /api/v1/public/requests/{customer_ref}/documents/{version_code}/download`

### Что добавлено в verification
- новый suite:
  - `tests.test_foundation_files_documents`
- новый smoke:
  - `scripts/foundation_files_documents_smoke_check.sh`

## Что дополнительно доведено после первичного скелета

- Добавлен unified local launcher `scripts/run_foundation_unified.sh`, который поднимает foundation backend и Next.js shell одним запуском.
- Добавлен regression test на authz-ограничения, который подтверждает:
  - `operator` не имеет доступа к admin-route;
  - `customer` не имеет доступа к operator-route;
  - неаутентифицированный запрос получает `401` на role-protected endpoint.
- Устранён doc drift в `README.md`: legacy SQLite больше не описывается как общая production-правда для нового foundation-контура.
- Добавлен `.dockerignore`, чтобы `docker compose build` не тащил в build context локальные `node_modules`, `.venv`, git-метаданные и проектный мусор.
- Исправлен `deploy/Caddyfile`: путь `/platform-api/*` теперь приходит в FastAPI без лишнего префикса, поэтому публичная страница `/login` может логиниться через тот же reverse proxy, что и production-like compose contour.
- Compose contour реально поднят и проверен на локальном macOS host через `colima + docker + docker compose`.
- Выровнен web runtime baseline:
  - `deploy/web.Dockerfile` переведён на `node:22-alpine`;
  - `apps/web/package.json` зафиксирован через `engines.node >=22 <23` и `engines.npm >=10`;
  - live web container после пересборки подтверждён на `Node v22.22.2 / npm 10.9.7`.
- В repo-local skill `skills/operate-platform/SKILL.md` добавлен ресурсный guard:
  - на macOS `Colima` стартует с компактного профиля `--cpu 2 --memory 2 --disk 20`;
  - расширение памяти делается только по фактической необходимости, а не по умолчанию.
- Локальный Docker runtime реально переведён на компактный профиль:
  - `colima list --json` подтверждает `cpus=2`, `memory=2147483648`, `disk=21474836480`;
  - после restart-cycle `docker compose up -d` снова даёт зелёные `health` и `login`;
  - текущий лимит контейнеров — около `1.913GiB`, а не прежние `~5.8GiB`.
- Реальный build-context теперь подтверждён как компактный:
  - `web` собирается с context порядка `1.21MB`;
  - `api` собирается с context порядка `1.41MB`;
  - локальные `node_modules`, `.venv`, `.git`, `data`, skills/docs assets и прочий шум больше не затягиваются в compose-build.
- Default runtime policy доведена до конца:
  - `MAGON_FOUNDATION_LEGACY_ENABLED` теперь по умолчанию `false` в settings, compose и env skeletons;
  - canonical local-up и smoke-check больше не включают legacy bridge автоматически;
  - legacy `/status` и `/ui/*` подтверждены только как opt-in compatibility surface, а не как штатный runtime первой волны.

## Messages / dashboards verification

### Что добавлено в тесты
- новый suite:
  - `tests.test_foundation_events_dashboards`
- покрывает цепочку:
  - event emitted
  - role-scoped visibility
  - notification rule evaluated
  - dashboard metrics updated
  - public payload не тянет operator-only поля

### Что добавлено в smoke
- новый smoke:
  - `scripts/foundation_messages_dashboards_smoke_check.sh`
- проверяет:
  - customer dashboard
  - operator workbench
  - processing dashboard
  - admin dashboard
  - operator timeline по request

## Supplier / Companies business module

### Что добавлено в schema
- `CompanyContact`
- `CompanyAddress`
- `SupplierSourceRegistry`
- `SupplierRawIngest`
- `SupplierRawRecord`
- `SupplierCompany`
- `SupplierSite`
- `SupplierNormalizationResult`
- `SupplierDedupCandidate`
- `SupplierMergeDecision`
- `SupplierVerificationEvent`
- `SupplierRatingSnapshot`

### Что добавлено в поведение
- supplier contour теперь живёт как отдельный первый крупный business-модуль поверх foundation.
- Данные разведены по слоям:
  - `raw`
  - `normalized`
  - `confirmed`
- Добавлен adapter registry через `src/magon_standalone/integrations/foundation/supplier_sources.py`.
- Добавлен рабочий fixture-adapter `fixture_json`.
- Добавлен service-layer `SupplierPipelineService`:
  - import raw records
  - normalize name/contact/location/capability summary
  - dedup against existing confirmed suppliers with confidence score
  - auto-merge уверенных дублей
  - manual-review path для спорных дублей
  - trust progression и verification history
  - rating/load baseline snapshots
- Добавлен Celery task `magon.foundation.suppliers.run_ingest`.

### Что добавлено в API
- Public:
  - `GET /api/v1/public/suppliers`
- Operator/Admin supplier workbench:
  - `GET /api/v1/operator/supplier-sources`
  - `POST /api/v1/admin/supplier-sources`
  - `GET /api/v1/operator/supplier-ingests`
  - `GET /api/v1/operator/supplier-ingests/{ingest_code}`
  - `POST /api/v1/operator/supplier-ingests/run-inline`
  - `POST /api/v1/operator/supplier-ingests/enqueue`
  - `GET /api/v1/operator/supplier-raw`
  - `GET /api/v1/operator/suppliers`
  - `GET /api/v1/operator/suppliers/{supplier_code}`
  - `GET /api/v1/operator/supplier-sites/{site_code}`
  - `GET /api/v1/operator/supplier-dedup-candidates`
  - `POST /api/v1/operator/supplier-dedup-candidates/{candidate_code}/decision`
  - `POST /api/v1/operator/suppliers/{supplier_code}/verify`
  - `POST /api/v1/admin/suppliers`
  - `POST /api/v1/admin/suppliers/{supplier_code}/block`
  - `POST /api/v1/admin/suppliers/{supplier_code}/archive`

### Что добавлено в web shell
- `/suppliers`
- `/suppliers/[supplierCode]`
- `/supplier-sites/[siteCode]`
- `/supplier-ingests/[ingestCode]`
- login теперь сохраняет foundation session token в browser storage для operator/admin workbench.

### Seed / demo
- foundation seed теперь создаёт:
  - fixture source registry
  - один trusted supplier baseline
- добавлен demo script:
  - `scripts/run_supplier_demo_pipeline.py`
- добавлен отдельный smoke:
  - `scripts/foundation_supplier_smoke_check.sh`

## Оставшийся риск после этого шага

- Foundation schema and API are now in place, but current legacy business contour and new foundation contour are not yet deeply reconciled entity-by-entity.

## Catalog / Showcase module

### Что добавлено в schema
- `CatalogItem` расширен до ограниченной wave1-витрины:
  - `category_code`
  - `category_label`
  - `tags_json`
  - `option_summaries_json`
  - `pricing_mode`
  - `pricing_summary`
  - `pricing_note`
  - `catalog_mode`
  - `translations_json`
  - `sort_order`
  - `is_featured`
  - `supplier_company_id`
- `DraftRequest` и `RequestRecord` теперь сохраняют публичный витринный контекст:
  - `catalog_item_id`
  - `customer_phone`
  - `guest_company_name`
  - `locale_code`

### Что добавлено в поведение
- Публичная витрина ограничена curated-набором first-wave позиций и направлений, а не широким каталогом "на всё".
- Поддержаны `mode: ready / config / rfq`.
- Поддержаны `pricing_mode: fixed / from / estimate / rfq`.
- Гостевой вход остаётся без обязательной регистрации.
- Переход из витрины ведёт прямо в `DraftRequest`, а не в отдельный параллельный lead-контур.
- Для публичных форм добавлен lightweight anti-bot:
  - honeypot
  - minimum elapsed time

### Что добавлено в API
- Public:
  - `GET /api/v1/public/catalog/directions`
  - `GET /api/v1/public/catalog/items`
  - `GET /api/v1/public/catalog/items/{item_code}`
  - `POST /api/v1/public/draft-requests` с поддержкой `catalog_item_code`, `customer_phone`, `guest_company_name`, `intake_channel`, `locale_code`, `honeypot`, `elapsed_ms`
- Operator:
  - `GET /api/v1/operator/catalog/items`
  - `GET /api/v1/operator/catalog/items/{item_code}`
  - `POST /api/v1/operator/catalog/items`

### Что добавлено в web shell
- `/catalog`
- `/catalog/[itemCode]`
- `/rfq`
- витрина теперь видна и с главной страницы через отдельный CTA

### Seed / smoke / tests
- Seed теперь поднимает три demo-позиции витрины:
  - транспортная упаковка
  - этикетки
  - сложный RFQ
- Добавлен smoke:
  - `scripts/foundation_catalog_smoke_check.sh`
- Добавлены тесты:
  - `tests.test_foundation_catalog`
  - сценарий `guest can browse -> start draft -> submit RFQ entry point`

## Draft / Request central intake module

### Что добавлено в schema
- `DraftRequest` расширен до отдельного входного слоя:
  - `submitted_request_id`
  - `item_service_context`
  - `city`
  - `geo_json`
  - `source_channel`
  - `draft_status`
  - `requested_deadline_at`
  - `owner_user_id`
  - `assignee_user_id`
  - `last_autosaved_at`
  - `last_customer_activity_at`
  - `abandoned_at`
  - `last_transition_reason_code`
  - `last_transition_note`
- `RequestRecord` выделен как отдельная центральная intake-сущность:
  - `customer_ref`
  - `item_service_context`
  - `source_channel`
  - `city`
  - `geo_json`
  - `requested_deadline_at`
  - `owner_user_id`
  - `assignee_user_id`
  - `last_transition_reason_code`
  - `last_transition_note`
  - `request_status` в новом operator review flow
- Добавлены новые intake-таблицы:
  - `required_fields_state`
  - `intake_file_links`
  - `request_reasons`
  - `request_clarification_cycles`
  - `request_follow_up_items`

### Что добавлено в поведение
- Draft получил отдельный lifecycle:
  - `draft`
  - `awaiting_data`
  - `ready_to_submit`
  - `blocked`
  - `abandoned`
  - `archived`
- Request получил отдельный operator review flow:
  - `new`
  - `needs_review`
  - `needs_clarification`
  - `supplier_search`
  - `offer_prep`
  - `offer_sent`
  - `converted_to_order`
  - `cancelled`
- Добавлен service-layer `RequestIntakeService`:
  - autosave draft
  - required fields recompute
  - stale draft abandonment
  - file-link attachment
  - guarded `draft -> request`
  - blocker/reason registration и resolution
  - clarification cycles
  - follow-up items
  - timeline через audit events
- Переход `draft -> request` теперь возможен только при выполнении обязательных условий и не смешивает статусы request с offer/file/order.
- `offer` и `order` контур приведены к новому request review flow:
  - offer создаётся из `supplier_search` / `offer_prep`
  - send offer переводит request в `offer_sent`
  - request может вернуться из `offer_sent` в `needs_clarification` / `offer_prep` для новой коммерческой версии
  - `converted_to_order` достигается только отдельной конверсией подтверждённой версии offer

### Что добавлено в API
- Public/customer:
  - `POST /api/v1/public/draft-requests`
  - `GET /api/v1/public/draft-requests/{draft_code}`
  - `PATCH /api/v1/public/draft-requests/{draft_code}`
  - `POST /api/v1/public/draft-requests/{draft_code}/file-links`
  - `POST /api/v1/public/draft-requests/{draft_code}/submit`
  - `POST /api/v1/public/draft-requests/{draft_code}/abandon`
  - `GET /api/v1/public/requests/{customer_ref}`
- Operator:
  - `GET /api/v1/operator/draft-requests`
  - `GET /api/v1/operator/draft-requests/{draft_code}`
  - `POST /api/v1/operator/draft-requests/{draft_code}/submit`
  - `POST /api/v1/operator/draft-requests/{draft_code}/transition`
  - `GET /api/v1/operator/requests`
  - `GET /api/v1/operator/requests/{request_code}`
  - `POST /api/v1/operator/requests/{request_code}/transition`
  - `POST /api/v1/operator/requests/{request_code}/reasons`
  - `POST /api/v1/operator/request-reasons/{request_reason_code}/resolve`
  - `POST /api/v1/operator/requests/{request_code}/follow-up-items`
  - `POST /api/v1/operator/follow-up-items/{follow_up_code}/transition`
  - `POST /api/v1/operator/requests/{request_code}/file-links`

### Что добавлено в web shell
- `/drafts/[draftCode]`
- `/requests/[customerRef]`
- `/request-workbench`
- `/request-workbench/[requestCode]`
- Draft editor теперь делает autosave и показывает required fields, file links и timeline.
- Public request page показывает customer-safe view по `customer_ref`.
- Operator workbench показывает request review flow, blocker reasons и follow-up items.

### Seed / smoke / tests
- Foundation seed теперь создаёт demo draft и demo request в `needs_review`.
- Добавлен smoke:
  - `scripts/foundation_request_smoke_check.sh`
- Добавлены тесты:
  - `tests.test_foundation_draft_request`
  - обновлены `tests.test_foundation_api` и `tests.test_foundation_catalog`
  - проверены блокировки submit и blocker-guards на transition.

## Offers module

### Что добавлено в schema
- `OfferRecord` расширен до versioned commercial-layer:
  - `request_ref`
  - `current_version_no`
  - `amount`
  - `currency_code`
  - `lead_time_days`
  - `terms_text`
  - `scenario_type`
  - `supplier_ref`
  - `offer_status`
  - `confirmation_state`
- Добавлены новые offer-таблицы:
  - `offer_versions`
  - `offer_confirmation_records`
  - `offer_comparison_metadata`
  - `offer_critical_change_reset_reasons`
- `OrderRecord` теперь хранит `offer_version_id`, чтобы order ссылался на конкретную подтверждённую коммерческую версию, а не на абстрактный offer.

### Что добавлено в поведение
- Offer живёт отдельным слоем между `Request` и `Order` и не смешивается с их состояниями.
- Одна заявка может иметь один или несколько `OfferRecord`, а каждый `OfferRecord` может иметь несколько версий.
- Добавлен service-layer `OfferService`:
  - create offer
  - revise offer
  - send offer
  - accept / decline / expire confirmation
  - compare payload для оператора и клиента
  - guarded `offer(current_version_confirmed) -> order`
- Критичная правка не мутирует старую версию:
  - создаётся новая версия
  - предыдущая версия помечается `superseded`
  - старая confirmation validity сбрасывается через reset reason и audit trail
- Только подтверждённая конкретная версия может конвертироваться в `Order`.

### Что добавлено в API
- Operator:
  - `GET /api/v1/operator/offers`
  - `GET /api/v1/operator/offers/{offer_code}`
  - `GET /api/v1/operator/requests/{request_code}/offers/compare`
  - `POST /api/v1/operator/requests/{request_code}/offers`
  - `POST /api/v1/operator/offers/{offer_code}/revise`
  - `POST /api/v1/operator/offers/{offer_code}/send`
  - `POST /api/v1/operator/offers/{offer_code}/accept`
  - `POST /api/v1/operator/offers/{offer_code}/decline`
  - `POST /api/v1/operator/offers/{offer_code}/expire`
  - `POST /api/v1/operator/offers/{offer_code}/convert-to-order`
- Public/customer:
  - `GET /api/v1/public/requests/{customer_ref}/offers/compare`
  - `POST /api/v1/public/requests/{customer_ref}/offers/{offer_code}/accept`
  - `POST /api/v1/public/requests/{customer_ref}/offers/{offer_code}/decline`

### Что добавлено в web shell
- Operator request workbench теперь показывает compare-view по вариантам предложения, действия `revise / send / accept / decline / expire / convert-to-order` и историю версий.
- Public request page теперь показывает клиенту только отправленные варианты и позволяет подтвердить или отклонить конкретную текущую версию.

### Seed / smoke / tests
- Foundation seed теперь создаёт demo sent offer на demo request.
- Добавлен smoke:
  - `scripts/foundation_offer_smoke_check.sh`
- Добавлены тесты:
  - `tests.test_foundation_offers`
  - обновлён `tests.test_foundation_api`
  - проверен сценарий `request -> offer v1 -> revise v2 -> old confirmation invalid -> v2 accept -> convert to order`.

## Orders / internal payment skeleton module

### Что добавлено в schema
- `OrderRecord` расширен до отдельного post-offer слоя:
  - `customer_refs_json`
  - `supplier_refs_json`
  - `internal_owner_user_id`
  - `payment_state`
  - `logistics_state`
  - `readiness_state`
  - `refund_state`
  - `dispute_state`
  - `last_transition_reason_code`
  - `last_transition_note`
- Добавлены новые order/payment-таблицы:
  - `order_lines`
  - `payment_records`
  - `internal_ledger_entries`

### Что добавлено в поведение
- `Order` теперь создаётся только из accepted current `OfferVersion`.
- На старте создаётся минимальный bundle:
  - `OrderRecord`
  - минимум одна `OrderLine`
  - один внутренний `PaymentRecord(created)`
  - один ledger entry `payment_expected`
- Поддержаны operator/admin actions:
  - `assign_supplier`
  - `confirm_start`
  - `mark_production`
  - `ready`
  - `delivery`
  - `complete`
  - `cancel`
  - `dispute`
- Поддержаны внутренние payment transitions:
  - `created`
  - `pending`
  - `confirmed`
  - `failed`
  - `partially_refunded`
  - `refunded`
- Каждое критичное действие идёт через guard, reason code и audit event.
- `OrderLine` хранит:
  - `catalog/service ref`
  - `quantity`
  - `line_status`
  - `planned_supplier_ref`
  - `planned_stage_refs`
- Агрегат заказа остаётся лёгким и готов к частичным сценариям:
  - partial readiness
  - partial delivery
  - partial refund
  - dispute

### Что добавлено в API
- Operator:
  - `GET /api/v1/operator/orders`
  - `GET /api/v1/operator/orders/{order_code}`
  - `POST /api/v1/operator/offers/{offer_code}/convert-to-order`
  - `POST /api/v1/operator/orders/{order_code}/action`
  - `POST /api/v1/operator/orders/{order_code}/payments`
  - `POST /api/v1/operator/payment-records/{payment_code}/transition`
- Public/customer:
  - customer request view теперь показывает связанный `order` summary после конвертации

### Что добавлено в web shell
- `/orders`
- `/orders/[orderCode]`
- request detail и customer request page теперь показывают order summary и переход в operator order workbench

### Seed / smoke / tests
- Foundation seed теперь создаёт отдельный demo order через accepted offer version.
- Добавлен smoke:
  - `scripts/foundation_order_smoke_check.sh`
- Добавлены тесты:
  - `tests.test_foundation_orders`
  - обновлены `tests.test_foundation_api` и `tests.test_foundation_offers`
  - проверен сценарий `accepted offer -> order created -> status transitions -> payment updates -> audit intact`.

## Acceptance hardening и эксплуатационный доводочный проход

### Что показал gap-audit

По критериям приёмки из `gpt_doc/codex_wave1_spec_ru.docx` основной бизнес-контур уже был собран, но до приемочного состояния не хватало нескольких эксплуатационных вещей:

- supplier ingest при падении не оставлял устойчивое retryable state, потому что ошибка откатывала транзакцию целиком;
- режимы `maintenance / emergency` были зафиксированы в документации, но не работали как runtime guard;
- архивный контур для managed files/documents был частично описан, но active views ещё не отрезали archived items;
- не было отдельного migration acceptance gate;
- не было одного end-to-end demo smoke на весь путь `supplier -> storefront -> draft -> request -> offer -> order -> file/document -> timeline/dashboard`;
- CI pipeline отставал от фактического foundation scope.

### Что добавлено в schema

- Новая migration `20260417_0009_wave1_acceptance_hardening.py`.
- `SupplierRawIngest` расширен полями:
  - `failed_at`
  - `last_retry_at`
  - `retry_count`
  - `failure_code`
  - `failure_detail`

### Что доведено в runtime

- Введён env-driven system mode:
  - `normal`
  - `test`
  - `maintenance`
  - `emergency`
- `MAGON_FOUNDATION_SYSTEM_MODE` стал частью foundation settings.
- Добавлен middleware guard:
  - в `maintenance` блокируются write-path операции, но health/meta/read endpoints остаются доступны;
  - в `emergency` режется почти весь трафик, кроме health/meta surfaces.
- Health/observability теперь публикуют `system_mode`.
- Добавлен endpoint:
  - `GET /api/v1/meta/system-mode`

### Что доведено в supplier ingest contour

- Inline ingest теперь сохраняет failed state, а не теряет его на rollback.
- В `SupplierRawIngest` пишутся:
  - статус ошибки
  - код исключения
  - detail ошибки
  - время падения
  - счётчик retry
- Добавлен ручной retry path:
  - `POST /api/v1/operator/supplier-ingests/{ingest_code}/retry`
- Retry умеет:
  - очищать старые raw/normalized/dedup rows этого ingest-run
  - увеличивать `retry_count`
  - повторно прогонять ingest inline или через job path
- Fixture supplier adapter теперь поддерживает управляемый demo-failure через `force_error`, чтобы failure/retry состояние можно было проверять тестом и smoke.

### Что доведено в archive behavior

- Active views по files/documents теперь исключают archived items, а не только deleted.
- Добавлены operator actions:
  - `POST /api/v1/operator/files/{asset_code}/archive`
  - `POST /api/v1/operator/documents/{document_code}/archive`
- Архивация:
  - сохраняет причину
  - оставляет audit trail
  - для document version переводит текущую версию в `archived`, если она была активной

### Что добавлено в automated checks

- Unit/API:
  - `tests.test_foundation_acceptance`
  - `tests.test_foundation_migrations`
- Acceptance tests теперь отдельно проверяют:
  - maintenance mode blocking
  - supplier ingest failed -> retry -> completed
  - archive hiding для files/documents
- Добавлены отдельные gates:
  - `scripts/foundation_migration_check.sh`
  - `scripts/foundation_wave1_demo_smoke_check.sh`
- Demo smoke прогоняет end-to-end сценарий:
  - supplier ingest -> normalized supplier
  - storefront -> draft
  - draft -> request
  - request -> versioned offer
  - accepted offer -> order
  - file/document flow
  - timeline/audit/dashboard visibility

### Что добавлено в CI / quality gates

- `.github/workflows/ci.yml` обновлён под актуальный foundation contour.
- В CI теперь отдельно гоняются:
  - foundation quality gate через `./scripts/verify_workflow.sh`
  - migration check
  - foundation smoke pack
  - web lint/typecheck/build
- `scripts/verify_workflow.sh` расширен до фактического wave1 suite, включая:
  - suppliers
  - catalog
  - draft/request
  - offers
  - orders
  - files/documents
  - events/dashboards
  - acceptance
  - migrations

### Что подтверждено после hardening-прохода

- запрещённые переходы и explainability guards остаются зелёными;
- role access boundaries не размыты;
- archive/soft-delete не ломают active выдачи;
- async supplier ingest имеет устойчивые failure/retry states;
- environment boot остаётся консистентным через migration/seed/api/web/smoke path;
- wave1 contour теперь можно демонстрировать целиком без ручного "доклеивания" пробелов по runtime.

## Доведение по обновлённой wave1-спецификации и frontend cleanup

### Что было найдено

- `gpt_doc/` реально содержит только один активный planning source-of-truth для wave1: `codex_wave1_spec_ru.docx` плюс PDF-экспорт той же спецификации.
- Часть backend status/default mappings отставала от обновлённой терминологии спецификации:
  - supplier `candidate/reviewing/approved`
  - offer `prepared`
  - order `created/confirmed_start`
  - file `pending_review/approved/rejected`
- В frontend ещё торчали сырые status/value куски и англо-ярлыки в request/order/dashboard/supplier surfaces.
- Public marketing surface отсутствовал как отдельная conversion-area, хотя по спецификации нужен лёгкий внешний слой вокруг showcase/RFQ/draft.

### Что было доведено

- Добавлена migration `20260417_0010_wave1_status_language_alignment` с backfill под обновлённые статусы первой волны.
- Backend выровнен под wave1 status map:
  - `Supplier` / `SupplierCompany`: `discovered -> normalized -> contact_confirmed -> capability_confirmed -> trusted`
  - `Offer`: `draft -> sent -> awaiting_confirmation -> revised -> accepted / declined / expired`
  - `Order`: `awaiting_confirmation / awaiting_payment / paid / supplier_assigned / in_production / partially_ready / ready / in_delivery / completed / cancelled / disputed`
  - `File`: `uploaded / checking / passed / failed / needs_manual_review / approved_final`
- Rules/guards и tests приведены к той же терминологии без смешивания старых и новых status-code.
- Добавлен единый display-layer `apps/web/lib/foundation-display.ts`, чтобы страницы больше не светили raw status-code и service fallbacks напрямую.
- Перечищены customer/operator/supplier dashboards, request detail/public view, draft editor, order detail/list и supplier surfaces:
  - статусы, причины, visibility и даты стали human-readable;
  - убраны заметные англо/raw fragments;
  - payment/logistics/order labels выровнены по новой модели.
- Добавлен отдельный public marketing route `/marketing` как лёгкий conversion-layer первой волны без создания нового большого модуля.
- На web добавлен `app/icon.svg`, чтобы публичный слой не шумел 404 по favicon в живом browser-pass.
- Runtime/docs truth синхронизированы с фактическим содержимым `gpt_doc/` без ссылок на несуществующие planning-docs.

### Что проверено

- PASS `./scripts/verify_workflow.sh --with-web`
- PASS `cd apps/web && npm run lint`
- PASS `cd apps/web && npm run build`
- PASS `./.venv/bin/python -m unittest tests.test_foundation_offers tests.test_foundation_orders tests.test_foundation_files_documents`
- PASS browser sanity pass:
  - `http://127.0.0.1:3000/marketing`
  - console without page errors after icon fix
  - navigation and key CTA surfaces rendered

## 2026-04-18 — Hourly launcher watchdog

### Что было найдено

- `Start_Platform.command` уже поднимал wave1 runtime корректно.
- Реальная проблема была в том, что у проекта был periodic smoke/observability layer, но не было отдельного self-heal guard, который мягко вернёт launcher после локального падения.
- Пользовательский запрос был именно про часовой refresh launcher-а, а не про ещё одну inbox-проверку.

### Что было доведено

- Добавлен safe watchdog runner `scripts/run_launcher_watchdog.py`.
- Watchdog проверяет:
  - `GET /health/ready`
  - `GET /login`
- Если runtime жив, watchdog ничего не делает.
- Если runtime мёртв, watchdog запускает:
  - `./Start_Platform.command --detach --no-open --keep-db --no-seed`
- Добавлен отдельный macOS LaunchAgent layer:
  - `scripts/install_launchd_launcher_watchdog.sh`
  - `scripts/launchd_launcher_watchdog_status.sh`
  - `scripts/render_launchd_launcher_watchdog.py`
  - `src/magon_standalone/launchd_launcher_watchdog.py`
- Новый guard включён в `scripts/verify_workflow.sh` и покрыт тестом `tests.test_launchd_launcher_watchdog`.
- Одновременно исправлен `scripts/platform_smoke_check.sh`, чтобы он проверял живой wave1 contour вместо устаревших `/status` и `/ui/companies` как обязательных public probes.

### Что проверено

- PASS `./.venv/bin/python -m unittest tests.test_launchd_launcher_watchdog`
- PASS `./.venv/bin/python scripts/run_launcher_watchdog.py`
- PASS `./scripts/install_launchd_launcher_watchdog.sh --interval 3600`
- PASS `./scripts/launchd_launcher_watchdog_status.sh`
- PASS `./scripts/verify_workflow.sh`

## 2026-04-18 — UI cleanup for clickable dashboards and clean RU shell

### Что было найдено

- В `admin/operator` dashboard-карточках уведомления, блокировки и части счётчиков оставались фактически информационными: перейти в заявку, заказ или поставщика было нельзя или неудобно.
- Верхняя шапка была перегружена: все разделы, язык, палитра, тема и session-block одновременно висели в одной строке.
- В русскоязычном UI ещё торчали смешанные формулировки вроде `login`, `intake`, `backend`, `request contour`, `Foundation auth`, а на admin-срезе метрики светили raw ключами `users`, `rules`, `message_events`.

### Что было доведено

- Dashboard-карточки стали интерактивными:
  - уведомления ведут в `request-workbench`, `orders` или `suppliers` по entity payload;
  - блокировки и просрочки ведут в owning object;
  - count-карточки получили прямые переходы в соответствующий рабочий раздел;
  - supply-карточки поставщиков открывают detail page.
- Backend dashboard payload для overdue offer confirmation теперь отдаёт `request_ref`, чтобы фронт мог строить корректный переход из карточки.
- Шапка собрана заново без расползания:
  - в верхней строке оставлены только ключевые разделы;
  - вторичные разделы и все переключатели убраны в панель `Ещё`;
  - session-chip стал компактным и читаемым.
- Login screen и связанные auth-блоки переведены на нормальные русские подписи.
- `apps/web/messages/ru.json` и `apps/web/messages/en.json` выровнены под новый header contract и очищены от наиболее заметных смешанных UI-формулировок.

### Что проверено

- PASS `cd apps/web && npm run lint`
- PASS `cd apps/web && npm run typecheck`
- PASS `cd apps/web && npm run build`
- PASS `./scripts/verify_workflow.sh --with-web`
- PASS browser pass через Playwright CLI:
  - `http://127.0.0.1:3000/login`
  - `Ещё` открывает secondary navigation и interface controls
  - login ведёт в рабочий контур
  - `http://127.0.0.1:3000/admin-dashboard`
  - клик по административному уведомлению переводит в `request-workbench/{requestCode}`

## 2026-04-18 — Wave1 audit: supplier parsing source restored as a first-class ingest option

### Что было найдено

- Спецификация первой волны требует supplier-модуль с `источники, парсинг, сырой слой, нормализация`, но foundation runtime фактически сидел только на seeded `fixture_json`.
- Нормализация, dedup и trust progression уже существовали; реальный разрыв был именно в source layer и operator UX выбора источника.
- `/suppliers` всегда запускал первый источник, поэтому parsing как отдельная опция в интерфейсе по сути отсутствовал.

### Что было доведено

- Добавлен supplier source adapter `scenario_live` поверх существующего `supplier_intelligence` discovery layer.
- В seed foundation добавлен второй source registry для live parsing рядом с fixture source.
- В панели `/suppliers` оператор теперь явно выбирает источник ingest и видит, это repeatable fixture ingest или live parsing.
- Backend-покрытие расширено тестом, который доказывает, что seeded live parsing source проходит через foundation ingest contour.

### Что проверено

- PASS `./.venv/bin/python -m unittest tests.test_foundation_suppliers`
- PASS `cd apps/web && npm run lint`
- PASS `cd apps/web && npm run typecheck`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — Final UI cleanup for operator shell and RU wording

### Что было найдено

- В интерфейс всё ещё попадали служебные и англоязычные хвосты: `RU:` пояснения в JSX, `Request`, `Offer`, `Raw layer`, `Dedup review`, `login`, `session token`, `ingest jobs`.
- На основных операторских поверхностях это делало экран похожим на промежуточную сборку, а не на пригодный рабочий продукт.
- Повторный browser-pass показал, что проблема была не в одном экране `/suppliers`, а в группе связанных экранов: `request-workbench`, `orders`, `supplier-ingests`, `suppliers/{code}`, `supplier-sites/{code}`, home shell.

### Что было доведено

- Вычищены пользовательские тексты в:
  - `request-workbench`
  - `request-workbench/{requestCode}`
  - `orders`
  - `orders/{orderCode}`
  - `suppliers`
  - `supplier-ingests/{ingestCode}`
  - `suppliers/{supplierCode}`
  - `supplier-sites/{siteCode}`
  - `drafts/{draftCode}`
  - home marketing-operational shell
- `RU:` объяснения оставлены только в кодовых комментариях и больше не рендерятся в UI.
- Англоязычные рабочие термины заменены на единый русский слой:
  - `login` -> `вход`
  - `Request / Offer / Draft` -> `заявка / предложение / черновик`
  - `Raw layer / Dedup review` -> `первичный слой / разбор дублей`
  - `ingest jobs` -> `запуски импорта`
- Header, `Ещё`-панель и операторские экраны повторно просмотрены в браузере после сборки.

### Что проверено

- PASS `cd apps/web && npm run lint`
- PASS `cd apps/web && npm run typecheck`
- PASS `cd apps/web && npm run build`
- PASS `./scripts/verify_workflow.sh --with-web`
- PASS browser pass через Playwright CLI:
  - `http://127.0.0.1:3000/`
  - `http://127.0.0.1:3000/request-workbench`
  - `http://127.0.0.1:3000/orders`
  - `http://127.0.0.1:3000/suppliers`
  - `http://127.0.0.1:3000/supplier-ingests/ING-00001`
  - раскрытие `Ещё` и проверка secondary navigation/session block

## 2026-04-18 — product-shell справка по сущностям и зависимостям

### Что было найдено

- В проекте уже были runtime docs и карта архитектуры, но не было одного короткого shell-entry, который объясняет сущности, зависимости и рабочие маршруты прямо внутри продукта.
- Новому участнику проекта приходилось прыгать между `gpt_doc`, `current-project-state` и кодом, чтобы понять, где живёт конкретная сущность и какой экран ей владеет.

### Что было доведено

- Добавлена встроенная product-shell страница `/reference`.
- На странице собраны:
  - ключевые сущности первой волны;
  - зависимые слои и boundaries;
  - роли и соответствующие маршруты;
  - список того, что сознательно не входит в wave1.
- Добавлен отдельный русский документ `docs/ru/platform-entity-reference.md`.
- `docs/current-project-state.md` и `docs/ru/current-project-state.md` теперь явно ссылаются на новую справку.

### Что проверено

- PASS `cd apps/web && npm run lint`
- PASS `cd apps/web && npm run typecheck`
- PASS `cd apps/web && npm run build`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — fault pass for wrapper/runtime tooling

### Что было найдено

- `scripts/run_playwright_cli.sh` регрессировал после chrome-only фиксации: meta-команда `list` получала лишний `--browser=chrome` и падала с `Unknown option: --browser`.
- Основной product contour при этом оставался зелёным; сбой был в operator/tooling слое, а не в foundation API или web shell.

### Что было доведено

- Browser wrapper теперь различает browser-driven команды и meta-команды.
- `--browser=chrome` автоматически добавляется только туда, где это действительно допустимо.
- Команды `list`, `close-all`, `kill-all`, `--help` и похожие meta-path больше не ломаются из-за chrome-only policy.
- Detached launcher дополнительно ужесточён через `nohup + disown`, чтобы локальный desktop shell не резал child-процессы сразу после выхода convenience launcher.

### Что проверено

- PASS `bash scripts/run_playwright_cli.sh list`
- PASS `bash scripts/run_playwright_cli.sh --help`
- PASS `bash scripts/run_playwright_cli.sh --browser=firefox --help`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — detached launcher fixed through double-fork daemon helper

### Что было найдено

- Подтверждённый operational bug жил в `Start_Platform.command --detach`: backend и web успевали стартовать, но потом умирали вместе с родительским shell-процессом.
- Попытка увести detached runtime в `launchd` не подошла для этого repo-path: процессы упирались в системное ограничение `getcwd: Operation not permitted`.
- Отдельно обнаружился drift в `scripts/verify_workflow.sh`: он ошибочно гонял `bash -n` по Python helper-файлу.

### Что было доведено

- Добавлен `scripts/run_detached_command.py` с double-fork daemonization.
- Detached-ветка `Start_Platform.command` переведена на новый helper вместо `nohup`/launchd-обходов.
- `scripts/verify_workflow.sh` очищен от ошибочного `bash -n` по Python helper.

### Что проверено

- PASS `./Start_Platform.command --detach --no-open --keep-db --no-seed`
- PASS повторные HTTP-проверки после выхода launcher shell:
  - `http://127.0.0.1:8091/health/ready` -> `200` через 6 и 18 секунд
  - `http://127.0.0.1:3000/login` -> `200` через 6 и 18 секунд
- PASS `ps` по backend/web pid показал `PPID 1`, то есть detached-процессы переживают завершение launcher shell
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — active runtime switched to Postgres-first and donor wording cleaned up

### Что было найдено

- Активные docs уже декларировали контур `PostgreSQL + Redis + Celery`, но локальные defaults всё ещё молча падали назад в SQLite.
- В пользовательском copy и policy-слое оставались явные упоминания Odoo/legacy-Odoo, хотя текущий standalone repo должен говорить только про donor/back-office boundary.
- После status-language alignment финальный wave1 demo smoke продолжал слать старое состояние `approved` в ручную проверку файла, тогда как сервис уже принимал `passed`.

### Что было доведено

- Local-up контур переведён на Postgres-first defaults:
  - `Start_Platform.command`
  - `scripts/run_foundation_unified.sh`
  - `scripts/run_foundation_migrations.sh`
  - `src/magon_standalone/foundation/settings.py`
  - `alembic.ini`
- Добавлены infra/helpers:
  - `scripts/ensure_foundation_infra.sh`
  - `scripts/reset_foundation_database.py`
  - `scripts/manage_temp_foundation_db.py`
- `docker-compose.yml` теперь публикует локальные host ports `5432` и `6379`, чтобы host-run backend не зависел от внутриконтейнерных адресов.
- Smoke/migration/demo checks переведены на временные PostgreSQL базы вместо ad-hoc SQLite файлов.
- Policy/docs/UI copy очищены от Odoo wording в пользу donor / legacy back-office boundary.
- Исправлены Postgres-specific миграционные drift’ы:
  - boolean backfill в `20260417_0010`
  - JSON payload backfill в `20260417_0008`
- Исправлен final demo-path: file review теперь использует `target_state=passed`, а не устаревшее `approved`.

### Что проверено

- PASS `bash -n Start_Platform.command scripts/run_foundation_unified.sh scripts/run_foundation_migrations.sh scripts/ensure_foundation_infra.sh scripts/foundation_smoke_check.sh scripts/foundation_migration_check.sh scripts/foundation_wave1_demo_smoke_check.sh scripts/verify_workflow.sh`
- PASS `psql postgresql://magon:magon@127.0.0.1:5432/postgres -c 'select 1'`
- PASS `./scripts/foundation_migration_check.sh`
- PASS `bash ./scripts/foundation_smoke_check.sh`
- PASS `./scripts/foundation_wave1_demo_smoke_check.sh`
- PASS `./Start_Platform.command --detach --no-open --keep-db --no-seed`
- PASS `cd apps/web && npm run build`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — minimal LLM connection prepared for explainable supplier parsing fallback

### Что было найдено

- В `supplier_intelligence` уже существовал `ai_assisted` fallback, но он фактически опирался только на Crawl4AI/plaintext и не имел реального LLM transport.
- В репозитории не было operator-visible status/test surface для LLM, поэтому даже корректно заданный API key было бы трудно проверить без ручного дебага кода.

### Что было доведено

- Добавлен env-gated OpenAI adapter в integrations-layer.
- Foundation settings и `.env*.example` получили явные LLM env keys.
- `ai_assisted` extraction теперь сначала пытается использовать LLM preview, но при любом сбое остаётся на explainable fallback path и не роняет supplier parsing contour.
- Добавлен операторский API:
  - `GET /api/v1/operator/llm/status`
  - `POST /api/v1/operator/llm/extract-preview`
- LLM wiring включён в канонический verify path через отдельный unit/API тест.

### Что проверено

- PASS `./.venv/bin/python -m unittest tests.test_foundation_llm`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — permanent supplier parser/classifier wired into repo-aware scheduler

### Что было найдено

- В foundation уже существовали `scenario_live` source registry, queued ingest state и Celery task `magon.foundation.suppliers.run_ingest`, но не было постоянного repo-owned scheduler слоя, который бы ставил live parsing/classification в очередь без ручного клика.
- Operator API показывал health/latest ingest, но не отдавал schedule/classification state: было не видно, какой source идёт постоянно, когда следующее окно и включён ли LLM-assisted fallback.

### Что было доведено

- Добавлен foundation scheduler layer:
  - `src/magon_standalone/foundation/supplier_scheduler.py`
  - считает due-window по source config
  - держит fixture source manual-only
  - по умолчанию ставит `scenario_live` в очередь каждые `60` минут
- Добавлен repo-aware runner:
  - `scripts/run_supplier_scheduler.py`
- Добавлен macOS launchd operating-layer:
  - `src/magon_standalone/launchd_supplier_scheduler.py`
  - `scripts/render_launchd_supplier_scheduler.py`
  - `scripts/install_launchd_supplier_scheduler.sh`
  - `scripts/launchd_supplier_scheduler_status.sh`
- `SupplierSourceRegistry` API теперь отдаёт:
  - `schedule.enabled`
  - `schedule.interval_minutes`
  - `schedule.next_run_at`
  - `schedule.skip_reason`
  - `classification.mode`
  - `classification.llm_enabled`
- Bootstrap/seed now enforce schedule defaults:
  - `fixture_json`: `schedule_enabled=false`
  - `scenario_live`: `schedule_enabled=true`, `schedule_interval_minutes=60`, `classification_mode=ai_assisted_fallback`

### Что проверено

- PASS `./.venv/bin/python -m unittest tests.test_supplier_scheduler`
- PASS `./.venv/bin/python scripts/run_supplier_scheduler.py`
- PASS `./scripts/install_launchd_supplier_scheduler.sh --interval 3600`
- PASS `./scripts/launchd_supplier_scheduler_status.sh`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-18 — repeatable foundation seed fixed on PostgreSQL

### Что было найдено

- После включения постоянного scheduler-а оставался operational drift в полном bootstrap path:
  - `./scripts/run_foundation_migrations.sh && ./.venv/bin/python scripts/seed_foundation.py`
  - `./Start_Platform.command --detach --no-open`
- `reserve_code()` ошибочно принимал специальные scope вроде `users:USR` и `request_customer_refs` за имена SQL-таблиц.
- На PostgreSQL это абортировало транзакцию ещё до корректного insert/update `FoundationSequence`, поэтому repeatable seed ломался даже при уже рабочем runtime.

### Что было доведено

- В `src/magon_standalone/foundation/codes.py` добавлен явный `scope -> table/column` mapping:
  - `users:* -> users_access_users.code`
  - `request_customer_refs -> requests.customer_ref`
  - обычные table-bound scope продолжают идти через `table.code`
- Legacy lookup теперь выполняется только для валидного table-bound scope и обёрнут в nested transaction/savepoint, чтобы Postgres не ронял весь outer transaction.
- Добавлен regression-test:
  - `tests/test_foundation_seed_repeatable.py`
- Канонический `verify_workflow.sh` теперь включает этот repeatable-seed test в общий repo gate.

### Что проверено

- PASS `./.venv/bin/python -m unittest tests.test_foundation_seed_repeatable`
- PASS `./scripts/run_foundation_migrations.sh && ./.venv/bin/python scripts/seed_foundation.py`
- PASS `./Start_Platform.command --detach --no-open`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-22 — readiness and CI parity fixed for blank Redis env

### Что было найдено

- GitHub Actions run `24773174396` падал в `tests.test_foundation_api.TestFoundationApi.test_health_and_login_flow`.
- `/health/ready` возвращал `degraded` вместо `ok`.
- Root cause был в `src/magon_standalone/foundation/settings.py`:
  - helper `_env()` трактовал пустую строку как отсутствие env;
  - test/smoke-контуры выставляли `MAGON_FOUNDATION_REDIS_URL=""`, ожидая явное отключение Redis;
  - в CI это молча откатывалось на `redis://127.0.0.1:6379/0`, и readiness становился degraded.

### Что было доведено

- Добавлен отдельный helper `_env_allow_blank()` для env-переменных, где пустое значение является осознанным operational сигналом.
- `MAGON_FOUNDATION_REDIS_URL`, `MAGON_FOUNDATION_CELERY_BROKER_URL` и `MAGON_FOUNDATION_CELERY_RESULT_BACKEND` теперь читаются через `_env_allow_blank()`.
- Пустой Redis env снова означает `disabled` для test/smoke-контуров, а не возврат к локальному default.

### Что проверено

- PASS `./.venv/bin/python -m unittest tests.test_foundation_api.TestFoundationApi.test_health_and_login_flow`
- PASS `./.venv/bin/python -m unittest tests.test_foundation_api tests.test_foundation_seed_repeatable`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-22 — CI smoke scripts detached from repo-local venv

### Что было найдено

- GitHub Actions run `24790147241` больше не падал на readiness, но всё ещё ломался в `./scripts/foundation_smoke_check.sh`.
- Root cause был в старых smoke/migration scripts:
  - они жёстко вызывали `./.venv/bin/python` и `./.venv/bin/alembic`;
  - локально это работало из-за repo venv;
  - на GitHub runner repo venv отсутствовал, поэтому create-temp-db шаг не стартовал и `DATABASE_URL` оставался пустым.

### Что было доведено

- Во все foundation smoke/migration scripts добавлен единый fallback:
  - сначала используется repo `.venv`, если он есть;
  - иначе скрипт явно переключается на `python3` или `python`;
  - alembic теперь вызывается через `python -m alembic`, а не через жёсткий бинарник внутри `.venv`.
- Это выровняло CI behavior с уже исправленным `verify_workflow.sh`: smoke теперь падает только по продуктовой причине, а не по пути к Python.

### Что проверено

- PASS `bash -n scripts/foundation_smoke_check.sh scripts/foundation_catalog_smoke_check.sh scripts/foundation_request_smoke_check.sh scripts/foundation_offer_smoke_check.sh scripts/foundation_order_smoke_check.sh scripts/foundation_supplier_smoke_check.sh scripts/foundation_files_documents_smoke_check.sh scripts/foundation_messages_dashboards_smoke_check.sh scripts/foundation_migration_check.sh scripts/foundation_wave1_demo_smoke_check.sh`
- PASS `./scripts/verify_workflow.sh --with-web`

## 2026-04-22 — GitHub default branch and branch protections realigned

### Что было найдено

- GitHub UI показывал красный верхний контур не потому, что `main` сломан, а потому что default branch оставался `develop`.
- У `develop` висели устаревшие required checks:
  - `python-tests`
  - `smoke-runtime`
  - `web-build`
- Эти имена уже не публиковались текущим workflow, поэтому GitHub рисовал постоянный ложный красный статус.

### Что было доведено

- Default branch возвращён на `main`.
- Branch protection для `main` и `develop` выровнена на живые checks:
  - `foundation-quality`
  - `foundation-smoke`
  - `web-quality`
- Старый конфликтный PR `main -> develop` закрыт как неактуальный после возврата `main` в роль основной ветки.

### Что проверено

- PASS `gh repo view --json defaultBranchRef`
- PASS `gh api repos/AntonMagon/MagonOS-Standalone/branches/main/protection`
- PASS `gh api repos/AntonMagon/MagonOS-Standalone/branches/develop/protection`
