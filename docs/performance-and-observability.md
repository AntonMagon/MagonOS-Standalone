# Performance and observability

This document tracks the repo-level performance and runtime-observability layer.

Included:
- versioned k6 scenarios under `perf/k6/`
- `scripts/run_perf_suite.sh`
- `scripts/platform_smoke_check.sh`
- `scripts/run_periodic_checks.py`
- local macOS LaunchAgent install/status scripts
- env-gated Sentry prep for backend and Next shell

Primary local commands:

```bash
./scripts/platform_smoke_check.sh
./scripts/run_perf_suite.sh smoke
./scripts/run_perf_suite.sh load
./scripts/run_perf_suite.sh stress
./scripts/install_launchd_periodic_checks.sh --interval 1800
./scripts/launchd_periodic_checks_status.sh
```

Task shortcuts:

```bash
task smoke:platform
task perf:smoke
task perf:load
task perf:stress
task checks:periodic
```
