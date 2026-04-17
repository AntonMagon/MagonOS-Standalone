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
- `perf/`
  Versioned perf/load сценарии для локальной платформы.
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
- `project-map/page.tsx` — визуальная карта проекта: контур, риски, автоматические контуры и последние проверенные изменения
- `personalize/page.tsx` — страница границ/контракта

Важно:
- главная витрина не должна превращаться в декоративный 3D-экран без смысла; правая колонка обязана объяснять следующий рабочий шаг
- `project-map/page.tsx` не должен читать как сырой technical log; для русского locale он обязан отдавать нормальные деловые формулировки, а не полуанглийский project-memory dump

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
- dev shell теперь использует отдельный `MAGON_WEB_DIST_DIR=.next-dev`
- это нужно, чтобы параллельный `next build` не ломал живой runtime на `3000`
- launcher теперь считает unified shell ready только после успешного `GET /`
- это нужно, чтобы внешние smoke/perf проверки не ловили холодную компиляцию главной страницы как ложный runtime-failure

### `scripts/run_platform.sh`

Backend-only entrypoint для standalone runtime.

Важно:
- локально он по-прежнему предпочитает repo-owned `.venv/bin/python`
- если `.venv` нет, но пакет уже установлен в активный Python окружения, скрипт корректно падает назад на `python3`
- это нужно для CI smoke-runtime, где editable install делается в runner Python без локальной `.venv`

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

### `scripts/check_russian_locale_integrity.py`

Жёсткий guard для русского слоя.

Проверяет versioned source-of-truth:
- `apps/web/messages/ru.json`
- `docs/ru/current-project-state.md`
- `docs/ru/visuals/project-map.md`
- `docs/ru/visuals/project-map.json`

Если передан `--web-url`, дополнительно проходит живые страницы:
- `/`
- `/dashboard`
- `/ops-workbench`
- `/project-map`

И режет проход, если в русском shell всплыли английские доменные ярлыки вроде `company`, `review queue`, `feedback ledger / projection` или `quote intent / RFQ boundary`.

Дополнительно режет плохие гибридные формулировки в русском слое вроде:
- `worklog`
- `scope guard`
- `technical log`
- `project-memory dump`

### `scripts/run_playwright_cli.sh`

Project-safe wrapper вокруг установленного `playwright` skill.
Нужен для живой browser automation именно в этом репозитории:
- использует `~/.codex/skills/playwright/scripts/playwright_cli.sh`
- уводит `npx` cache в `.cache/npm-playwright`
- обходит проблему с root-owned файлами в `~/.npm`
- по умолчанию переиспользует одну живую playwright-сессию из `.cache/playwright-session`
- повторный `open` не должен плодить новые окна Chrome; если окно уже открыто, wrapper ведёт тот же браузер в новый URL
- это именно ручной lightweight-инструмент для одного окна, а не тяжёлый suite внутри каждого `verify`

Если нужно открыть живую страницу, снять snapshot, кликать по UI и ловить текстовые ошибки — стартовать лучше через этот wrapper.

### `scripts/platform_smoke_check.sh`

Быстрый probe для:
- `GET /health`
- `GET /status`
- `/`
- `/dashboard`
- `/ops-workbench`
- `/project-map`
- `/ui/companies`

Нужен, чтобы без полного suite быстро доказать, что backend/web/operator surfaces живы.

### `scripts/run_perf_suite.sh`

Канонический launcher для `k6`.
Сценарии лежат в:
- `perf/k6/smoke.js`
- `perf/k6/load.js`
- `perf/k6/stress.js`

Смысл:
- smoke — быстрый proof живости и latency budget
- load — умеренная нагрузка
- stress — жёсткий локальный предел

### `scripts/run_periodic_checks.py`

Лёгкий periodic runner.
Пишет:
- `.cache/periodic-checks-status.json`
- `.cache/periodic-checks.log`

Нужен, чтобы локальная машина сама периодически фиксировала:
- синхронность root docs
- актуальность visual map
- чистоту русского source-of-truth
- живость платформы
- утечки английских доменных ярлыков в русском shell
- k6 smoke при живом runtime

### `scripts/install_launchd_periodic_checks.sh`

Устанавливает локальный macOS LaunchAgent `com.magonos.periodic-checks`.
Это уже не Codex automation, а системный periodic runner уровня машины.

### `scripts/launchd_periodic_checks_status.sh`

Показывает:
- plist в `~/Library/LaunchAgents/`
- реальный `launchctl print`

Если periodic runner "вроде установлен", но реально не живёт, смотреть сюда.

### `src/magon_standalone/observability.py`

Env-gated backend observability helper.
Отвечает за:
- backend Sentry init
- safe WSGI wrapping
- отсутствие жёсткой зависимости на внешний DSN в обычном локальном режиме

### `apps/web/instrumentation-client.ts`

Browser-side Sentry init для Next shell.
Активируется только при наличии `NEXT_PUBLIC_MAGON_SENTRY_DSN`.

