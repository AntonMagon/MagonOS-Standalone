# Аудит паритета бизнес-логики между legacy donor и standalone platform

> Историческая оговорка:
> этот файл фиксирует extraction-era donor audit.
> Каноническая правда по текущему wave1 runtime живёт в `docs/current-project-state.md` и `docs/ru/current-project-state.md`.
> Не читай этот файл как доказательство текущего foundation runtime на SQLite или donor-era `/ui/*` shell.

## 1. Executive verdict

### Короткий ответ

**Нет, полная бизнес-логика и реальные правила работы ещё не перенесены.**

Перенесена не только оболочка. Перенесён уже реальный рабочий контур:

- discovery / extraction / normalization / enrichment
- canonical supplier intelligence
- scoring / dedup / review queue / routing / qualification flow
- feedback ledger / feedback projection
- company-centric operator workflow
- standalone commercial preparation contour
- quote intent lifecycle
- production handoff / production board contour
- standalone workforce estimation engine

Но это **не равно** полной миграции Odoo-бизнеса. В Odoo всё ещё остаются критичные домены, где durable state и правила живут только там:

- customer master
- CRM lead ownership
- RFQ
- full quote domain
- conversation/history tied to CRM/customer flow
- workforce planning persistence
- auth / roles / internal access model
- remaining admin/operator surfaces outside extracted contour
- ERP / accounting side effects

### Что уже точно standalone-owned

- supplier intelligence как рабочий контур
- routing/qualification/review decisions по extracted contour
- feedback ingestion + projection
- standalone commercial preparation state
- quote intents
- production handoffs
- production board

### Что точно остаётся Odoo-owned

- customer / partner master ownership
- lead/opportunity ownership
- RFQ / quote как полноценные Odoo-shaped домены
- conversation / ERP snapshots
- workforce planning data
- auth / permissions / users
- accounting / invoice / payment

### Самый опасный overlap

Самый опасный overlap сейчас не в supplier intelligence.
Он в **commercial semantics**:

- standalone уже имеет `commercial_records`, `quote_intents`, `production_handoffs`
- Odoo всё ещё имеет `print.broker.customer`, `print.broker.lead`, `print.broker.rfq`, `print.broker.quote`

Если называть это “уже перенесённым CRM/quote контуром”, это будет ложь.

### Следующий бизнес-модуль для миграции

**Customer / Lead / RFQ / Quote donor audit and minimum standalone commercial ownership boundary.**

Не ERP целиком.
Не accounting.
Не generic CRM.

Нужно разобрать именно тот коммерческий модуль, который связывает текущий standalone commercial prep с Odoo-only sales/CRM state.

---

## 2. Каноническое стратегическое утверждение

### Активный продуктовый репозиторий

- `/Users/anton/Desktop/MagonOS-Standalone`

### Legacy donor / bridge репозиторий

- `/Users/anton/Desktop/MagonOS/MagonOS`

### Что это означает practically

- вся новая platform/product-core работа должна вестись в standalone repo
- source repo — только donor inspection, legacy support, bridge/export
- source repo не является truth-source для того, что уже extracted в standalone
- при конфликте `docs` vs `code` — **доверять коду и тестам**

---

## 3. Использованные доказательства

### Source repo inspected

- `addons/print_broker_core/models/*`
- `addons/print_broker_core/services/*`
- `addons/print_broker_core/views/print_broker_admin_views.xml`
- `platform_core/supplier_intelligence/*`
- `tests/pipeline/*`
- `tests/platform_core/*`
- `docs/strategy/*`
- `docs/PROJECT_SCOPE.md`

### Standalone repo inspected

- `src/magon_standalone/supplier_intelligence/*`
- `tests/*`
- runtime/API routes through `api.py`

### Тесты, реально прогнанные как evidence

#### Source repo

```bash
cd /Users/anton/Desktop/MagonOS/MagonOS && ./.venv/bin/python -m unittest \
  tests.pipeline.test_transition_rules \
  tests.pipeline.test_operations_service \
  tests.pipeline.test_workforce_estimation \
  tests.pipeline.test_operational_policy \
  tests.platform_core.test_feedback_ingestion \
  tests.platform_core.test_standalone_api \
  tests.pipeline.test_odoo_feedback_export
```

