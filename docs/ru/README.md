# Русский слой документации

Эта папка — обязательный русскоязычный слой проекта.
Она существует не для красоты, а чтобы состояние репозитория и смысл кода можно было читать без постоянной ручной распаковки контекста.
Корневые `AGENTS.md` и `README.md` теперь считаются частью того же operating-layer и автоматически пересобираются из project memory, skills и automation state.

## Обязательное правило

Если меняются product-owned файлы, в том же коммите должен обновиться хотя бы один файл в `docs/ru/`.

Под product-owned файлами понимаются:
- `src/`
- `apps/web/`
- `scripts/`
- `tests/`
- `perf/`
- `AGENTS.md`
- `docs/current-project-state.md`
- `docs/ru/`
- `.codex/config.toml`
- `docs/repo-workflow.md`

## Что должно лежать в `docs/ru/`

- `current-project-state.md`
  Русское описание текущей рабочей правды проекта.
- `repo-workflow.md`
  Русское описание обязательного workflow репозитория.
- `code-map.md`
  Русская карта кода: какие директории и ключевые файлы за что отвечают.
- `performance-and-observability.md`
  Русское описание perf/load/launchd/Sentry-контура.
- `visuals/`
  Отдельная папка для визуальных карт проекта, чтобы состояние системы читалось не только текстом.

## Правило по комментариям в коде

Если меняется неочевидная логика, рядом с ней должен появиться короткий комментарий или docstring на русском языке.
Для изменённого кодового файла в staged diff должна появиться хотя бы одна добавленная строка с явным маркером `RU:`.

Обязательно комментировать на русском:
- business rules
- routing / qualification transitions
- locale / i18n fallback logic
- persistence / projection logic
- workflow guards / git hooks
- любые места, где без пояснения непонятно "зачем так, а не иначе"

Не нужно комментировать:
- очевидные присваивания
- простые JSX/HTML обёртки
- примитивные getters/setters

Допустимые примеры:
- `# RU: почему здесь fallback идёт через cookie`
- `// RU: зачем этот guard срабатывает до commit`
- `/* RU: почему этот переход нельзя уносить в ERP */`

## Как использовать

Перед существенной работой:

```bash
./scripts/restore_context.sh
```

После существенной работы:

1. обновить нужный файл в `docs/ru/`
2. добавить нужные русские комментарии в изменённый код
3. пройти проверку
4. обновить `.codex/project-memory.md`
5. коммитить и пушить

Важно:
- `./.venv/bin/python scripts/finalize_task.py ...` теперь сам пересобирает корневые `AGENTS.md` и `README.md`
- `./scripts/verify_workflow.sh` и `pre-commit` режут проход, если эти корневые файлы отстали

## Локальные project skills

В репозитории есть локальные skills в `skills/*/SKILL.md`.
Они нужны, чтобы не поднимать один и тот же рабочий контекст вручную на каждом проходе.

Текущий набор:
- `audit-docs-vs-runtime` — аудит истины проекта по коду, тестам и runtime
- `git-safe-commit` — узкий безопасный commit/push path
- `operate-platform` — запуск и проверка standalone-платформы
- `operate-standalone-intelligence` — pipeline и operator contour
- `web-regression-pass` — browser smoke/regression для web shell и operator pages
- `ci-watch-fix` — разбор и починка CI/verification failures минимальным патчем
- `verify-implementation` — жёсткий post-implementation verify pass
- `release-readiness-gate` — финальный verdict по готовности к handoff/release
- `docs-sync-curator` — синхронизация docs/ и docs/ru/ с реальным кодом
- `skill-pattern-scan` — поиск повторяющихся workflow-паттернов под новые skills
- `donor-boundary-audit` — безопасный аудит donor/Odoo-границы
- `project-visual-map` — обновление визуальной карты проекта и графического слоя `/project-map`

## Как эти skills реально активируются

Факт: одних файлов в `skills/` недостаточно.
Текущая среда Codex реально подхватывает skills из `~/.codex/skills/`.

