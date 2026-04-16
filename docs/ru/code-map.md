# Карта кода

Этот файл нужен как быстрый вход в структуру проекта на русском языке.
Он не заменяет чтение кода, но снимает постоянный ручной старт "а что здесь за что отвечает".

## Верхний уровень

- `src/magon_standalone/`
  Основной backend/runtime код standalone-платформы.
- `apps/web/`
  Внешняя web-оболочка и встроенный операторский shell на Next.js.
- `scripts/`
  Канонические entrypoints запуска, проверки и repo workflow.
- `tests/`
  Unit/integration-проверки backend и repo workflow.
- `docs/`
  Основная документация на английском.
- `docs/ru/`
  Обязательный русскоязычный слой документации.
- `.codex/`
  Project memory и repo-level config для агентного workflow.
- `.githooks/`
  Versioned git hooks, которые реально принуждают workflow.

## Backend

### `src/magon_standalone/supplier_intelligence/api.py`

Главный backend UI/API слой.
Отвечает за:
- HTTP API
- server-rendered operator pages
- company/commercial/quote/handoff screens
- locale cookie и локализацию backend UI

Если меняется операторский backend UI, очень вероятно, что правки будут здесь.

### `src/magon_standalone/supplier_intelligence/sqlite_persistence.py`

Главный persistence-слой на SQLite.
Отвечает за:
- сохранение canonical companies
- feedback ledger / projection
- commercial records
- quote intents
- production handoffs

Если меняются правила записи, проекции, аудита или связности сущностей, смотреть сюда.

### `src/magon_standalone/supplier_intelligence/pipeline.py`

Оркестрация supplier-intelligence pipeline:
- normalization
- enrichment
- dedup
- scoring
- routing

### `src/magon_standalone/supplier_intelligence/operations_service.py`

Сервис прикладных действий по операторскому/коммерческому контуру.
Сюда смотреть, когда меняется практическая логика действий, а не только рендеринг.

### `src/magon_standalone/supplier_intelligence/routing_service.py`

Правила маршрутизации и review queue.
Если меняется логика очередей, decision flow или qualification routing, искать здесь.

### `src/magon_standalone/supplier_intelligence/workforce_estimation_service.py`

Отдельный расчёт трудозатрат/персонала.
Не должен молча мутировать company intelligence.

## Web shell

### `apps/web/app/`

App Router страницы Next.js:
- `page.tsx` — главная витрина
- `dashboard/page.tsx` — runtime/dashboard
- `ops-workbench/page.tsx` — операторский вход
- `personalize/page.tsx` — страница границ/контракта

### `apps/web/components/navigation/site-header.tsx`

Главный header web shell.
Сейчас отвечает за:
- основную навигацию
- mobile nav
- theme controls
- language toggle

### `apps/web/components/navigation/language-toggle.tsx`

Компонент переключения языка интерфейса.
Работает через cookie `magonos-locale` и `router.refresh()`.

### `apps/web/i18n/request.ts`

Точка выбора locale и сборки message tree.
Сначала смотрит cookie, потом `Accept-Language`, затем fallback на default locale.

### `apps/web/messages/*.json`

Словари интерфейса.
Сейчас русский слой выступает базовым, а английский — override-слоем поверх него.

## Repo workflow

### `.codex/project-memory.md`

Versioned memory проекта.
Без его обновления существенная задача не считается нормально закрытой.

### `scripts/restore_context.sh`

Канонический restore context entrypoint.
Проверяет обязательные repo files и печатает их в стабильном порядке.

### `scripts/finalize_task.py`

Канонический finalize entrypoint.
Запускает verification, обновляет project memory и пишет worklog entry.

### `.githooks/pre-commit`

Не даёт коммитить product-owned изменения без:
- обновления `.codex/project-memory.md`
- обновления хотя бы одного файла в `docs/ru/`

### `.githooks/pre-push`

Не даёт пушить без verify workflow.

## Tests

### `tests/test_api.py`

Проверяет backend API и operator pages.
Если меняется UI backend-контура, locale behavior, company/commercial/quote/handoff flow — почти точно надо смотреть этот файл.

### `tests/test_repo_workflow.py`

Проверяет repo workflow helpers и обновление project memory.
