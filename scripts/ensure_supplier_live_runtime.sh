#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PYTHON_BIN="$REPO_ROOT/.venv/bin/python"

if [ ! -x "$PYTHON_BIN" ]; then
  PYTHON_BIN="$(command -v python3 || command -v python)"
fi

if [ -z "${PYTHON_BIN:-}" ]; then
  echo "supplier-live-runtime: python interpreter not found" >&2
  exit 1
fi

check_runtime() {
  "$PYTHON_BIN" - <<'PY'
import json
import sys

from magon_standalone.supplier_intelligence.live_runtime import probe_live_runtime

result = probe_live_runtime(force_refresh=True)
print(json.dumps({"ok": result.ok, "detail": result.detail, "payload": result.payload}, ensure_ascii=False, indent=2))
raise SystemExit(0 if result.ok else 1)
PY
}

# RU: Сначала ставим live extra, затем только при реальном browser-launch failure подтягиваем bundled Chromium, чтобы runtime health отражал исполнимый path, а не просто наличие пакета.
"$PYTHON_BIN" -m pip install -e "$REPO_ROOT[live]"
if check_runtime; then
  exit 0
fi

"$PYTHON_BIN" -m playwright install chromium
check_runtime