Результат: `Ran 22 tests ... OK`

#### Standalone repo

```bash
cd /Users/anton/Desktop/MagonOS-Standalone && ./.venv/bin/python -m unittest \
  tests.test_api \
  tests.test_operations \
  tests.test_persistence \
  tests.test_feedback \
  tests.test_pipeline \
  tests.test_workforce
```

Результат: `Ran 34 tests ... OK`

### Runtime checks, реально прогнанные

В historical extraction pass поднимался временный SQLite/in-memory contour и проверялись donor-era operator surfaces:

- `/`
- `/ui/companies`
- `/ui/quote-intents`
- `/ui/production-handoffs`
- `/ui/production-board`
- `/ui/review-queue`
- `/ui/feedback-status`

Это остаётся полезным как donor evidence, но не как канонический runtime proof для текущего foundation shell.

---

## 4. Domain-by-domain parity analysis

### A. Supplier intelligence core

#### Business purpose

Собрать supplier evidence, нормализовать, обогатить, дедуплицировать, посчитать score, получить каноническую supplier/company intelligence state.

#### Source repo evidence

- `platform_core/supplier_intelligence/extraction_engine.py`
- `platform_core/supplier_intelligence/normalization_service.py`
- `platform_core/supplier_intelligence/deduplication_service.py`
- `platform_core/supplier_intelligence/scoring_service.py`
- `platform_core/supplier_intelligence/pipeline.py`
- Odoo sink: `addons/print_broker_core/services/repositories.py`
- Odoo raw/master models: `models/raw_entities.py`, `models/master_entities.py`
- tests:
  - `tests/pipeline/test_normalization.py`
  - `tests/pipeline/test_deduplication.py`
  - `tests/pipeline/test_scoring.py`
  - `tests/pipeline/test_pipeline_flow.py`
  - `tests/platform_core/test_standalone_api.py`

#### Standalone repo evidence

- `src/magon_standalone/supplier_intelligence/extraction_engine.py`
- `src/magon_standalone/supplier_intelligence/normalization_service.py`
- `src/magon_standalone/supplier_intelligence/deduplication_service.py`
- `src/magon_standalone/supplier_intelligence/scoring_service.py`
- `src/magon_standalone/supplier_intelligence/pipeline.py`
- `src/magon_standalone/supplier_intelligence/sqlite_persistence.py`
- runtime/API surfaces in `api.py`
- tests:
  - `tests/test_pipeline.py`
  - `tests/test_persistence.py`
  - `tests/test_api.py`

#### Real business rules found

- raw source fingerprint uniqueness
- evidence uniqueness per raw company/source reference
- normalization into canonical company key/name/contact/capabilities
- dedup pair fingerprint uniqueness
- dedup confidence constrained to 0..1 on source side
- score persistence and later routing usage
- evidence/provenance persisted and operator-visible

#### Current source of truth

**standalone** for the extracted contour.

#### Migration status

**standalone already authoritative**

#### Confidence

**high**

#### Why this classification is true

- standalone has its own persistence tables for raw records, raw evidence, canonical companies, scores, dedup decisions
- standalone runtime and tests prove the pipeline runs without Odoo runtime
- source repo `platform_core` and standalone repo code are materially the same contour, but standalone now owns execution and storage

#### Risk if left as-is

Low in ownership terms.
Remaining risk is only code drift between legacy source copies and standalone copies.

#### Recommended action

Keep in standalone. Treat source implementation as donor snapshot only.

---

### B. Review / qualification / routing

#### Business purpose

Take scored supplier intelligence and drive review queue state, dedup review, qualification decisions, routing outcome, manual override, and audit trail.

#### Source repo evidence

- `addons/print_broker_core/services/qualification_service.py`
- `addons/print_broker_core/services/transition_service.py`
- `addons/print_broker_core/services/operations_service.py`
- `addons/print_broker_core/services/operational_policy.py`
- `addons/print_broker_core/services/repositories.py`
- `addons/print_broker_core/models/quality_entities.py`
- tests:
  - `tests/pipeline/test_transition_rules.py`
  - `tests/pipeline/test_operations_service.py`
  - `tests/pipeline/test_operational_policy.py`

