#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.magonos.launcher-watchdog"
INTERVAL="3600"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

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
      shift 2 ;;
    --help|-h)
      usage; exit 0 ;;
    *)
      echo "Unknown option: $1" >&2
      usage >&2
      exit 1 ;;
  esac
done

mkdir -p "$HOME/Library/LaunchAgents" "$REPO_ROOT/.cache"

# RU: Watchdog plist рендерим из versioned template, чтобы часовой restart-guard не жил отдельно от repo-контракта.
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/render_launchd_launcher_watchdog.py" \
  --interval "$INTERVAL" \
  --label "$LABEL" \
  --output "$PLIST_PATH"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

echo "Installed LaunchAgent: $PLIST_PATH"
launchctl print "gui/$(id -u)/$LABEL" | sed -n '1,80p'
