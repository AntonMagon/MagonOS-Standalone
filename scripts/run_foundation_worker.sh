#!/usr/bin/env bash
# RU: Скрипт проверяет или поднимает контур первой волны.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

cd "$REPO_ROOT"
exec "$REPO_ROOT/.venv/bin/celery" -A magon_standalone.foundation.celery_app.celery_app worker --loglevel="${MAGON_FOUNDATION_LOG_LEVEL:-INFO}"
