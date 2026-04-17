# Performance и observability

Этот файл фиксирует новый контур, который нужен проекту не для красоты, а чтобы не терять контроль над:
- скоростью
- runtime-ошибками
- периодическими проверками
- переходом от локального режима к реальной нагрузке

## Что теперь есть в репозитории

- `perf/k6/`
  Версионируемые k6-сценарии под локальную платформу:
  - `smoke.js`
  - `load.js`
  - `stress.js`
- `scripts/run_perf_suite.sh`
  Канонический launcher для k6.
  Важно: перед `k6` он теперь делает retry-aware warmup ключевых web routes, чтобы cold compile Next dev не выглядел как ложный perf-failure.
- `scripts/platform_smoke_check.sh`
  Быстрый probe backend/web/operator surfaces.
- `scripts/run_periodic_checks.py`
  Лёгкий периодический контур, который:
  - синхронизирует root docs
  - пересобирает visual map
  - проверяет русский source-of-truth
  - проверяет живость платформы
  - проверяет русский shell на ключевых маршрутах
  - запускает k6 smoke, если платформа жива
  Его liveness-probe теперь терпимее к холодному dev runtime и не краснеет только из-за первого долгого compile.
- `scripts/check_russian_locale_integrity.py`
  Жёсткий locale-guard для `apps/web/messages/ru.json`, `docs/ru/current-project-state.md`, `docs/ru/visuals/*` и живых маршрутов `/`, `/dashboard`, `/ops-workbench`, `/project-map`.
- `scripts/install_launchd_periodic_checks.sh`
  Ставит локальный macOS LaunchAgent.
- `scripts/launchd_periodic_checks_status.sh`
  Показывает реальный status LaunchAgent.
- `src/magon_standalone/observability.py`
  Env-gated backend observability для Sentry.
- `apps/web/instrumentation-client.ts`
  Browser-side Sentry init для Next shell.
- `apps/web/sentry.server.config.ts`
  Server-side Sentry init для Next shell.

## Канонические команды

Smoke платформы:

```bash
./scripts/platform_smoke_check.sh
```

Perf smoke:

```bash
./scripts/run_perf_suite.sh smoke
```

Perf load:

```bash
./scripts/run_perf_suite.sh load
```

Perf stress:

```bash
./scripts/run_perf_suite.sh stress
```

Через Task:

```bash
task smoke:platform
task perf:smoke
task perf:load
task perf:stress
task checks:periodic
./.venv/bin/python scripts/check_russian_locale_integrity.py --static-only
```

## Локальный periodic runner

Теперь можно держать локальный фоновый контур без открытого терминала:

```bash
./scripts/install_launchd_periodic_checks.sh --interval 1800
./scripts/launchd_periodic_checks_status.sh
```

Что он делает:
- запускается при логине
- потом каждые `StartInterval` секунд
- пишет status в `.cache/periodic-checks-status.json`
- пишет лог в `.cache/periodic-checks.log`
- если локальная платформа не поднята на целевых URL, не падает, а честно пишет `skip` по smoke/perf
- если предыдущий periodic-run ещё не закончился, новый запуск тоже не наслаивается поверх него, а пишет controlled `periodic-lock-skip`

Важно:
- это лёгкий periodic runner
- он не заменяет `verify_workflow`
- он не делает commit/push
- он не стартует платформу сам
- он проверяет уже живой repo/runtime-контур

## Как разведён тайминг

Слои теперь разделены так, чтобы они не мешали друг другу:

- file-watch autosync реагирует сразу на реальные изменения файлов
- локальный `launchd`-runner каждые `1800` секунд держит тихий maintenance-контур
- Codex automations работают как inbox-facing аудиты и review, а не как дубль локального runner

Правильная хронология теперь такая:

### 1. Мгновенный слой

- Watchman trigger `magonos-repo-auto`
  - реагирует на source-of-truth файлы
  - запускает repo-native sync и verify по реальному набору изменений

### 2. Локальный тихий слой

