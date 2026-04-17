# Foundation architecture as built

## Контур

Первая волна реализована как **modular monolith** на FastAPI + SQLAlchemy + Alembic.
Ключевой принцип сохранён:

- `Draft`
- `Request`
- `Offer`
- `Order`

Это четыре разные сущности с разными статусами, журналом причин и transition-guards.

## Модульная карта

- `UsersAccess`: роли, сессии, auth/authz
- `Companies`: confirmed business entities
- `Suppliers`: raw -> normalized -> confirmed supplier contour
- `Catalog`: ограниченная витрина и intake entry points
- `DraftsRequests`: черновики, заявки, follow-up, blockers, clarification
- `Offers`: versioned commercial offers
- `Orders`: thin orchestration layer после accepted offer
- `FilesMedia`: managed file assets и file versions
- `Documents`: generated managed documents и document versions
- `Comms`: threads, events, notifications
- `RulesEngine`: explainable transition/critical-action checks
- `AuditDashboards`: unified timeline, reason displays, role workbenches, dashboards

## Главная цепочка wave1

`storefront -> draft -> request -> offer(versioned) -> accepted offer -> order`

Дополнительные боковые контуры:

- `supplier ingest -> raw -> normalization -> dedup -> confirmed supplier`
- `request/offer/order -> managed files/documents`
- `audit -> message events -> role-scoped notifications -> dashboards`

## Границы представлений

Слой представлений разделён намеренно:

- public/customer view
- internal operator/admin view
- supplier-facing visibility scope

Это реализовано не через один универсальный DTO, а через отдельные view-модели и role-scoped выдачи.

## Adapter / integrations boundary

Внешние интеграции не зашиваются в ядро.
Используется отдельный слой:

- `src/magon_standalone/integrations/foundation/*`

В текущей wave1 это особенно важно для:

- supplier source adapters
- storage adapters
- optional legacy bridge

## Explainability-first automation

Automation в первой волне не считается "чёрным ящиком".
Критичные автоматизированные решения обязаны иметь:

- `reason_code`
- audit event
- explainability payload
- role restriction

RulesEngine сейчас покрывает:

- transition guards
- blocker reasons
- critical action checks
- versioned rule metadata

## Timeline и сообщения

Source-of-truth для критичных переходов остаётся `AuditEvent`.
Поверх него построен `MessageEvent` слой для:

- unified timeline
- role-scoped visibility
- notification rules
- dashboard metrics

Это intentionally не отдельный distributed event bus.

## Async contour

В первой волне async контур минимальный:

- Celery task для supplier ingest
- явные failure state / retry state в `SupplierRawIngest`
- ручной retry path через API

Это закрывает демонстрационный и операционный минимум, не превращая wave1 в тяжёлый orchestration platform.

## System mode contour

В runtime введён минимальный operational switch:

- `normal`
- `test`
- `maintenance`
- `emergency`

Что он делает сейчас:

- публикуется через `/api/v1/meta/system-mode`
- отражается в health/observability
- блокирует write-path в `maintenance`
- режет почти весь трафик кроме health/meta в `emergency`

## Архивный контур

Важные объекты не должны физически стираться из истории.
В wave1 подтверждены рабочие archival paths для:

- auto-archive draft after submit
- supplier archive
- file archive
- document archive

При этом active views исключают archived items, а audit trail остаётся.

## Что intentionally не строилось

- микросервисы
- marketplace-wide orchestration
- full supplier portal
- heavy payment-core
- склад / MES
- mandatory vector search / heavy AI
