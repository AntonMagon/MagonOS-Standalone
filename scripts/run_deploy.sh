#!/usr/bin/env bash
set -euo pipefail

# RU: Production/VPS deploy entrypoint обязан поднимать только active foundation compose contour, а не старый WSGI/SQLite path.

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$REPO_ROOT/docker-compose.yml"
DEFAULT_ENV_FILE="$REPO_ROOT/.env.prod"
COMMAND="up"
ENV_FILE="${MAGON_DEPLOY_ENV_FILE:-$DEFAULT_ENV_FILE}"
BUILD_ON_UP="1"
DETACH="1"
FOLLOW_LOGS="0"
TAIL_LINES="${TAIL_LINES:-200}"
SERVICES=()

usage() {
  cat <<USAGE
Usage: scripts/run_deploy.sh [command] [options] [services...]

Commands:
  up         Build (by default) and start the foundation production contour
  down       Stop and remove the foundation production contour
  restart    Recreate the selected services
  status     Show compose status
  ps         Alias for status
  logs       Show compose logs
  build      Build selected services
  pull       Pull service images
  config     Render the resolved compose config
  help       Show this help

Options:
  --env-file <path>  Explicit env file (default: .env.prod)
  --build            Force build before up/restart
  --no-build         Skip build before up/restart
  --attach           Keep 'up' in the foreground
  --detach           Run 'up' in detached mode (default)
  --follow           Follow logs for the 'logs' command
  --tail <lines>     Tail lines for the 'logs' command (default: $TAIL_LINES)

Examples:
  ./scripts/run_deploy.sh
  ./scripts/run_deploy.sh up --build
  ./scripts/run_deploy.sh logs --follow api web
  ./scripts/run_deploy.sh config --env-file .env.prod
USAGE
}

if [[ $# -gt 0 ]]; then
  case "$1" in
    up|down|restart|status|ps|logs|build|pull|config|help|-h|--help)
      COMMAND="$1"
      shift
      ;;
  esac
fi

while [[ $# -gt 0 ]]; do
  case "$1" in
    --env-file)
      ENV_FILE="$2"
      shift 2
      ;;
    --build)
      BUILD_ON_UP="1"
      shift
      ;;
    --no-build)
      BUILD_ON_UP="0"
      shift
      ;;
    --attach)
      DETACH="0"
      shift
      ;;
    --detach)
      DETACH="1"
      shift
      ;;
    --follow)
      FOLLOW_LOGS="1"
      shift
      ;;
    --tail)
      TAIL_LINES="$2"
      shift 2
      ;;
    -h|--help|help)
      usage
      exit 0
      ;;
    *)
      SERVICES+=("$1")
      shift
      ;;
  esac
done

if [[ "$COMMAND" == "help" ]]; then
  usage
  exit 0
fi

require_command() {
  local binary="$1"
  if ! command -v "$binary" >/dev/null 2>&1; then
    echo "Missing required command: $binary" >&2
    exit 1
  fi
}

ensure_env_file_for_mutating_command() {
  case "$COMMAND" in
    up|restart|build|pull|config)
      if [[ ! -f "$ENV_FILE" ]]; then
        echo "Missing deploy env file: $ENV_FILE" >&2
        echo "Copy .env.prod.example to .env.prod and replace placeholder passwords first." >&2
        exit 1
      fi
      ;;
  esac
}

validate_production_secrets() {
  case "$COMMAND" in
    up|restart)
      ;;
    *)
      return 0
      ;;
  esac

  local key
  local value
  local invalid=0
  while IFS='=' read -r key value; do
    case "$key" in
      POSTGRES_PASSWORD)
        if [[ -z "$value" || "$value" == "magon" || "$value" == change-me* ]]; then
          echo "Refusing deploy with placeholder $key in $ENV_FILE" >&2
          invalid=1
        fi
        ;;
      MAGON_FOUNDATION_DEFAULT_ADMIN_PASSWORD|MAGON_FOUNDATION_DEFAULT_OPERATOR_PASSWORD|MAGON_FOUNDATION_DEFAULT_CUSTOMER_PASSWORD)
        if [[ -z "$value" || "$value" == admin123 || "$value" == operator123 || "$value" == customer123 || "$value" == change-me* ]]; then
          echo "Refusing deploy with placeholder $key in $ENV_FILE" >&2
          invalid=1
        fi
        ;;
    esac
  done < "$ENV_FILE"

  if [[ "$invalid" == "1" ]]; then
    echo "Set real passwords in $ENV_FILE before starting the VPS contour." >&2
    exit 1
  fi
}

compose_base=(docker compose -f "$COMPOSE_FILE")
if [[ -f "$ENV_FILE" ]]; then
  compose_base+=(--env-file "$ENV_FILE")
fi

run_compose() {
  "${compose_base[@]}" "$@"
}

require_command docker
ensure_env_file_for_mutating_command
validate_production_secrets

case "$COMMAND" in
  up)
    up_args=(up)
    if [[ "$BUILD_ON_UP" == "1" ]]; then
      up_args+=(--build)
    fi
    if [[ "$DETACH" == "1" ]]; then
      up_args+=(-d)
    fi
    if [[ ${#SERVICES[@]} -gt 0 ]]; then
      up_args+=("${SERVICES[@]}")
    fi
    run_compose "${up_args[@]}"
    ;;
  down)
    run_compose down --remove-orphans
    ;;
  restart)
    if [[ "$BUILD_ON_UP" == "1" ]]; then
      build_args=(build)
      if [[ ${#SERVICES[@]} -gt 0 ]]; then
        build_args+=("${SERVICES[@]}")
      fi
      run_compose "${build_args[@]}"
    fi
    up_args=(up -d --force-recreate)
    if [[ ${#SERVICES[@]} -gt 0 ]]; then
      up_args+=("${SERVICES[@]}")
    fi
    run_compose "${up_args[@]}"
    ;;
  status|ps)
    run_compose ps
    ;;
  logs)
    log_args=(logs --tail "$TAIL_LINES")
    if [[ "$FOLLOW_LOGS" == "1" ]]; then
      log_args+=(-f)
    fi
    if [[ ${#SERVICES[@]} -gt 0 ]]; then
      log_args+=("${SERVICES[@]}")
    fi
    run_compose "${log_args[@]}"
    ;;
  build)
    build_args=(build)
    if [[ ${#SERVICES[@]} -gt 0 ]]; then
      build_args+=("${SERVICES[@]}")
    fi
    run_compose "${build_args[@]}"
    ;;
  pull)
    pull_args=(pull)
    if [[ ${#SERVICES[@]} -gt 0 ]]; then
      pull_args+=("${SERVICES[@]}")
    fi
    run_compose "${pull_args[@]}"
    ;;
  config)
    run_compose config
    ;;
  *)
    echo "Unknown command: $COMMAND" >&2
    usage >&2
    exit 1
    ;;
esac