#### Standalone repo evidence

- `src/magon_standalone/supplier_intelligence/operations_service.py`
- `src/magon_standalone/supplier_intelligence/routing_service.py`
- `src/magon_standalone/supplier_intelligence/operational_policy.py`
- `src/magon_standalone/supplier_intelligence/sqlite_persistence.py`
- UI/operator actions in `api.py`
- tests:
  - `tests/test_operations.py`
  - `tests/test_api.py`
  - `tests/test_persistence.py`

#### Real business rules found

- explicit queue transition matrix exists in source: `_ALLOWED_TRANSITIONS`
- reprocess from `done|dismissed -> pending` requires `allow_reprocess=True`
- routing decision persists:
  - route outcome
  - reason code
  - evidence refs
  - manual override flag
  - qualification decision row
  - routing audit row
- standalone preserves operator-owned queue state on pipeline rerun
- standalone manual routing decision updates qualification/routing state and audit trail
- dedup review/manual approval exists in source Odoo model actions

#### Current source of truth

**standalone** for extracted review/routing contour

#### Migration status

**standalone already authoritative**

#### Confidence

**high**

#### Why this classification is true

- standalone has dedicated tables: `review_queue`, `vendor_profiles`, `qualification_decisions`, `routing_audit`
- standalone tests prove manual decision and queue transition behavior live there now
- runtime/UI actions operate against standalone storage, not Odoo queue state

#### Risk if left as-is

Low for current extracted contour. Main risk is still legacy operator habits or stale source-side assumptions.

#### Recommended action

Keep in standalone and stop treating Odoo queue state as the canonical version for this contour.

---

### C. Feedback ledger / downstream outcome projection

#### Business purpose

Receive narrow downstream outcome data from Odoo without making Odoo source-of-truth for supplier intelligence. Build auditable ledger + read model.

#### Source repo evidence

- `addons/print_broker_core/services/standalone_feedback_service.py`
- `addons/print_broker_core/models/quality_entities.py` (`print.broker.standalone.feedback.event` etc.)
- tests:
  - `tests/pipeline/test_odoo_feedback_export.py`
  - `tests/platform_core/test_feedback_ingestion.py`

#### Standalone repo evidence

- `src/magon_standalone/supplier_intelligence/contracts.py`
- `src/magon_standalone/supplier_intelligence/sqlite_persistence.py`
- `src/magon_standalone/supplier_intelligence/api.py`
- tests:
  - `tests/test_feedback.py`
  - `tests/test_api.py`

#### Real business rules found

- allowed event families are narrow
- legacy `crm_lead_feedback` is normalized to `commercial_disposition_feedback`
- forbidden reverse-flow content is rejected
- integration token required on ingest endpoint
- idempotency via deterministic event id + unique storage
- projection is derived from feedback ledger and kept separate from canonical intelligence
- canonical company data is not overwritten by feedback projection

#### Current source of truth

**standalone** for feedback ledger and projection

#### Migration status

**standalone already authoritative**

#### Confidence

**high**

#### Why this classification is true

- standalone stores `feedback_events` and `feedback_status_projection`
- standalone tests prove idempotency, forbidden payload rejection, projection separation, alias normalization
- source repo only publishes/export events; it no longer owns the feedback read model

#### Risk if left as-is

Low if contract remains narrow.
High only if someone broadens this into generic entity sync.

#### Recommended action

Keep narrow. Do not expand into mirrored CRM/entity synchronization.

---

### D. Commercial preparation

#### Business purpose

Track company-centric commercial state before full ERP/CRM downstream execution: status, stage, refs, next action, notes, blockers/readiness.

#### Source repo evidence

- `addons/print_broker_core/models/commercial_entities.py`
- `addons/print_broker_core/services/repositories.py`
- `addons/print_broker_core/services/operational_policy.py`

#### Standalone repo evidence

- `sqlite_persistence.py` -> `commercial_records`
- UI pages and write actions in `api.py`
- tests:
  - `tests/test_api.py::test_commercial_state_is_editable_in_standalone`
  - `tests/test_persistence.py::test_commercial_record_roundtrip`

#### Real business rules found

