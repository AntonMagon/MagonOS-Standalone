# Заметки по реализации

## Зафиксированные допущения

1. Первая волна собирается по `gpt_doc/codex_wave1_spec_ru.docx` как новый модульный монолит на FastAPI + SQLAlchemy + Alembic. Default runtime первой волны идёт без legacy WSGI/SQLite-моста; если старый контур временно монтируется рядом, это допустимо только как явный transitional compatibility bridge через `MAGON_FOUNDATION_LEGACY_ENABLED=true`, а не как целевая модель wave1.
2. Для `local` и `test` окружений foundation по умолчанию использует SQLite и in-memory Celery broker/result backend как быстрый dev-path. При этом compose contour на `Docker/Colima + PostgreSQL + Redis` уже отдельно подтверждён и остаётся основным `prod-ready` контуром.
3. Auth реализован через DB-backed opaque sessions, а не через JWT, чтобы сохранить минимальный foundation-контур без лишних внешних зависимостей и не усложнять revoke/audit.
4. `FilesMedia` и `Documents` в первой волне хранят только метаданные и ownership boundary. Бинарное хранилище и полнофункциональный document pipeline остаются отдельным следующим слоем.
5. `Comms` и `RulesEngine` реализованы как минимальные управляемые сущности и API-контракты. Полный event bus, message delivery orchestration и rules execution engine в первую волну сознательно не входят.
6. Публичное, внутреннее и ролевое представление объектов разведено на уровне отдельных API prefixes и view-моделей, а не через один "универсальный" DTO.
7. Критичные переходы первой волны зафиксированы как отдельные операции с reason + audit + role restriction:
   - `draft_request -> request`
   - `request -> offer`
   - `offer -> order`
8. Next.js shell сохраняется как текущая web-оболочка репозитория; foundation-login экран добавлен как проверочный UI для нового auth/session слоя, а не как полный кабинет пользователя.
9. Для текущего wave1 contour не требуется принудительное обновление стека поверх уже подтверждённого baseline: `Python 3.10`, `Node 22`, `PostgreSQL 16`, `Redis 7`, `Caddy 2.8`, `FastAPI/SQLAlchemy/Alembic/Celery` в текущих подтверждённых версиях уже согласованы и проходят живой compose runtime.
10. Текущий компактный профиль `Colima 2 CPU / 2 GB / 20 GB` достаточен для steady-state compose runtime и routine rebuilds. Расширение до `3-4 GB` нужно только для явно более тяжёлых задач, а не по умолчанию.
11. Для supplier/companies модуля первая волна разделяет данные строго по слоям `raw -> normalized -> confirmed`:
   - `raw`: `SupplierRawIngest` + `SupplierRawRecord`
   - `normalized`: `SupplierNormalizationResult`
   - `confirmed`: `Company` + `CompanyContact` + `CompanyAddress` + `SupplierCompany` + `SupplierSite`
