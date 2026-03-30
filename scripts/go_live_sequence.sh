#!/usr/bin/env bash
set -euo pipefail

# PURECORTEX go-live sequence helper.
# Executes the day-0 operational checks and prints required manual gates.
#
# Usage:
#   scripts/go_live_sequence.sh --dry-run
#   scripts/go_live_sequence.sh --execute

MODE="dry-run"
if [[ "${1:-}" == "--execute" ]]; then
  MODE="execute"
fi

PROJECT="${PURECORTEX_GCP_PROJECT:-purecortexai}"
ZONE="${PURECORTEX_GCP_ZONE:-us-central1-a}"
MAINNET_INSTANCE="${PURECORTEX_GCP_INSTANCE:-purecortex-mainnet}"
TESTNET_INSTANCE="${PURECORTEX_TESTNET_INSTANCE:-purecortex-master}"
DOMAIN="${PURECORTEX_PUBLIC_DOMAIN:-purecortex.ai}"
MAINNET_DOMAIN="${PURECORTEX_MAINNET_DOMAIN:-mainnet.purecortex.ai}"
HEALTH_URL="https://${MAINNET_DOMAIN}/api/health"

log() { printf '[go-live] %s\n' "$*"; }
run() {
  if [[ "${MODE}" == "dry-run" ]]; then
    log "DRY RUN: $*"
  else
    "$@"
  fi
}

log "Mode: ${MODE}"
log "Project: ${PROJECT} | Zone: ${ZONE}"
log "Mainnet VM: ${MAINNET_INSTANCE} | Testnet VM: ${TESTNET_INSTANCE}"

log "T-4h: VM snapshots"
run gcloud compute disks snapshot "${MAINNET_INSTANCE}" \
  --project="${PROJECT}" \
  --zone="${ZONE}" \
  --snapshot-names="${MAINNET_INSTANCE}-prelaunch-$(date +%Y%m%d%H%M)"

run gcloud compute disks snapshot "${TESTNET_INSTANCE}" \
  --project="${PROJECT}" \
  --zone="${ZONE}" \
  --snapshot-names="${TESTNET_INSTANCE}-prelaunch-$(date +%Y%m%d%H%M)"

log "T-4h: Mainnet health check"
run curl -fsS "${HEALTH_URL}"

log "T-1h: DNS and cert readiness (manual checkpoints)"
log "  - Ensure cert covers ${DOMAIN} and ${MAINNET_DOMAIN}"
log "  - Prepare DNS A record cutover for ${DOMAIN}"

log "T-0: Launch actions (manual checkpoints)"
log "  - Switch ${DOMAIN} A record to mainnet static IP"
log "  - Trigger social day-0 launch thread"
log "  - Confirm /api/health reports mainnet network"
log "  - Verify CORTEX/ALGO pools on Tinyman and Pact"

log "T+1h: Monitoring checks"
log "  - Watch API latency / error rate"
log "  - Confirm airdrop registration requests persist in DB"
log "  - Confirm governance and marketplace contract activity via indexer"

log "Go-live checklist complete."
