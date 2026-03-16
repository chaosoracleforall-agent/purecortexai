#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_vm.sh [--pull] [--skip-build] [--tail-logs]

Supported PURECORTEX deployment flow for the GCP VM.

Options:
  --pull        Update the checked out branch with git pull --ff-only before deploy.
  --skip-build  Reuse existing images and skip docker compose build.
  --tail-logs   Follow signer, backend, and frontend logs after deployment succeeds.
  -h, --help    Show this help message.
EOF
}

log() {
  printf '[deploy_vm] %s\n' "$*"
}

fail() {
  printf '[deploy_vm] ERROR: %s\n' "$*" >&2
  exit 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    fail "Missing required command: $1"
  fi
}

read_env_key() {
  python3 - "$ENV_FILE" "$1" <<'PY'
from pathlib import Path
import sys

path = Path(sys.argv[1])
target = sys.argv[2]

for line in path.read_text().splitlines():
    stripped = line.strip()
    if not stripped or stripped.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    if key == target:
        print(value)
        break
PY
}

resolve_compose() {
  if docker compose version >/dev/null 2>&1; then
    COMPOSE=(docker compose)
    return
  fi

  if command -v docker-compose >/dev/null 2>&1; then
    COMPOSE=(docker-compose)
    return
  fi

  fail "Docker Compose not found. Install either 'docker compose' or 'docker-compose'."
}

git_tree_clean() {
  local status
  status="$(git status --porcelain)"
  [[ -z "${status}" ]]
}

wait_for_backend_health() {
  local attempt
  for attempt in $(seq 1 20); do
    if "${COMPOSE[@]}" exec -T backend python - <<'PY' >/dev/null 2>&1
import urllib.request

with urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5) as response:
    if response.status != 200:
        raise SystemExit(1)
PY
    then
      log "Backend health check passed."
      return 0
    fi

    sleep 3
  done

  return 1
}

wait_for_signer_health() {
  local attempt
  for attempt in $(seq 1 20); do
    if "${COMPOSE[@]}" exec -T signer python - <<'PY' >/dev/null 2>&1
import os
import sys

socket_path = os.environ.get("PURECORTEX_SIGNER_SOCKET_PATH", "/run/purecortex/socket/signer.sock")
sys.exit(0 if os.path.exists(socket_path) else 1)
PY
    then
      log "Signer socket check passed."
      return 0
    fi

    sleep 2
  done

  return 1
}

wait_for_database_health() {
  if [[ -n "${CLOUD_SQL_CONNECTION_NAME}" ]]; then
    local attempt
    for attempt in $(seq 1 20); do
      if "${COMPOSE[@]}" exec -T backend python - <<'PY' >/dev/null 2>&1
import socket

with socket.create_connection(("127.0.0.1", 5432), timeout=5):
    pass
PY
      then
        log "Cloud SQL proxy connectivity check passed."
        return 0
      fi

      sleep 3
    done

    return 1
  fi

  local attempt
  for attempt in $(seq 1 20); do
    if "${COMPOSE[@]}" exec -T postgres pg_isready -U purecortex -d purecortex >/dev/null 2>&1; then
      log "Postgres health check passed."
      return 0
    fi

    sleep 2
  done

  return 1
}

run_database_migrations() {
  log "Applying Alembic migrations..."
  "${COMPOSE[@]}" exec -T backend alembic upgrade head
}

PULL_CHANGES=false
SKIP_BUILD=false
TAIL_LOGS=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --pull)
      PULL_CHANGES=true
      ;;
    --skip-build)
      SKIP_BUILD=true
      ;;
    --tail-logs)
      TAIL_LOGS=true
      ;;
    -h|--help)
      usage
      exit 0
      ;;
    *)
      fail "Unknown argument: $1"
      ;;
  esac
  shift
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
ENV_FILE="${ROOT_DIR}/.env"

require_cmd docker
require_cmd git

if ! docker info >/dev/null 2>&1; then
  fail "Docker daemon is not reachable."
fi

resolve_compose

if [[ ! -f "${ENV_FILE}" ]]; then
  fail "Missing ${ENV_FILE}. Copy .env.example to .env on the VM before deploying."
fi

cd "${ROOT_DIR}"

require_cmd python3
python3 scripts/sync_runtime_env.py

CLOUD_SQL_CONNECTION_NAME="$(read_env_key PURECORTEX_CLOUD_SQL_CONNECTION_NAME)"

if [[ "${PULL_CHANGES}" == true ]]; then
  if ! git_tree_clean; then
    fail "Git working tree is not clean. Commit or stash changes before running --pull."
  fi

  log "Fetching latest changes..."
  git fetch --all --prune
  git pull --ff-only
fi

log "Using compose command: ${COMPOSE[*]}"

if [[ "${SKIP_BUILD}" == false ]]; then
  log "Building images..."
  "${COMPOSE[@]}" build
fi

log "Starting services..."
SERVICES=(redis signer backend frontend oauth2-proxy nginx)
if [[ -n "${CLOUD_SQL_CONNECTION_NAME}" ]]; then
  SERVICES=(cloudsql-proxy "${SERVICES[@]}")
else
  SERVICES=(postgres "${SERVICES[@]}")
fi
"${COMPOSE[@]}" up -d --remove-orphans "${SERVICES[@]}"

if [[ -n "${CLOUD_SQL_CONNECTION_NAME}" ]]; then
  log "Recreating backend and Cloud SQL proxy together for shared networking..."
  "${COMPOSE[@]}" up -d --no-deps --force-recreate backend cloudsql-proxy
  "${COMPOSE[@]}" stop postgres >/dev/null 2>&1 || true
else
  "${COMPOSE[@]}" stop cloudsql-proxy >/dev/null 2>&1 || true
fi

log "Current service status:"
"${COMPOSE[@]}" ps

if [[ -n "${CLOUD_SQL_CONNECTION_NAME}" ]]; then
  log "Waiting for Cloud SQL proxy connectivity..."
else
  log "Waiting for Postgres health check..."
fi
if ! wait_for_database_health; then
  if [[ -n "${CLOUD_SQL_CONNECTION_NAME}" ]]; then
    log "Recent cloudsql-proxy logs:"
    "${COMPOSE[@]}" logs --tail=80 cloudsql-proxy || true
    fail "Cloud SQL proxy did not become ready after deployment."
  fi
  log "Recent postgres logs:"
  "${COMPOSE[@]}" logs --tail=80 postgres || true
  fail "Postgres did not become ready after deployment."
fi

log "Waiting for isolated signer socket..."
if ! wait_for_signer_health; then
  log "Recent signer logs:"
  "${COMPOSE[@]}" logs --tail=80 signer || true
  fail "Signer socket did not become ready after deployment."
fi

if ! run_database_migrations; then
  log "Recent backend logs:"
  "${COMPOSE[@]}" logs --tail=80 backend || true
  fail "Database migrations failed after deployment."
fi

log "Waiting for backend health check..."
if ! wait_for_backend_health; then
  log "Recent backend logs:"
  "${COMPOSE[@]}" logs --tail=80 backend || true
  fail "Backend health check did not succeed after deployment."
fi

if [[ "${TAIL_LOGS}" == true ]]; then
  log "Tailing signer/backend/frontend logs. Press Ctrl+C to stop."
  "${COMPOSE[@]}" logs -f signer backend frontend
fi