Поэтому для project-local skills добавлен канонический installer:

```bash
./scripts/install_project_skills.sh
```

Что он делает:
- берёт каждый каталог из `skills/*`
- создаёт symlink в `~/.codex/skills/`
- оставляет сам репозиторий single source of truth

Важно:
- после линковки нужен рестарт Codex, иначе текущая живая сессия не переиндексирует skill list
- без этого repo skills остаются только проектными playbooks, а не live-discovered skills среды

## Дополнительные curated skills для этой платформы

Кроме repo-local skills, для реальной отладки и автоматизации этой платформы уже подключены:
- `playwright-interactive`
  Постоянная браузерная сессия для длинных UI-разборов. Полезно, когда нужно не переоткрывать браузер после каждого изменения. Важно: этому skill нужен новый сеанс Codex с включённым `js_repl`; глобальный `~/.codex/config.toml` уже должен содержать `[features] js_repl = true`.
- `screenshot`
  Системные и оконные скриншоты, когда Playwright недостаточно или нужно увидеть нативное окно/overlay.
- `cli-creator`
  Нужен не для ежедневной правки UI, а для следующего шага: когда проекту понадобится собственный короткий CLI вместо россыпи отдельных команд.

## Канонический Playwright launcher для этого репозитория

Для этой платформы добавлен отдельный wrapper:

```bash
./scripts/run_playwright_cli.sh --help
```

Он нужен, потому что:
- использует установленный skill `playwright`
- уводит `npx` cache в локальную папку репозитория
- не зависит от проблемного `~/.npm`, где уже встречались root-owned файлы

Если нужен быстрый headed browser run по проекту, использовать нужно его:

```bash
./scripts/run_playwright_cli.sh open http://127.0.0.1:3000/ --headed
```

## Локальная автоматизация по изменению файлов

Теперь в репозитории есть отдельный repo-native autosync слой, который нужен именно как обход ограничения Codex: skills не стартуют сами на каждый save, но repo может сам запускать свои канонические действия.

Что для этого есть:
- `.watchmanconfig`
  Конфиг root watch для Watchman.
- `Taskfile.yml`
  Короткие команды `task sync:root-docs`, `task verify:web`, `task automation:install`, `task autosync:watch`.
- `scripts/install_repo_automation.sh`
  Ставит постоянный Watchman trigger `magonos-repo-auto`.
- `scripts/run_repo_autosync.py`
  Принимает changed paths, затем запускает:
  - `scripts/sync_operating_docs.py`
  - `scripts/update_project_visual_map.py`
  - `./scripts/verify_workflow.sh` или `./scripts/verify_workflow.sh --with-web`
- `scripts/repo_automation_status.sh`
  Показывает, что Watchman реально смотрит этот repo и что trigger установлен.

Канонический запуск:

```bash
./scripts/install_repo_automation.sh
./scripts/repo_automation_status.sh
```

Ручной fallback без background trigger:

```bash
task autosync:watch
```

Важно:
- autosync не делает commit/push сам
- autosync не выбирает “skill” на каждый save
- autosync запускает именно repo-native scripts, чтобы корневые docs, visual map и verification не отставали от реального состояния

## Performance / periodic / observability слой

Теперь поверх autosync добавлен ещё один технический контур:
- `perf/k6/` — versioned smoke/load/stress сценарии
- `scripts/run_perf_suite.sh` — канонический k6 launcher
- `scripts/platform_smoke_check.sh` — быстрый probe локальных surfaces
- `scripts/run_periodic_checks.py` — лёгкий periodic runner
- `scripts/install_launchd_periodic_checks.sh` — установка macOS LaunchAgent
- `scripts/launchd_periodic_checks_status.sh` — живой status launchd job
- `src/magon_standalone/observability.py` и `apps/web/instrumentation-client.ts` — env-gated Sentry prep

Подробности:
- `docs/ru/performance-and-observability.md`
