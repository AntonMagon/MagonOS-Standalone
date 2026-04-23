#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.magonos.launcher-watchdog"
INTERVAL="3600"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
SUPPORT_ROOT="$HOME/.codex/launchd-support/$LABEL"
HELPER_PATH="$SUPPORT_ROOT/run-agent.sh"

usage() {
  cat <<USAGE
Usage: scripts/install_launchd_launcher_watchdog.sh [options]

Installs the macOS LaunchAgent that keeps the standalone launcher alive.

Options:
  --interval <seconds>    StartInterval value (default: $INTERVAL)
  --label <label>         LaunchAgent label (default: $LABEL)
  --help                  Show this help
USAGE
}

while [[ $# -gt 0 ]]; do
  case "$1" in
    --interval)
      INTERVAL="$2"; shift 2 ;;
    --label)
      LABEL="$2"
      PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
      SUPPORT_ROOT="$HOME/.codex/launchd-support/$LABEL"
      HELPER_PATH="$SUPPORT_ROOT/run-agent.sh"
      shift 2 ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1 ;;
  esac
done

mkdir -p "$HOME/Library/LaunchAgents" "$REPO_ROOT/.cache" "$SUPPORT_ROOT"

cat >"$HELPER_PATH" <<EOF
#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$REPO_ROOT"
SCRIPT_PATH="\$1"
shift || true

# RU: launchd helper живёт вне Desktop repo, чтобы сам агент не падал на protected cwd/log path до старта Python.
# RU: Здесь намеренно вызываем versioned repo python/script напрямую, а не системный alias из shell-профиля пользователя.
PYTHON_BIN="\$REPO_ROOT/.venv/bin/python"
if [[ ! -x "\$PYTHON_BIN" ]]; then
  PYTHON_BIN="\$(command -v python3)"
fi
if [[ -z "\$PYTHON_BIN" ]]; then
  echo "Missing python runtime for launchd helper" >&2
  exit 78
fi

export PYTHONDONTWRITEBYTECODE=1
export PYTHONPATH="\$REPO_ROOT/src\${PYTHONPATH:+:\$PYTHONPATH}"
exec "\$PYTHON_BIN" "\$REPO_ROOT/\$SCRIPT_PATH" "\$@"
EOF
chmod +x "$HELPER_PATH"

# RU: Watchdog plist рендерим из versioned template, чтобы часовой restart-guard не жил отдельно от repo-контракта.
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/render_launchd_launcher_watchdog.py" \
  --interval "$INTERVAL" \
  --label "$LABEL" \
  --launchd-root "$SUPPORT_ROOT" \
  --program "$HELPER_PATH" \
  --output "$PLIST_PATH"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

echo "Installed LaunchAgent: $PLIST_PATH"
launchctl print "gui/$(id -u)/$LABEL" | sed -n '1,80p'
