#!/usr/bin/env bash

resolve_repo_python() {
  local repo_root="${1:?repo_root is required}"
  # RU: CI не обязан поднимать локальную .venv, поэтому verification/smoke scripts должны уметь работать и через runner python.
  if [[ -n "${MAGON_REPO_PYTHON_BIN:-}" ]]; then
    printf '%s\n' "$MAGON_REPO_PYTHON_BIN"
    return 0
  fi
  if [[ -x "$repo_root/.venv/bin/python" ]]; then
    printf '%s\n' "$repo_root/.venv/bin/python"
    return 0
  fi
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi
  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi
  echo "resolve_repo_python: python interpreter not found" >&2
  return 1
}

run_repo_alembic() {
  local repo_root="${1:?repo_root is required}"
  shift
  local python_bin
  python_bin="$(resolve_repo_python "$repo_root")"
  "$python_bin" -m alembic "$@"
}