- company-centric commercial state can be updated in standalone
- stage, customer status, references, next action, due-at, notes persist and round-trip
- company workbench surfaces standalone commercial state explicitly

#### Current source of truth

**mixed / dangerous overlap**

#### Migration status

**partially migrated / dangerous overlap**

#### Confidence

**medium-high**

#### Why this classification is true

- standalone clearly owns `commercial_records`
- but Odoo still owns `print.broker.customer` and `print.broker.lead`
- therefore standalone commercial prep exists, but it is not yet full commercial/customer ownership parity

#### Risk if left as-is

Operators may assume standalone commercial status equals CRM/customer truth, while source Odoo still owns related master entities and sales semantics.

#### Recommended action

Migrate next as business module boundary, not as UI enhancement.

---

### E. Partner / account / contact / lead / opportunity handling

#### Business purpose

Maintain customer account identity, contact/account linkage, lead mapping, CRM ownership, assigned user, lead lifecycle.

#### Source repo evidence

- `models/commercial_entities.py`
  - `PrintBrokerCustomer`
  - `PrintBrokerLead`
- `res.partner`, `crm.lead`, `res.users` references embedded there
- `repositories.py` side effects create/reuse partner/lead mappings

#### Standalone repo evidence

- no standalone customer master
- no standalone lead master
- external references only in `commercial_records` and feedback projection
- feedback traceability only, not entity ownership

#### Real business rules found

- customer partner must be unique
- only one broker lead per canonical company
- lead status enum exists on Odoo side
- assigned user/account manager semantics are Odoo-bound

#### Current source of truth

**source/Odoo**

#### Migration status

**still Odoo-only**

#### Confidence

**high**

#### Why this classification is true

Standalone has no customer/lead domain model that replaces these Odoo entities as durable owners.

#### Risk if left as-is

This is the biggest business parity blind spot in the commercial contour.

#### Recommended action

Audit and redesign before migration. Do not mirror Odoo `res.partner`/`crm.lead` blindly.

---

### F. RFQ / quote / conversation / order-intent logic

#### Business purpose

Move from commercial opportunity into actual supplier/customer RFQ/quote and conversation state.

#### Source repo evidence

- `models/commercial_entities.py`
  - `PrintBrokerRFQ`
  - `PrintBrokerQuote`
  - `PrintBrokerConversation`
- Odoo links to `purchase.order`, `sale.order`, customer, channel

#### Standalone repo evidence

- `quote_intents` in `sqlite_persistence.py`
- quote workbench UI/actions in `api.py`
- tests:
  - `tests/test_api.py::test_quote_intent_is_editable_in_standalone`
  - `tests/test_api.py::test_quote_workbench_updates_status_and_pricing`
  - `tests/test_persistence.py::test_quote_intent_roundtrip`

#### Real business rules found

- standalone supports quote intent creation/update, pricing notes, quote reference, status transitions at intent/workbench level
- source Odoo supports actual RFQ and quote durable entities
- standalone has **no** conversation domain equivalent

#### Current source of truth

**mixed / dangerous overlap**

#### Migration status

**partially migrated / dangerous overlap**

#### Confidence

**high**

#### Why this classification is true

Standalone has a real quote-intent contour, but that is not the same as Odoo RFQ/quote/customer/conversation ownership.

#### Risk if left as-is

False claims of quote parity.
Operators may mistake quote intent for full quote/order replacement.

#### Recommended action

This must be the next business-module audit slice.

---

### G. Production preparation / execution prep

#### Business purpose

Take validated commercial/quote preparation and move it into production-ready handoff state and execution board state.

#### Source repo evidence

- no equally explicit extracted standalone-like contour in source models
- source operational flow was previously embedded around Odoo entities and UI

#### Standalone repo evidence

- `production_handoffs` in `sqlite_persistence.py`
- production board views/actions in `api.py`
- tests:
  - `tests/test_persistence.py::test_production_handoff_roundtrip`
  - `tests/test_persistence.py::test_production_handoff_rejects_quote_from_another_company`
  - `tests/test_persistence.py::test_production_handoff_status_update_preserves_existing_fields_when_not_supplied`
  - `tests/test_api.py::test_production_handoff_is_editable_in_standalone`
  - `tests/test_api.py::test_production_board_status_move_does_not_overwrite_existing_handoff_fields`