### `apps/web/sentry.server.config.ts`

Server-side Sentry init для Next shell.
Держит server capture отдельно от browser env, но не ломает dev-path без DSN.

### `scripts/run_repo_autosync.py`

Главный repo-native autosync runner.
Принимает список changed paths и не пытается угадывать “какой skill выбрать”, а запускает канонические действия репозитория:
- `scripts/sync_operating_docs.py`
- `scripts/update_project_visual_map.py`
- `./scripts/verify_workflow.sh`
- `./scripts/verify_workflow.sh --with-web`

Смысл:
- после сохранения файлов корневые `AGENTS.md` и `README.md` не должны отставать
- `/project-map` и visual docs тоже не должны жить отдельно
- verification должен запускаться по реальному контуру изменений

### `scripts/install_repo_automation.sh`

Installer постоянного Watchman trigger для этого репозитория.
Ставит trigger `magonos-repo-auto`, который следит только за source-of-truth путями и не слушает generated outputs.

### `scripts/repo_automation_status.sh`

Показывает текущий статус Watchman:
- версия
- watched roots
- trigger list для этого repo

### `scripts/sync_operating_docs.py`

Канонический синхронизатор корневых operating docs.
Собирает активный статус из `.codex/project-memory.md`, `docs/current-project-state.md`, repo-local skills и активных automation в `~/.codex/automations/`, после чего обновляет:
- `AGENTS.md`
- `README.md`

Нужен, чтобы корневые файлы не жили отдельной устаревшей жизнью после реальной работы в репозитории.

### `scripts/verify_workflow.sh`

Главная локальная verification-цепочка репозитория.
Сейчас она обязана проверять:
- shell syntax для канонических launcher- и guard-скриптов
- синхронность `AGENTS.md` и `README.md`
- backend/unit tests
- web typecheck при `--with-web`

Важно:
- browser automation wrapper `scripts/run_playwright_cli.sh` тоже включён в этот contract
- autosync scripts и watchman installer тоже входят в этот contract
- если verification не знает про новый launcher или guard, значит repo drift уже начался

## Codex automation topology

### `~/.codex/automations/`

Тут живут Codex cron-автоматизации, которые не заменяют локальный `launchd`, а дают inbox-facing контроль поверх репозитория.

Общий meta-skill для них теперь один:
- `automation-context-guard`

Его задача:
- всегда стартовать с `./scripts/restore_context.sh --check`
- тянуть один и тот же repo context bundle
- заставлять automation доверять каноническим файлам и командам, а не собственной интерпретации
- не давать дневным audit/review слоям жить "от башки"

Текущий рабочий набор:
- `Platform Smoke 2h`
- `Repo Guard 3h`
- `RU Locale Guard 6h`
- `Architecture Drift Watch`
- `Operator Flow Audit`
- `Visual Map Daily`
- `PR Branch Hygiene`
- `Daily Project Digest`
- `Nightly Deep Review`
- `Weekly Release Gate`

Смысловой порядок такой:
- сначала быстрые guard’ы и smoke
- потом дневные бизнес- и архитектурные аудиты
- потом вечерние review/digest
- в конце недели — release verdict

Это нужно, чтобы:
- локальный autosync не тащил на себе весь review-контур
- тяжёлые агенты не стреляли каждый час
- активная разработка не тонула в overlapping automation runs

## Naming contract для `skills/`

Repo-local skills больше не должны называться произвольно.

Теперь есть явный guard:
- `scripts/check_skill_naming.py`
- `src/magon_standalone/skill_naming.py`

Он проверяет:
- lowercase `kebab-case`
- от `2` до `4` токенов
- разрешённый первый токен действия
- совпадение имени папки и `name:` во frontmatter `SKILL.md`

Смысл:
- не плодить похожие skills с хаотичными именами
- не ломать читаемость automation prompt layer
- не путать repo-local skills с plugin/curated skills

### `Taskfile.yml`

Короткий task-runner слой поверх канонических repo scripts.
Нужен для предсказуемых команд:
- `task sync:root-docs`
- `task sync:visual-map`
- `task verify`
- `task verify:web`
- `task smoke:platform`
- `task perf:smoke`
- `task perf:load`
- `task perf:stress`
- `task checks:periodic`
- `task automation:install`
- `task automation:status`
- `task launchd:install`
- `task launchd:status`
- `task autosync:watch`

### `.watchmanconfig`

Root config для Watchman.
Нужен, чтобы watcher не тратил события на:
- `.git`
- `.venv`
- `node_modules`
- `.next`
- `.cache`
- `data`
- `__pycache__`

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
Нужен, когда надо быстро увидеть контур продукта, активный фокус, риски, локальные скиллы и автоматические контуры в графическом виде.

## Tests

### `tests/test_api.py`

Проверяет backend API и operator pages.
Если меняется UI backend-контура, locale behavior, company/commercial/quote/handoff flow — почти точно надо смотреть этот файл.

### `tests/test_repo_workflow.py`

Проверяет repo workflow helpers и обновление project memory.
