#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PWCLI="${CODEX_HOME}/skills/playwright/scripts/playwright_cli.sh"
PLAYWRIGHT_CACHE_DIR="${REPO_ROOT}/.cache/npm-playwright"

if ! command -v npx >/dev/null 2>&1; then
  echo "npx is required to run Playwright CLI." >&2
  exit 1
fi

if [[ ! -x "${PWCLI}" ]]; then
  echo "Missing Playwright wrapper: ${PWCLI}" >&2
  echo "Install or restore the curated playwright skill in ~/.codex/skills first." >&2
  exit 1
fi

mkdir -p "${PLAYWRIGHT_CACHE_DIR}"

# RU: Принудительно уводим npx cache в репозиторий, чтобы Playwright не падал из-за root-owned файлов в ~/.npm.
export NPM_CONFIG_CACHE="${PLAYWRIGHT_CACHE_DIR}"

exec bash "${PWCLI}" "$@"
