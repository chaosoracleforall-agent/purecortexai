#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy_remote_vm.sh [deploy_vm.sh args...]

Run the supported PURECORTEX deployment flow on the remote GCP VM over
gcloud compute ssh. Any arguments are forwarded to scripts/deploy_vm.sh.

Environment overrides:
  PURECORTEX_GCP_PROJECT   Default: purecortexai
  PURECORTEX_GCP_ZONE      Default: us-central1-a
  PURECORTEX_GCP_INSTANCE  Default: purecortex-master
  PURECORTEX_VM_DIR        Default: /home/davidgarcia/PureCortex
EOF
}

fail() {
  printf '[deploy_remote_vm] ERROR: %s\n' "$*" >&2
  exit 1
}

if [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]]; then
  usage
  exit 0
fi

if ! command -v gcloud >/dev/null 2>&1; then
  fail "Missing required command: gcloud"
fi

PROJECT="${PURECORTEX_GCP_PROJECT:-purecortexai}"
ZONE="${PURECORTEX_GCP_ZONE:-us-central1-a}"
INSTANCE="${PURECORTEX_GCP_INSTANCE:-purecortex-master}"
VM_DIR="${PURECORTEX_VM_DIR:-/home/davidgarcia/PureCortex}"

REMOTE_ARGS=""
for arg in "$@"; do
  REMOTE_ARGS+=" $(printf '%q' "$arg")"
done

REMOTE_COMMAND="cd $(printf '%q' "${VM_DIR}") && bash scripts/deploy_vm.sh${REMOTE_ARGS}"

printf '[deploy_remote_vm] Deploying to %s (%s/%s)\n' "${INSTANCE}" "${PROJECT}" "${ZONE}"

gcloud compute ssh "${INSTANCE}" \
  --zone="${ZONE}" \
  --project="${PROJECT}" \
  --tunnel-through-iap \
  --command="${REMOTE_COMMAND}"