#### Real business rules found

- production handoff must not link to a quote intent from another company
- board status move must not overwrite fresher handoff fields implicitly
- handoff field updates preserve existing values when not supplied
- company -> quote intent -> handoff linkage is enforced and surfaced

#### Current source of truth

**standalone** for this contour

#### Migration status

**standalone already authoritative**

#### Confidence

**high**

#### Why this classification is true

This contour exists as real persistence + API + tests only in standalone form as current active path.

#### Risk if left as-is

Low in ownership terms.
Main risk is that this contour still lacks deeper integration with yet-unmigrated quote/customer modules.

#### Recommended action

Keep in standalone.
Use as anchor for the next commercial module migration.

---

### H. Workforce / capacity / estimation

#### Business purpose

Estimate labor needs and, in the fuller model, manage workforce roles, shifts, rates, absences, capacity slots, and labor policies.

#### Source repo evidence

- `services/workforce_estimation_service.py`
- `models/workforce_entities.py`
- tests:
  - `tests/pipeline/test_workforce_estimation.py`

#### Standalone repo evidence

- `src/magon_standalone/supplier_intelligence/workforce_estimation_service.py`
- runtime/UI exposure in `api.py`
- tests:
  - `tests/test_workforce.py`
  - workforce UI/API assertions in `tests/test_api.py`

#### Real business rules found

Source/Odoo-only persistence rules:

- unique worker role code
- unique skill code
- valid shift hours 0..24 and start before end
- unique shift slot per facility/role/day/time
- non-negative base rate
- overtime multiplier >= 1
- effective_from <= effective_to
- unique hourly rate rule per role/location/effective date
- absence start before end
- unique capacity slot

Standalone rules:

- workforce estimation engine computes headcount, overtime, bottleneck role, labor cost, time remaining
- runtime and tests show this logic works independently from Odoo

#### Current source of truth

**mixed**

#### Migration status

**partially migrated / dangerous overlap**

#### Confidence

**high**

#### Why this classification is true

The **engine** is migrated.
The **planning/master data domain** is still only Odoo.

#### Risk if left as-is

People may say “workforce migrated” when only estimation migrated.
That would be false.

#### Recommended action

Do not claim workforce parity.
Treat this as engine parity without domain/state parity.

---

### I. Admin/operator decision flows

#### Business purpose

Allow operators to move state, apply decisions, reopen/reprocess queue items, capture rationale, and inspect audit trail.

#### Source repo evidence

- model actions in `models/master_entities.py`, `models/quality_entities.py`, `models/raw_entities.py`
- admin UI in `views/print_broker_admin_views.xml`
- service layer in `operations_service.py`, `transition_service.py`, `qualification_service.py`

#### Standalone repo evidence

- write actions in `api.py`
- persistence transitions and routing audit in `sqlite_persistence.py`
- tests:
  - `tests/test_operations.py`
  - `tests/test_api.py`

#### Real business rules found

- standalone operator actions now write standalone state directly for extracted contours
- queue transition reopening requires explicit reprocess flag
- manual routing decisions create audit trail
- sample feedback is explicitly labeled synthetic
- standalone operator flows are no longer debug-only; they are actual write paths

#### Current source of truth

**mixed**

#### Migration status

**partially migrated / dangerous overlap**

#### Confidence

**medium-high**

#### Why this classification is true

For extracted contours, standalone is authoritative.
For the remaining non-extracted Odoo domains, admin/operator flow is still Odoo-only.

#### Risk if left as-is

Operational split-brain: some decisions in standalone, some still only in Odoo.

#### Recommended action

Move next by business module, not by screen-by-screen cloning.

---

### J. Downstream ERP / CRM / accounting side effects

#### Business purpose

Reflect commercial and operational state into ERP/CRM/accounting consequences.

#### Source repo evidence

- `standalone_sync_service.py`
- `standalone_feedback_service.py`
- `erp_context_service.py`
- `models/commercial_entities.py`
- Odoo ERP links to `res.partner`, `crm.lead`, `purchase.order`, `sale.order`

#### Standalone repo evidence

- narrow feedback ingest only
- no accounting/order ERP ownership

