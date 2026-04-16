#!/usr/bin/env bash
set -euo pipefail

LABEL="${1:-com.magonos.periodic-checks}"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"

echo "== LaunchAgent plist =="
if [[ -f "$PLIST_PATH" ]]; then
  echo "$PLIST_PATH"
  sed -n '1,120p' "$PLIST_PATH"
else
  echo "missing: $PLIST_PATH"
fi

echo
echo "== launchctl status =="
# RU: Статус показываем через launchctl print, потому что наличие plist само по себе не доказывает живой periodic runner.
launchctl print "gui/$(id -u)/$LABEL" 2>&1 | sed -n '1,120p'
