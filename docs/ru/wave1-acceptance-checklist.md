# Чеклист приёмки wave1

## Назначение

Этот файл фиксирует gap-audit между `gpt_doc/codex_wave1_spec_ru.docx` и фактической standalone-реализацией.
Статусы:

- `FULL`: реализовано и проверено кодом/тестом/smoke
- `PARTIAL`: контур есть, но намеренно ограничен для wave1
- `POST-WAVE-1`: сознательно отложено

## Аудит до hardening-прохода

До текущего шага в репозитории уже были:

- supplier ingest / normalization / dedup contour
- storefront + draft/request/offer/order chain
- files/documents contour
- message/rules/dashboard contour

Главные незакрытые эксплуатационные риски были такими:

- failure/retry состояние supplier ingest не переживало rollback и не оставляло надёжный retryable след
- maintenance/emergency mode оставались в документации, но не в runtime guard
- архивный контур для managed files/documents был неполным: поля были, но активные выдачи не умели исключать archived items
- не было одного demo-smoke потока на весь wave1 contour
- CI был отстающим по scope и не закрывал текущий foundation contour целиком
- migration check не был вынесен в явный acceptance gate

## Критерии приёмки из спецификации

### 1. Поставщики собираются и хранятся через управляемый контур парсинга и нормализации

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_suppliers`
  - `scripts/foundation_supplier_smoke_check.sh`
  - `scripts/foundation_wave1_demo_smoke_check.sh`

### 2. Витрина показывает ограниченный набор направлений и принимает черновики/заявки

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_catalog`
  - `tests.test_foundation_draft_request`
  - `scripts/foundation_request_smoke_check.sh`

### 3. Черновик не переходит дальше без обязательных условий

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_draft_request::test_draft_blocks_submit_until_required_fields_are_filled`

### 4. Для заявки можно создать версионное предложение

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_offers`
  - `scripts/foundation_offer_smoke_check.sh`

### 5. Подтверждённое предложение переводится в заказ без потери истории

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_orders`
  - `scripts/foundation_order_smoke_check.sh`
  - timeline/audit checks в `tests.test_foundation_api`

### 6. Файлы и документы имеют версии и ролевую видимость

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_files_documents`
  - `tests.test_foundation_acceptance::test_archive_hides_file_and_document_from_active_views`
  - `scripts/foundation_files_documents_smoke_check.sh`

### 7. Есть сквозная хронология, причины и аудит по ключевым объектам

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_events_dashboards`
  - `scripts/foundation_messages_dashboards_smoke_check.sh`
  - `scripts/foundation_wave1_demo_smoke_check.sh`

### 8. Есть минимальные ролевые рабочие столы

- Статус: `FULL`
- Покрытые поверхности:
  - customer dashboard
  - operator workbench
  - admin dashboard
  - supply dashboard
  - processing dashboard

### 9. Есть базовые дашборды по supply-side и статусу обработки

- Статус: `FULL`
- Доказательство:
  - `tests.test_foundation_events_dashboards`
  - `scripts/foundation_messages_dashboards_smoke_check.sh`
  - `scripts/foundation_wave1_demo_smoke_check.sh`

## Обязательные платформенные контуры

### Аудит и единая хронология

- Статус: `FULL`

### Причины действий и explainability

- Статус: `FULL`
- Примечание: explainability payload реализован для critical transitions и rule violations, а не как отдельный тяжёлый DSL/runtime.

### Версии предложений, файлов и документов

- Статус: `FULL`

### Ролевые дашборды и рабочие столы

- Статус: `FULL`

### Эскалации и внутренние нормативы реакции

- Статус: `PARTIAL`
- Что есть:
  - baseline `EscalationHint`
  - overdue/blocked buckets в dashboards
- Что намеренно не делается в wave1:
  - отдельный scheduler
  - pager-duty стиль orchestration
  - внешние escalation channels

### Мягкое удаление и архивный контур

- Статус: `PARTIAL`
- Что есть:
  - soft-delete/archival поля на foundation entities
  - auto-archive draft after submit
  - supplier archive
  - file/document archive с исключением из active views
- Что остаётся ограничением:
  - нет полного операционного archive UI/API для всех сущностей wave1

### Локальная, тестовая и боевая среды

- Статус: `FULL`
- Доказательство:
  - `docs/ru/foundation-runbook.md`
  - health/readiness
  - smoke scripts
  - CI pipeline

### Режимы системы: обычный / тестовый / обслуживание / аварийный

- Статус: `PARTIAL`
- Что есть:
  - env-driven `MAGON_FOUNDATION_SYSTEM_MODE`
  - `GET /api/v1/meta/system-mode`
  - maintenance write-guard
  - emergency read/write clamp с сохранением health/meta
- Что не делается:
  - сложная feature-by-feature degradation matrix

### Контур секретов и безопасной конфигурации

- Статус: `PARTIAL`
- Что есть:
  - env-based config
  - explicit integrations layer
  - no hard requirement on external secret manager in wave1

### Встроенные подсказки, демо и онбординг

- Статус: `PARTIAL`
- Что есть:
  - seeded users/data
  - demo smoke script
  - runbook
- Что не делается:
  - отдельный onboarding product surface

## Что сознательно остаётся post-wave-1

- полный supplier portal
- официальный широкий payment-core
- склад и локальные запасы
- MES / production planning
- heavy AI contour
- vector DB как обязательное ядро
- full-country/full-channel matrix
- внешние notification channels как обязательный слой

Подробный список оставленных ограничений вынесен в `docs/ru/wave1-known-limitations.md`.

## Итог приёмочного статуса

- `FULL`: core supplier/storefront/draft/request/offer/order/files/documents/timeline/dashboard contour
- `PARTIAL`: escalation, archive breadth, system modes breadth, secret-management depth, onboarding
- `POST-WAVE-1`: всё, что расширяет систему за пределы управляемого foundation contour первой волны