#### Real business rules found

- standalone -> Odoo sync remains explicit bridge logic
- Odoo -> standalone feedback remains explicit narrow outcome ingestion
- accounting/payment/order side effects are not modeled as standalone-owned truth

#### Current source of truth

**source/Odoo**

#### Migration status

**still Odoo-only** for ERP/accounting side effects

#### Confidence

**high**

#### Why this classification is true

Standalone does not attempt to own ERP/accounting/order effects yet, by design.

#### Risk if left as-is

Low if this boundary remains explicit.
High only if someone starts pretending these effects are already migrated.

#### Recommended action

Keep outside the current standalone contour.

---

## 5. Четыре обязательные таблицы

### Table 1 — STANDALONE ALREADY AUTHORITATIVE

| Domain / responsibility | Standalone evidence | Why authoritative now |
|---|---|---|
| Raw discovery/evidence | `sqlite_persistence.py`, `pipeline.py`, `tests/test_pipeline.py`, `tests/test_api.py` | Own runtime + own storage + operator visibility |
| Canonical supplier/company intelligence core | `canonical_companies`, `api.py` company workbench | No Odoo runtime needed; read/write path exists in standalone |
| Scoring | `vendor_scores`, scoring services, tests | Stored and consumed in standalone routing flow |
| Dedup decisions | `dedup_decisions`, tests, routing flow | Persisted and used in standalone |
| Review queue state and transitions | `review_queue`, `transition_review_queue`, tests | Queue state changes and audit live in standalone |
| Routing / qualification outcome for extracted contour | `operations_service.py`, `apply_routing_decision`, tests | Manual and automatic decisions operate on standalone state |
| Routing audit/history | `routing_audit`, company workbench, tests | Audit trail no longer depends on Odoo for extracted contour |
| Feedback ledger | `feedback_events`, `/feedback-events`, tests | Standalone stores ledger and enforces contract |
| Feedback projection/read model | `feedback_status_projection`, `/feedback-status`, tests | Projection is derived and served from standalone |
| Commercial prep state already implemented | `commercial_records`, commercial UI/tests | Standalone persists company-centric commercial follow-up state |
| Quote intent lifecycle | `quote_intents`, quote workbench/tests | Real standalone write-path and read-path exist |
| Production handoff / board contour | `production_handoffs`, production board/tests | Real standalone validation and state ownership exist |
| Workforce estimation engine | `workforce_estimation_service.py`, runtime/test coverage | Computation runs outside Odoo |

### Table 2 — STILL ODOO-ONLY

| Domain / responsibility | Source evidence | Why still Odoo-only |
|---|---|---|
| Customer master | `models/commercial_entities.py::PrintBrokerCustomer` | No standalone replacement entity exists |
| Lead mapping / CRM lead ownership | `PrintBrokerLead`, `crm.lead`, `res.users` refs | Standalone only has trace refs, not lead ownership |
| RFQ domain | `PrintBrokerRFQ` | No standalone RFQ model/workflow exists |
| Full quote domain | `PrintBrokerQuote` | `quote_intent` is not full quote parity |
| Conversation domain | `PrintBrokerConversation` | No standalone equivalent |
| ERP snapshot/admin context | `erp_context_service.py` + snapshot models | Standalone avoids owning ERP shadow state |
| Workforce master/planning state | `models/workforce_entities.py` | Standalone only migrated estimation engine |
| Auth / roles / permissions | `res.users`, access CSV, Odoo groups/views | No standalone auth/admin model exists |
| Non-extracted admin/operator flows | Odoo views + model actions | Standalone only covers extracted contours |
| Accounting / invoice / payment / order effects | Odoo ERP links | Not migrated by design |

### Table 3 — PARTIALLY MIGRATED / DANGEROUS OVERLAP

