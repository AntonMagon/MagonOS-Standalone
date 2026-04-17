# Визуальная карта проекта

Обновлено: ``2026-04-17 08:55 +07``

## Контур движения

```mermaid
flowchart LR
  Company["Компания"] --> Customer["Клиентский аккаунт"]
  Customer --> Opportunity["Сделка"]
  Opportunity --> Quote["Заявка на расчёт / RFQ"]
  Quote --> Handoff["Передача в производство"]
  Handoff --> Board["Производственная доска"]
```

## Что уже принадлежит standalone

- конвейер проверки и обогащения поставщиков
- нормализация / обогащение / дедупликация / скоринг
- очередь проверки
- маршрутизация / квалификационные решения
- журнал обратной связи / проекция
- оценка трудозатрат

## Что сейчас является ядром контура

- компания
- коммерческий контекст клиента
- сделка
- заявка на расчёт / граница RFQ
- передача в производство
- производственная доска

## Где остаётся риск overlap

- идентичность клиента / аккаунта
- владение сделкой / лидом
- граница RFQ / расчёта

## Что не должно расползаться в scope

- бухгалтерия
- счета / оплаты
- полное ERP-управление заказами
- огромная универсальная CRM
- широкое зеркалирование сущностей Odoo
- рост функциональности donor-репозитория

## Активный контекст

- Текущий фокус: Keep the Russian docs and shell protected from both English leakage and bad technical hybrid copy.
- Последний подтверждённый статус workflow: PASS `./.venv/bin/python -m unittest tests.test_locale_integrity`, PASS `./scripts/verify_workflow.sh`, PASS `./.venv/bin/python scripts/check_russian_locale_integrity.py --static-only`
- Главный операционный риск: The guard now catches known English leaks and bad hybrid phrases, but it still cannot judge whether a sentence sounds commercially good without manual review.

## Автоматические контуры контроля

- Hourly Repo Guard
- Hourly Platform Smoke
- RU Locale Guard
- Hourly Visual Map
- Weekly Release Gate
- Launchd Periodic Checks

## Активные project skills

- audit-docs-vs-runtime
- ci-watch-fix
- docs-sync-curator
- donor-boundary-audit
- git-safe-commit
- operate-platform
- operate-standalone-intelligence
- project-visual-map
- release-readiness-gate
- skill-pattern-scan
- verify-implementation
- web-regression-pass
