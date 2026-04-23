#!/usr/bin/env bash
set -euo pipefail

LABEL="${1:-com.magonos.launcher-watchdog}"
PLIST_PATH="$HOME/Library/LaunchAgents/$LABEL.plist"
SUPPORT_ROOT="$HOME/.codex/launchd-support/$LABEL"

echo "== LaunchAgent plist =="
if [[ -f "$PLIST_PATH" ]]; then
  echo "$PLIST_PATH"
  sed -n '1,120p' "$PLIST_PATH"
else
  echo "missing: $PLIST_PATH"
fi

echo
echo "== launchctl status =="
# RU: Для watchdog важен не только plist на диске, а факт, что launchctl реально держит агент и не падает по последнему запуску.
launchctl print "gui/$(id -u)/$LABEL" 2>&1 | sed -n '1,120p'

echo
echo "== launchd support path =="
# RU: Показываем именно support-path в домашней директории, чтобы сразу видеть новый launchd-root вне Desktop и свежие stdout/stderr агента.
if [[ -d "$SUPPORT_ROOT" ]]; then
  ls -la "$SUPPORT_ROOT"
else
  echo "missing: $SUPPORT_ROOT"
fi