| Domain | Source evidence | Standalone evidence | Why overlap is dangerous |
|---|---|---|---|
| Commercial/customer workflow semantics | customer/lead/quote models in Odoo | `commercial_records`, company workbench | Same business area, different ownership layers |
| Quote semantics | `PrintBrokerQuote`, `PrintBrokerRFQ` | `quote_intents` | Quote intent can be mistaken for full quote parity |
| Workforce | workforce models + policies in Odoo | estimation engine in standalone | Engine moved, state did not |
| Company master depth | `master_entities.py` deep graph | thinner `canonical_companies` | Easy to overclaim master-data parity |
| Operator/admin flow | Odoo XML admin + actions | standalone operator surfaces | Some contours moved, some still Odoo-only |
| Bridge/export assumptions | `standalone_sync_service.py`, `standalone_feedback_service.py` | narrow feedback/read model | Ownership can blur if bridge grows casually |
| Strategy/docs statements | source `PROJECT_SCOPE.md` | standalone docs/AGENTS | Conflicting narrative causes bad decisions |
| Duplicate code copies | `platform_core/supplier_intelligence/*` in source | `src/magon_standalone/supplier_intelligence/*` | Donor snapshot may be mistaken for active implementation |
| Request/specification lineage | `request.py`, `specification.py` | no proven full replacement | Hidden donor logic may still matter |
| Public/commercial offering claims | old hybrid docs | standalone product shell | Teams may sell a scope that code does not support |

### Table 4 — DEAD LEGACY / SHOULD NOT BE MIGRATED AS-IS

| Candidate | Why it should not be ported as-is |
|---|---|
| Odoo XML view system as product boundary | Wrong target architecture for the standalone platform |
| Odoo model actions returning UI actions | UI-side effect pattern should not be recreated in standalone |
| Odoo users/groups/access CSV as future auth model | Should be replaced, not copied |
| ERP snapshot UI shape | Too Odoo-shaped to copy directly |
| Treating `res.partner` mirroring as customer strategy | Creates fake parity and sync monster |
| Treating `crm.lead` mirroring as standalone CRM | Same problem: mirrored entity trap |
| Legacy source-repo `apps/web` as active frontend | It is now donor/legacy only |
| Source repo startup path as canonical runtime | Wrong after platform-of-record decision |
| Any “sync everything both ways” idea | Violates current architecture constraints |
| Odoo-only admin surface assumptions for extracted domains | Should be replaced by standalone operator flows, not re-hosted |

---

## 6. Rule inventory by domain

### Supplier intelligence core

| Rule | Where found | Status |
|---|---|---|
| raw source fingerprint unique | source `models/raw_entities.py`; standalone `raw_records.source_fingerprint UNIQUE` | migrated |
| raw evidence unique per raw record | source `raw_entities.py`; standalone `raw_evidence UNIQUE(...)` | migrated |
| dedup confidence bounded / pair uniqueness | source `quality_entities.py`; standalone `dedup_decisions` flow and tests | migrated |
| canonical company normalization into portable shape | source `platform_core/.../normalization_service.py`; standalone same module/tests | migrated |

### Review / qualification / routing

| Rule | Where found | Status |
|---|---|---|
| explicit queue transition matrix | source `transition_service.py::_ALLOWED_TRANSITIONS`; standalone `transition_review_queue` | migrated |
| reprocess requires explicit allow flag | source `transition_service.py`; standalone `sqlite_persistence.py` | migrated |
| routing decision persists qualification decision + audit | source `repositories.py`; standalone `apply_routing_decision` | migrated |
| operator override flagged and audited | source `repositories.py`, `quality_entities.py`; standalone tests `test_operations.py`, `test_api.py` | migrated |
| pipeline rerun must not clobber operator-owned queue state | standalone `tests/test_operations.py` | standalone-only improvement |

### Feedback

| Rule | Where found | Status |
|---|---|---|
| integration token required | source `tests/platform_core/test_feedback_ingestion.py`; standalone `tests/test_feedback.py` | migrated |
| forbidden reverse-flow payloads rejected | same tests | migrated |
| crm_lead_feedback normalized to commercial_disposition_feedback | same tests | migrated |
| feedback projection must not overwrite canonical intelligence | same tests | migrated |
| feedback event idempotent | same tests | migrated |

### Commercial preparation / quote intent / handoff