12. `Company` остаётся общим confirmed business entity, а `SupplierCompany` и `SupplierSite` — supplier-specific слой поверх него. `Site` не схлопывается в `Company`.
13. Для первого рабочего adapter layer используется fixture-based adapter `fixture_json`, который читает `tests/fixtures/vn_suppliers_raw.json`. Это осознанный demo/source baseline для wave1 supplier contour.
14. Dedup строится на уже существующем standalone normalization/dedup logic из `supplier_intelligence`, а не на новом отдельном движке. Автоматически мержатся только уверенные совпадения; спорные кейсы уходят в `SupplierDedupCandidate` и требуют ручного решения.
15. Trust progression для supplier contour идёт только последовательно и без прыжков: `discovered -> normalized -> contact_confirmed -> capability_confirmed -> trusted`. Для `trusted` обязательны уже подтверждённые contact и capability.
16. Wave1-каталог остаётся ограниченной curated-витриной, а не "маркетплейсом всего". Для этого `CatalogItem` расширяется поверх уже существующей таблицы, а не заменяется отдельной параллельной архитектурой.
17. Мультиязычность первой волны для витрины реализуется как минимальный skeleton: UI chrome локализуется через `next-intl`, а content overrides по товарам идут через `CatalogItem.translations_json` с fallback на базовый русский текст.
18. Антибот для публичных форм первой волны intentionally lightweight: honeypot + минимальное время заполнения (`elapsed_ms`). Это manual-first защита входа в draft/RFQ contour, а не полноценный anti-fraud perimeter.
19. Центральная intake-модель первой волны строится вокруг отдельного `Request`, но публичный вход всегда идёт через отдельный `Draft`. Система не переводит draft дальше, пока не собраны обязательные поля и не пересчитан `required_fields_state`.
20. Для wave1 обязательные поля draft зафиксированы как: `customer_email`, `title`, `summary`, `item_service_context`, `city`, `requested_deadline_at`. Этот набор deliberately narrow и покрывает минимальный коммерческий intake без ERP-расширения.
21. Draft считается abandoned после `7` дней без customer activity / autosave. Это operational guard первой волны для ручного review queue, а не окончательная retention policy.
22. Публичная customer-facing ссылка на request идёт через отдельный `customer_ref`, а не через внутренний `request.code`, чтобы сохранить разделение публичного и внутреннего представления.
23. Коммерческий слой первой волны строится как `Request -> Offer(versioned) -> Order`: один `Request` может иметь несколько `Offer`, а каждая `Offer` может иметь несколько версий. В `Order` конвертируется только подтверждённая текущая конкретная версия, а не абстрактная оферта без version binding.
24. Критичная правка предложения всегда создаёт новую `OfferVersion` и сбрасывает валидность предыдущего подтверждения через отдельные `OfferConfirmationRecord` и `OfferCriticalChangeResetReason`. Это намеренно жёстче, чем "обновить оферту на месте", чтобы не оставить старое подтверждение магически валидным.
25. `Order` первой волны остаётся тонким orchestration-слоем после подтверждённой версии `Offer`, а не полным ERP/MES-заказом. На старте заказ создаётся с минимальным внутренним денежным каркасом: один `OrderRecord`, минимум одна `OrderLine`, один внутренний `PaymentRecord(created)` и ledger-ожидание оплаты.
26. Внутренний денежный каркас первой волны intentionally limited: `PaymentRecord` и `InternalLedgerEntry` нужны для ручного контроля коммерческого статуса и возвратов, но не заменяют полноценный payment-core, эквайринг или бухгалтерию.
27. Для первой волны составной и частичный сценарий выражается через агрегатные поля заказа и статусы строк: `readiness_state`, `logistics_state`, `refund_state`, `dispute_state` плюс line-level `planned_stage_refs`, `delivery_state`, `refund_state`, `dispute_state`. Полный производственный планировщик сознательно не строится.
28. Файловый и документный контур первой волны управляется как единый ownership-boundary слой вокруг `Request / Offer / Order`: бинарники хранятся через отдельный storage adapter, а бизнес-статусы и visibility живут в foundation DB.
29. Для `local/test` storage backend первой волны по умолчанию `local` с корнем `data/file-assets`, а object storage оставлен как готовый архитектурный adapter stub без обязательного подключения в этой волне.
30. Базовые file checks intentionally lightweight: `presence / size / extension / type + manual_review`. Тяжёлая предпечатная проверка, визуальный diff и production-grade prepress automation в первую волну не входят.
31. Документные шаблоны первой волны генерируются как markdown-backed managed documents (`offer_proposal`, `offer_confirmation`, `invoice_like`, `internal_job`). Это рабочий управляемый слой документооборота первой волны, а не обязательный полнофункциональный редактор или DMS.
32. Unified `MessageEvent` первой волны строится как explainable timeline-layer поверх уже существующего `AuditEvent`, а не как отдельный event bus. Source-of-truth для критичных переходов остаётся audit trail; `MessageEvent` — производный read/write слой для role-scoped timeline и notifications.
33. Notification delivery первой волны ограничен внутренним `inbox`-каналом в БД. Email, мессенджеры, webhook fanout и внешние очереди сознательно не включаются в обязательный контур и должны идти через отдельный integrations-layer в следующих волнах.
34. Role-scoped visibility для сообщений и уведомлений первой волны фиксируется четырьмя scopes: `public`, `customer`, `supplier`, `internal`. Operator/admin получают объединённый внутренний обзор; customer/supplier видят только свои разрешённые срезы без внутренних user ownership полей.
35. SLA / escalation contour первой волны intentionally lightweight: `EscalationHint` хранит baseline thresholds и dashboard hints для review/processing, но не запускает отдельный scheduler, pager duty или внешнюю эскалационную оркестрацию.
36. Customer dashboard первой волны опирается на существующий public request surface и дополняется отдельным summary endpoint. Полный отдельный customer portal с авторизацией и профилями не строится в этой волне.
37. Runtime system modes первой волны intentionally minimal: `normal / test / maintenance / emergency` задаются через env и режут трафик coarse-grained, без сложной feature-by-feature degradation matrix.
38. Failure/retry contour для supplier ingest первой волны обязан быть объяснимым и устойчивым: failed state хранится прямо в `SupplierRawIngest`, а retry идёт через тот же сервисный слой с очисткой промежуточных rows этого ingest-run, а не через "переигрывание поверх мусора".
39. Архивный контур первой волны считается достаточным, если историчность сохраняется, archived items исчезают из active views и audit/timeline не теряются. Полный operator archive-кабинет для всех сущностей специально не входит в wave1.
40. Demo readiness первой волны считается закрытой не по словам, а по отдельному end-to-end smoke сценарному прогону. Поэтому `scripts/foundation_wave1_demo_smoke_check.sh` является частью обязательного acceptance набора, а не необязательной демонстрацией.
41. Маркетинговый слой в пределах первой волны трактуется как отдельная публичная conversion-surface поверх уже существующих `catalog / rfq / drafts / customer request`, а не как новый большой модуль, CRM или CMS. Поэтому route `/marketing` только собирает и объясняет wave1-путь клиента без дублирования бизнес-сущностей.
42. Под "parsing option" в wave1-контуре понимается именно supplier-source parsing внутри модуля поставщиков, потому что спецификация включает `источники, парсинг, сырой слой, нормализация` в этот блок. Продвинутый file OCR/prepress parsing в первую волну не входит.
43. Чтобы не плодить второй контур парсинга, foundation supplier ingest использует уже существующий `supplier_intelligence` discovery layer как selectable source adapter `scenario_live`, а fixture source остаётся рядом как повторяемый demo/test baseline.
44. Async parsing contour первой волны intentionally operator-managed: `enqueue` создаёт/обновляет явный `SupplierRawIngest(queued)` row ещё до worker execution, а UI показывает именно этот explainable state вместо неявного фонового "что-то ушло в очередь".

## Явно исключено из этого шага

- Полный supplier portal
- Полный payment-core
- Склад
- MES
- Полноценный messaging delivery layer
- Тяжёлый AI контур
- Обязательная vector DB
- Полное покрытие всех стран/каналов
- Тяжёлый редактор файлов и полнофункциональный DMS
