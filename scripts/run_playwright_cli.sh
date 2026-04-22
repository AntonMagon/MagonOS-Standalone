#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
CODEX_HOME="${CODEX_HOME:-$HOME/.codex}"
PWCLI="${CODEX_HOME}/skills/playwright/scripts/playwright_cli.sh"
PLAYWRIGHT_CACHE_DIR="${REPO_ROOT}/.cache/npm-playwright"
SESSION_FILE="${REPO_ROOT}/.cache/playwright-session"
DEFAULT_BROWSER="chrome"

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

has_session_flag="false"
has_browser_flag="false"
for arg in "$@"; do
  case "$arg" in
    --session|--session=*)
      has_session_flag="true"
      ;;
  esac
  case "$arg" in
    --browser|--browser=*)
      has_browser_flag="true"
      ;;
  esac
done

session_name() {
  if [[ -f "${SESSION_FILE}" ]]; then
    tr -d '\n' < "${SESSION_FILE}"
  fi
}

session_is_open() {
  local current_session="$1"
  [[ -n "${current_session}" ]] || return 1
  bash "${PWCLI}" list 2>/dev/null | grep -Fq -- "- ${current_session}:"
}

remember_session() {
  local current_session="$1"
  [[ -n "${current_session}" ]] || return 0
  printf '%s' "${current_session}" > "${SESSION_FILE}"
}

forget_session() {
  rm -f "${SESSION_FILE}"
}

COMMAND="${1:-}"
CURRENT_SESSION="$(session_name)"
browser_arg_supported="false"

case "${COMMAND}" in
  ""|--help|-h|list|close|close-all|kill-all|attach|install|install-browser)
    browser_arg_supported="false"
    ;;
  *)
    # RU: Meta-команды playwright-cli не принимают --browser, поэтому chrome-фиксацию добавляем только в реальные browser-driven действия.
    browser_arg_supported="true"
    ;;
esac

if [[ "${has_browser_flag}" == "true" ]]; then
  for arg in "$@"; do
    case "$arg" in
      --browser=chrome)
        ;;
      --browser=*|--browser)
        echo "Only Google Chrome is allowed in this repository. Use --browser=chrome or omit the flag." >&2
        exit 2
        ;;
    esac
  done
fi

if [[ "${has_session_flag}" != "true" && -n "${CURRENT_SESSION}" ]] && session_is_open "${CURRENT_SESSION}"; then
  export PLAYWRIGHT_CLI_SESSION="${CURRENT_SESSION}"
fi

case "${COMMAND}" in
  open)
    # RU: Если живая playwright-сессия уже есть, повторный `open` не должен плодить новые Chrome-окна; переиспользуем то же окно и просто переходим на новый URL.
    if [[ "${has_session_flag}" != "true" && -n "${CURRENT_SESSION}" ]] && session_is_open "${CURRENT_SESSION}"; then
      if [[ $# -ge 2 ]] && [[ "${2}" != --* ]]; then
        shift
        exec bash "${PWCLI}" goto "$@"
      fi
      exec bash "${PWCLI}" attach "${CURRENT_SESSION}"
    fi
    remember_session "default"
    ;;
  install-browser)
    # RU: Репозиторий жёстко фиксирован на Google Chrome; лишние browser runtimes не ставим и не поддерживаем.
    if [[ $# -ge 2 && "${2}" != "chrome" ]]; then
      echo "Only Google Chrome is allowed in this repository." >&2
      exit 2
    fi
    ;;
  attach)
    if [[ $# -ge 2 && -n "${2}" ]]; then
      remember_session "${2}"
    fi
    ;;
  close|close-all|kill-all)
    forget_session
    ;;
esac

# RU: Все browser-driven проверки и ручные walkthrough в этом репозитории идут только через Google Chrome.
if [[ "${browser_arg_supported}" == "true" && "${has_browser_flag}" != "true" ]]; then
  exec bash "${PWCLI}" "$@" --browser="${DEFAULT_BROWSER}"
fi

exec bash "${PWCLI}" "$@"