| Rule | Where found | Status |
|---|---|---|
| company commercial state round-trip persists | standalone `tests/test_persistence.py::test_commercial_record_roundtrip` | standalone-owned contour |
| quote intent creation/update persists refs and pricing | standalone `tests/test_persistence.py::test_quote_intent_roundtrip`, `tests/test_api.py` | standalone-owned contour |
| handoff rejects quote from another company | standalone `tests/test_persistence.py::test_production_handoff_rejects_quote_from_another_company` | standalone-owned contour |
| handoff update preserves unsupplied fields | standalone `tests/test_persistence.py::test_production_handoff_status_update_preserves_existing_fields_when_not_supplied` | standalone-owned contour |
| board move must not overwrite fresher handoff fields | standalone `tests/test_api.py::test_production_board_status_move_does_not_overwrite_existing_handoff_fields` | standalone-owned contour |

### Workforce

| Rule | Where found | Status |
|---|---|---|
| estimation computes headcount/overtime/bottleneck/cost | source `tests/pipeline/test_workforce_estimation.py`; standalone `tests/test_workforce.py` | engine migrated |
| shift validity / rate validity / uniqueness / absence / capacity rules | source `models/workforce_entities.py` | still Odoo-only |

### Auth / admin

| Rule | Where found | Status |
|---|---|---|
| assigned users / account manager / access rules tied to Odoo users | source `models/commercial_entities.py`, access CSV, Odoo views | still Odoo-only |
| standalone operator identity is simplified/local only | standalone runtime/actions | not parity |

---

## 7. Gaps and contradictions

### Code vs docs

- `MagonOS/MagonOS/docs/PROJECT_SCOPE.md` still says Odoo is the internal system of record.
- Actual code and runtime say standalone is the active platform-of-record for extracted contours.

### Source vs standalone

- Source repo still physically contains donor copies of `platform_core/supplier_intelligence/*`.
- Standalone repo is the active execution path.
- If anyone treats both as live equals, drift will continue.

### Tests vs implementation

- Standalone tests prove real commercial/handoff/board rules that do **not** exist as identical Odoo replacements.
- Therefore standalone is not “just a shell”; it contains new real business logic.
- But source tests and source models still prove that customer/lead/RFQ/quote/workforce state remains Odoo-only.

---

## 8. Migration priority order

### Priority 1 — Customer / Lead / RFQ / Quote donor audit and minimum replacement boundary

Why:

- this is the largest remaining business parity blind spot
- it sits exactly between current standalone commercial prep and Odoo-only sales/CRM state
- it is the biggest source of false migration claims

### Priority 2 — Request / Specification donor logic audit

Why:

- these legacy models may still contain real business rules that feed quote/handoff/product preparation
- they should not be dropped blindly

### Priority 3 — Workforce planning domain decision

Why:

- workforce estimation already lives in standalone
- workforce planning state does not
- the team needs a conscious decision: migrate, integrate externally, or keep as back-office only

---

## 9. Stop-doing-now list

- Stop saying “we already moved everything from Odoo.”
- Stop treating `quote_intent` as proof of full quote parity.
- Stop treating workforce estimation as proof that workforce domain was migrated.
- Stop treating source repo `platform_core` copies as active product implementation.
- Stop treating source repo `apps/web` as canonical frontend.
- Stop growing new product-core logic in Odoo for domains already extracted.
- Stop using docs-only claims as evidence of migration completeness.
- Stop framing customer/lead/quote gaps as “just UI/admin tasks.”
- Stop broadening feedback into generic entity sync.
- Stop pretending auth/admin replacement is already solved.

---

## 10. Final judgement

### Перенесли ли мы реальные правила работы и бизнес-логику?

**Да, но только по части системы.**

Перенесены:

- supplier-intelligence core
- review/routing/qualification contour
- feedback ledger/projection
- commercial-prep contour in standalone form
- quote-intent contour
- production handoff / board contour
- workforce estimation engine

### Перенесли ли мы всё, что раньше жило в Odoo?

**Нет.**

Критичные домены всё ещё только в Odoo:

- customer master
- lead/CRM ownership
- RFQ
- full quote domain
- conversation/history
- workforce planning state
- auth/roles/permissions
- ERP/accounting effects

### Честная формулировка состояния проекта

> Мы уже перенесли существенную часть реальной бизнес-логики и operating rules в standalone platform. Но полный паритет бизнес-логики с Odoo не достигнут. Наиболее опасный незакрытый модуль — customer/lead/RFQ/quote boundary.
