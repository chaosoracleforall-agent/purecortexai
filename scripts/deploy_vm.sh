#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_vm.sh [--pull] [--skip-build] [--tail-logs]

Supported PURECORTEX deployment flow for the GCP VM.

Options:
  --pull        Update the checked out branch with git pull --ff-only before deploy.
  --skip-build  Reuse existing images and skip docker compose build.
  --tail-logs   Follow backend and frontend logs after deployment succeeds.
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
"${COMPOSE[@]}" up -d --remove-orphans

log "Current service status:"
"${COMPOSE[@]}" ps

log "Waiting for backend health check..."
if ! wait_for_backend_health; then
  log "Recent backend logs:"
  "${COMPOSE[@]}" logs --tail=80 backend || true
  fail "Backend health check did not succeed after deployment."
fi

if [[ "${TAIL_LOGS}" == true ]]; then
  log "Tailing backend/frontend logs. Press Ctrl+C to stop."
  "${COMPOSE[@]}" logs -f backend frontend
fi
