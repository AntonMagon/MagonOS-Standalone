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
- `docs/ru/visuals/`
  Визуальная папка проекта: сгенерированные графические карты и структурные схемы.
- `skills/`
  Локальные project-specific skills для типовых режимов работы по этому репозиторию.
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
- `project-map/page.tsx` — визуальная карта проекта: контур, риски, automation loops и последние verified changes
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

### `apps/web/lib/project-visual-map.ts`

Тонкий loader для визуальной карты проекта.
Читает `docs/ru/visuals/project-map.json` от корня репозитория и отдаёт уже сгенерированный payload в web shell без пересборки project state на лету.

### `apps/web/messages/*.json`

Словари интерфейса.
Сейчас русский слой выступает базовым, а английский — override-слоем поверх него.
Для пользовательских экранов русский текст должен звучать как нормальный деловой интерфейс, а не как внутренняя инженерная терминология вроде "runtime", "контур ради контура" или "сырые записи" без пояснения.

## Repo workflow

### `.codex/project-memory.md`

Versioned memory проекта.
Без его обновления существенная задача не считается нормально закрытой.

### `scripts/restore_context.sh`

Канонический restore context entrypoint.
Проверяет обязательные repo files и печатает их в стабильном порядке.

### `scripts/run_unified_platform.sh`

Канонический entrypoint для полного standalone shell:
- backend
- public web shell
- operator routes через web

Важно:
- теперь скрипт поднимает Next dev с `WATCHPACK_POLLING=true`
- это нужно, чтобы локальный unified shell не падал на macOS с `EMFILE: too many open files`

### `Start_Platform.command`

Desktop launcher-обёртка для локального старта с Finder/двойного клика.
Нужен для удобства:
- жёстко освободить backend/web порты
- при необходимости очистить локальную SQLite БД
- открыть браузер автоматически

Важно:
- это не новый канонический runtime path
- реальный all-in-one entrypoint всё равно `scripts/run_unified_platform.sh`
- `Start_Platform.command` просто подготавливает окружение и в foreground передаёт управление туда

### `scripts/finalize_task.py`

Канонический finalize entrypoint.
Запускает verification, обновляет project memory и пишет worklog entry.

### `.githooks/pre-commit`

Не даёт коммитить product-owned изменения без:
- обновления `.codex/project-memory.md`
- обновления хотя бы одного файла в `docs/ru/`
- добавленного `RU:` пояснения в staged diff каждого изменённого кодового файла

### `.githooks/pre-push`

Не даёт пушить без verify workflow.

### `scripts/check_russian_comment_contract.py`

Проверяет comment-contract по изменённому коду.
Если кодовый файл меняется, а в staged diff нет добавленной строки с `RU:` и русским текстом, commit должен падать.

### `scripts/update_project_visual_map.py`

Генератор визуальной карты проекта.
Собирает данные из `docs/current-project-state.md`, `docs/ru/current-project-state.md` и `.codex/project-memory.md`, затем обновляет:
- `docs/ru/visuals/project-map.md`
- `docs/ru/visuals/project-map.json`
- `docs/visuals/project-map.md`
- `docs/visuals/project-map.json`

### `scripts/run_playwright_cli.sh`

Project-safe wrapper вокруг установленного `playwright` skill.
Нужен для живой browser automation именно в этом репозитории:
- использует `~/.codex/skills/playwright/scripts/playwright_cli.sh`
- уводит `npx` cache в `.cache/npm-playwright`
- обходит проблему с root-owned файлами в `~/.npm`

Если нужно открыть живую страницу, снять snapshot, кликать по UI и ловить текстовые ошибки — стартовать лучше через этот wrapper.

### `scripts/verify_workflow.sh`

Главная локальная verification-цепочка репозитория.
Сейчас она обязана проверять:
- shell syntax для канонических launcher- и guard-скриптов
- backend/unit tests
- web typecheck при `--with-web`

Важно:
- browser automation wrapper `scripts/run_playwright_cli.sh` тоже включён в этот contract
- если verification не знает про новый launcher или guard, значит repo drift уже начался

## Skills

### `skills/audit-docs-vs-runtime/SKILL.md`

Локальный skill для аудита того, что реально true в standalone-репозитории.
Должен идти от кода и проверок, а не от устаревших текстов.

### `skills/git-safe-commit/SKILL.md`

Локальный skill для узкого и дисциплинированного commit/push-пути.
Должен уважать `.codex/project-memory.md` и `docs/ru/`.

### `skills/operate-platform/SKILL.md`

Локальный skill для запуска и проверки активной standalone-платформы.

### `skills/operate-standalone-intelligence/SKILL.md`

Локальный skill для pipeline/operator-контура, включая company -> opportunity -> quote intent -> handoff.

### `skills/web-regression-pass/SKILL.md`

Локальный skill для browser smoke/regression.
Нужен, когда надо не "пощёлкать руками", а реально проверить web shell и операторские страницы через устойчивый regression-path.

### `skills/ci-watch-fix/SKILL.md`

Локальный skill для разбора красного CI или локального verification guard.
Нужен, когда надо починить точную причину падения минимальным патчем.

### `skills/verify-implementation/SKILL.md`

Локальный skill для пост-implementation проверки.
Нужен, когда код уже написан, но надо жёстко доказать, что задача действительно закрыта и ничего рядом не сломалось.

### `skills/release-readiness-gate/SKILL.md`

Локальный skill для финального verdict по готовности.
Нужен перед merge, handoff, demo или release, когда требуется не "вроде ок", а явное `Ready / Ready with caveats / Not ready`.

### `skills/docs-sync-curator/SKILL.md`

Локальный skill для синхронизации `docs/`, `docs/ru/`, `AGENTS.md`, `.codex/config.toml` и script references с реальным runtime.

### `skills/skill-pattern-scan/SKILL.md`

Локальный skill для поиска повторяющихся проектных паттернов и предложения новых skills без дублирования существующих.

### `skills/donor-boundary-audit/SKILL.md`

Локальный skill для безопасного чтения donor/Odoo-репозитория.
Нужен, когда надо достать бизнес-правила из legacy-кода, но не тащить donor-runtime обратно в standalone.

### `skills/project-visual-map/SKILL.md`

Локальный skill для обновления и ревизии визуальной карты проекта.
Нужен, когда надо быстро увидеть контур продукта, активный фокус, риски, skills и automation loops в графическом виде.

## Tests

### `tests/test_api.py`

Проверяет backend API и operator pages.
Если меняется UI backend-контура, locale behavior, company/commercial/quote/handoff flow — почти точно надо смотреть этот файл.

### `tests/test_repo_workflow.py`

Проверяет repo workflow helpers и обновление project memory.
