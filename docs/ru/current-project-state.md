# Текущее состояние проекта

## Где главный репозиторий

- Активный продуктовый репозиторий: `/Users/anton/Desktop/MagonOS-Standalone`
- Donor / bridge-репозиторий: `/Users/anton/Desktop/MagonOS/MagonOS`

## Что является правдой рантайма

- `Standalone` — основной platform-of-record.
- Odoo — только donor / bridge, но не целевой runtime.
- По умолчанию работа и изменения идут только в standalone-репозитории.

## Что уже подтверждено в standalone-контуре

- компания
- коммерческий контекст клиента
- сделка
- заявка на расчёт / граница RFQ
- передача в производство
- производственная доска

## Что уже принадлежит standalone

- конвейер проверки и обогащения поставщиков
- нормализация / обогащение / дедупликация / скоринг
- очередь проверки
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

- поднять unified platform:
  - `./scripts/run_unified_platform.sh --fresh`
- поднять backend отдельно:
  - `./scripts/run_platform.sh --fresh --port 8091`
- прогнать fixture pipeline:
  - `./.venv/bin/python scripts/run_pipeline.py --fixture tests/fixtures/vn_suppliers_raw.json`
- проверить backend/workflow:
  - `./scripts/verify_workflow.sh`
- если менялся web:
  - `./scripts/verify_workflow.sh --with-web`
  - `cd apps/web && npm run build`

## Локальные поверхности

- public shell: `http://127.0.0.1:3000/`
- dashboard: `http://127.0.0.1:3000/dashboard`
- ops workbench: `http://127.0.0.1:3000/ops-workbench`
- operator pages: `http://127.0.0.1:3000/ui/*`
- direct backend debug: `http://127.0.0.1:8091/`
