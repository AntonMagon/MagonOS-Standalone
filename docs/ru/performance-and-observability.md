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
  - проверяет живость платформы
  - запускает k6 smoke, если платформа жива
  Его liveness-probe теперь терпимее к холодному dev runtime и не краснеет только из-за первого долгого compile.
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

- локальный `launchd`-runner остаётся частым silent-maintenance слоем
- Codex automations не должны дублировать его каждый час одним и тем же тяжёлым проходом
- правильный контур такой:
  - `launchd` каждые `1800` секунд держит sync/smoke/perf-smoke в фоне
  - `Platform Smoke` идёт реже как inbox-facing контроль живости
  - `Repo Guard` идёт ещё реже как drift-аудит
  - `Visual Map` идёт редко, потому что карта и так пересобирается file-watch/periodic контуром

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
