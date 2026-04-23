#!/usr/bin/env bash
set -euo pipefail

LABEL="${1:-com.magonos.periodic-checks}"
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
# RU: Статус показываем через launchctl print, потому что наличие plist само по себе не доказывает живой periodic runner.
launchctl print "gui/$(id -u)/$LABEL" 2>&1 | sed -n '1,120p'

echo
echo "== launchd support path =="
# RU: Support-path нужен в выводе статуса, чтобы periodic runner можно было диагностировать по home-root логам, а не по старым repo-файлам на Desktop.
if [[ -d "$SUPPORT_ROOT" ]]; then
  ls -la "$SUPPORT_ROOT"
else
  echo "missing: $SUPPORT_ROOT"
fi
