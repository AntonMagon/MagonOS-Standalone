#!/usr/bin/env bash
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WEB_DIR="$REPO_ROOT/apps/web"
BUILD_ID_FILE="$WEB_DIR/.next/BUILD_ID"

if [[ ! -d "$WEB_DIR/node_modules" ]]; then
  echo "[magon-web] installing web dependencies"
  (cd "$WEB_DIR" && npm ci)
fi

needs_build="0"

if [[ ! -f "$BUILD_ID_FILE" ]]; then
  needs_build="1"
else
  # RU: Пересобираем production bundle только если web-исходники новее текущего BUILD_ID, иначе не тратим время на лишний build при каждом запуске launcher.
  if find \
    "$WEB_DIR/app" \
    "$WEB_DIR/components" \
    "$WEB_DIR/lib" \
    "$WEB_DIR/messages" \
    "$WEB_DIR/package.json" \
    "$WEB_DIR/package-lock.json" \
    -type f -newer "$BUILD_ID_FILE" \
    -print -quit | grep -q .; then
    needs_build="1"
  fi
fi

if [[ "$needs_build" == "1" ]]; then
  echo "[magon-web] building production web bundle"
  (cd "$WEB_DIR" && npm run build)
else
  echo "[magon-web] reusing current production web bundle"
fi
