#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
LABEL="com.magonos.periodic-checks"
INTERVAL="1800"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

usage() {
  cat <<USAGE
Usage: scripts/install_launchd_periodic_checks.sh [options]

Installs the macOS LaunchAgent that runs repo periodic checks on an interval.

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

# RU: Plist рендерим из versioned repo-template, чтобы launchd не жил отдельно от текущего standalone contract.
"$REPO_ROOT/.venv/bin/python" "$REPO_ROOT/scripts/render_launchd_periodic_checks.py" \
  --interval "$INTERVAL" \
  --label "$LABEL" \
  --output "$PLIST_PATH"

launchctl bootout "gui/$(id -u)" "$PLIST_PATH" >/dev/null 2>&1 || true
launchctl bootstrap "gui/$(id -u)" "$PLIST_PATH"
launchctl kickstart -k "gui/$(id -u)/$LABEL" >/dev/null 2>&1 || true

echo "Installed LaunchAgent: $PLIST_PATH"
launchctl print "gui/$(id -u)/$LABEL" | sed -n '1,80p'
