#!/usr/bin/env bash
set -euo pipefail

# RU: Historical wrapper сохранён только как совместимый alias; active local runtime обязан идти через run_foundation_unified.sh.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

echo "[magon-unified] scripts/run_unified_platform.sh is now an alias for scripts/run_foundation_unified.sh" >&2
exec "$REPO_ROOT/scripts/run_foundation_unified.sh" "$@"