- `launchd` каждые `1800` секунд
  - `scripts/sync_operating_docs.py`
  - `scripts/update_project_visual_map.py`
  - `scripts/check_russian_locale_integrity.py --static-only`
  - runtime smoke и `k6 smoke`, только если локальная платформа уже жива

### 3. Частые Codex guard-автоматизации

- `Platform Smoke 2h`
  - каждые 2 часа
  - подтверждает живость backend/web/operator surfaces
- `Repo Guard 3h`
  - каждые 3 часа
  - ловит docs/runtime/skills drift
- `RU Locale Guard 6h`
  - каждые 6 часов
  - ловит английские утечки и плохой гибридный технический русский

### 4. Дневные смысловые аудиты

- `Architecture Drift Watch`
  - каждый день в `11:30`
  - следит за границами standalone и scope drift
- `Operator Flow Audit`
  - каждый день в `14:00`
  - проверяет операторский и supplier-intelligence путь
- `Visual Map Daily`
  - каждый день в `15:30`
  - проверяет, что визуальная карта не отстала от project memory и current-state
- `PR Branch Hygiene`
  - каждый день в `18:15`
  - проверяет, не пора ли резать накопившийся diff в PR и не уплыл ли `develop`

### 5. Вечерний review-слой

- `Daily Project Digest`
  - каждый день в `20:30`
  - собирает краткий итог по изменениям, зелёным проверкам и главным рискам
- `Nightly Deep Review`
  - каждый день в `21:15`
  - делает более тяжёлый code-review проход по свежему delta

### 6. Недельный gate

- `Weekly Release Gate`
  - пятница в `19:00`
  - даёт жёсткий verdict `Ready / Ready with caveats / Not ready`

Важно:
- лёгкие guard’ы идут чаще, потому что они дешёвые
- смысловые и архитектурные аудиты разведены по разным часам, чтобы не наслаиваться
- вечерние review идут после дневной активной разработки, чтобы не мешать рабочему темпу
- weekly release gate вынесен на конец недели, а не на понедельник утром

## Sentry env contract

### Backend

Минимум:

```bash
export MAGON_SENTRY_DSN='https://...'
```

Опционально:

```bash
export MAGON_SENTRY_ENV='local'
export MAGON_SENTRY_RELEASE='git-sha-or-tag'
export MAGON_SENTRY_TRACES_SAMPLE_RATE='0.2'
export MAGON_SENTRY_PROFILES_SAMPLE_RATE='0.1'
```

### Web / Next shell

Для browser-side capture:

```bash
export NEXT_PUBLIC_MAGON_SENTRY_DSN='https://...'
export NEXT_PUBLIC_MAGON_SENTRY_ENV='local'
export NEXT_PUBLIC_MAGON_SENTRY_RELEASE='git-sha-or-tag'
export NEXT_PUBLIC_MAGON_SENTRY_TRACES_SAMPLE_RATE='0.1'
export NEXT_PUBLIC_MAGON_SENTRY_REPLAYS_SESSION_SAMPLE_RATE='0'
export NEXT_PUBLIC_MAGON_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE='0.1'
```

Важно:
- без DSN Sentry не активируется
- текущий dev/runtime path без env-переменных не ломается
- observability intentionally env-gated

## Как это использовать правильно

Если менялся backend/runtime:
- `./scripts/platform_smoke_check.sh`
- `./scripts/run_perf_suite.sh smoke`

Если менялся web shell:
- `cd apps/web && npm run typecheck`
- `./scripts/platform_smoke_check.sh`
- `./scripts/run_perf_suite.sh smoke`

Если готовишься к более тяжёлой проверке:
- `./scripts/run_perf_suite.sh load`
- `./scripts/run_perf_suite.sh stress`

## Честная граница текущего контура

- `k6` сейчас меряет только локальный standalone runtime
- это ещё не multi-node performance envelope
- SQLite остаётся слабым местом для write-heavy конкурентной нагрузки
- когда сценарии начнут упираться не в UI, а в записи/блокировки/latency базы, это будет сигналом готовить путь к Postgres
