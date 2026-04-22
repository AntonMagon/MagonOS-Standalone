#!/usr/bin/env bash
# RU: Active foundation runtime должен поднимать локальный Postgres/Redis явно, а не молча сваливаться в SQLite fallback.
set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
POSTGRES_USER="${POSTGRES_USER:-magon}"
POSTGRES_DB="${POSTGRES_DB:-magon}"

ensure_docker() {
  if docker info >/dev/null 2>&1; then
    return 0
  fi

  if command -v colima >/dev/null 2>&1; then
    echo "[foundation-infra] docker daemon is not running; starting colima"
    colima start \
      --cpu "${MAGON_COLIMA_CPU:-2}" \
      --memory "${MAGON_COLIMA_MEMORY:-4}" \
      --disk "${MAGON_COLIMA_DISK:-20}" >/dev/null
  fi

  if ! docker info >/dev/null 2>&1; then
    echo "[foundation-infra] docker daemon is unavailable; cannot start PostgreSQL/Redis runtime" >&2
    exit 1
  fi
}

wait_for_postgres() {
  for _ in $(seq 1 60); do
    if docker compose exec -T db pg_isready -U "$POSTGRES_USER" -d "$POSTGRES_DB" >/dev/null 2>&1; then
      return 0
    fi
    sleep 1
  done
  echo "[foundation-infra] postgres failed to become ready" >&2
  exit 1
}

wait_for_redis() {
  for _ in $(seq 1 60); do
    if [[ "$(docker compose exec -T redis redis-cli ping 2>/dev/null || true)" == "PONG" ]]; then
      return 0
    fi
    sleep 1
  done
  echo "[foundation-infra] redis failed to become ready" >&2
  exit 1
}

cd "$REPO_ROOT"
ensure_docker
docker compose up -d db redis >/dev/null
wait_for_postgres
wait_for_redis
echo "[foundation-infra] postgres and redis are ready"
