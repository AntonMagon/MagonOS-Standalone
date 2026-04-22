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
browser_value=""
skip_browser_value="false"
FILTERED_ARGS=()
for arg in "$@"; do
  if [[ "${skip_browser_value}" == "true" ]]; then
    browser_value="${arg}"
    has_browser_flag="true"
    skip_browser_value="false"
    continue
  fi
  case "$arg" in
    --session|--session=*|-s|-s=*)
      has_session_flag="true"
      FILTERED_ARGS+=("$arg")
      ;;
    --browser)
      has_browser_flag="true"
      skip_browser_value="true"
      ;;
    --browser=*)
      has_browser_flag="true"
      browser_value="${arg#*=}"
      ;;
    *)
      FILTERED_ARGS+=("$arg")
      ;;
  esac
done

if [[ "${skip_browser_value}" == "true" ]]; then
  echo "Missing value for --browser." >&2
  exit 2
fi

if [[ "${has_browser_flag}" == "true" ]]; then
  if [[ -z "${browser_value}" || "${browser_value}" == "${DEFAULT_BROWSER}" ]]; then
    :
  else
    echo "Only Google Chrome is allowed in this repository. Use --browser=chrome or omit the flag." >&2
    exit 2
  fi
fi

set -- "${FILTERED_ARGS[@]}"

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

# RU: Все browser-driven команды проходят через curated wrapper, чтобы policy и reuse одной сессии оставались едиными.
exec bash "${PWCLI}" "$@"
