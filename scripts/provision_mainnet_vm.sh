#!/usr/bin/env bash
set -euo pipefail

# Provisions a dedicated GCP VM for the PureCortex mainnet deployment.
# This VM is fully isolated from the testnet instance (purecortex-master).
#
# Usage:
#   scripts/provision_mainnet_vm.sh [--dry-run]
#
# Prerequisites:
#   - gcloud CLI authenticated as project owner
#   - DNS A record for mainnet.purecortex.ai pointed to the new VM's external IP
#     (created after first run, once the static IP is known)

PROJECT="${PURECORTEX_GCP_PROJECT:-purecortexai}"
ZONE="${PURECORTEX_GCP_ZONE:-us-central1-a}"
REGION="${ZONE%-*}"
INSTANCE="purecortex-mainnet"
MACHINE_TYPE="e2-standard-4"
BOOT_DISK_SIZE="50GB"
BOOT_IMAGE_FAMILY="ubuntu-2404-lts-amd64"
BOOT_IMAGE_PROJECT="ubuntu-os-cloud"
STATIC_IP_NAME="purecortex-mainnet-ip"
FIREWALL_TAG="purecortex-mainnet"
SERVICE_ACCOUNT_NAME="purecortex-mainnet-vm"

DRY_RUN=false
if [[ "${1:-}" == "--dry-run" ]]; then
  DRY_RUN=true
fi

log() { printf '[provision] %s\n' "$*"; }
run() {
  if [[ "${DRY_RUN}" == true ]]; then
    log "DRY RUN: $*"
  else
    "$@"
  fi
}

log "Project: ${PROJECT} | Zone: ${ZONE} | Instance: ${INSTANCE}"

# --- Static external IP ---
if gcloud compute addresses describe "${STATIC_IP_NAME}" \
     --region="${REGION}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "Static IP ${STATIC_IP_NAME} already exists."
else
  log "Reserving static external IP: ${STATIC_IP_NAME}"
  run gcloud compute addresses create "${STATIC_IP_NAME}" \
    --region="${REGION}" \
    --project="${PROJECT}" \
    --network-tier=PREMIUM
fi

EXTERNAL_IP=$(gcloud compute addresses describe "${STATIC_IP_NAME}" \
  --region="${REGION}" --project="${PROJECT}" \
  --format='get(address)' 2>/dev/null || echo "<pending>")
log "External IP: ${EXTERNAL_IP}"

# --- Service account ---
SA_EMAIL="${SERVICE_ACCOUNT_NAME}@${PROJECT}.iam.gserviceaccount.com"
if gcloud iam service-accounts describe "${SA_EMAIL}" \
     --project="${PROJECT}" >/dev/null 2>&1; then
  log "Service account ${SA_EMAIL} already exists."
else
  log "Creating service account: ${SERVICE_ACCOUNT_NAME}"
  run gcloud iam service-accounts create "${SERVICE_ACCOUNT_NAME}" \
    --project="${PROJECT}" \
    --display-name="PureCortex Mainnet VM"
fi

log "Binding Secret Manager accessor role..."
run gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/secretmanager.secretAccessor" \
  --condition=None \
  --quiet 2>/dev/null || true

log "Binding Cloud SQL client role..."
run gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/cloudsql.client" \
  --condition=None \
  --quiet 2>/dev/null || true

log "Binding logging writer role..."
run gcloud projects add-iam-policy-binding "${PROJECT}" \
  --member="serviceAccount:${SA_EMAIL}" \
  --role="roles/logging.logWriter" \
  --condition=None \
  --quiet 2>/dev/null || true

# --- Firewall rules ---
FW_HTTP="${FIREWALL_TAG}-allow-http"
FW_HTTPS="${FIREWALL_TAG}-allow-https"

if gcloud compute firewall-rules describe "${FW_HTTP}" \
     --project="${PROJECT}" >/dev/null 2>&1; then
  log "Firewall rule ${FW_HTTP} already exists."
else
  log "Creating firewall rule: ${FW_HTTP}"
  run gcloud compute firewall-rules create "${FW_HTTP}" \
    --project="${PROJECT}" \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:80 \
    --source-ranges=0.0.0.0/0 \
    --target-tags="${FIREWALL_TAG}"
fi

if gcloud compute firewall-rules describe "${FW_HTTPS}" \
     --project="${PROJECT}" >/dev/null 2>&1; then
  log "Firewall rule ${FW_HTTPS} already exists."
else
  log "Creating firewall rule: ${FW_HTTPS}"
  run gcloud compute firewall-rules create "${FW_HTTPS}" \
    --project="${PROJECT}" \
    --direction=INGRESS \
    --priority=1000 \
    --network=default \
    --action=ALLOW \
    --rules=tcp:443 \
    --source-ranges=0.0.0.0/0 \
    --target-tags="${FIREWALL_TAG}"
fi

# --- Create the VM ---
if gcloud compute instances describe "${INSTANCE}" \
     --zone="${ZONE}" --project="${PROJECT}" >/dev/null 2>&1; then
  log "Instance ${INSTANCE} already exists. Skipping creation."
else
  log "Creating VM instance: ${INSTANCE} (${MACHINE_TYPE})"
  run gcloud compute instances create "${INSTANCE}" \
    --project="${PROJECT}" \
    --zone="${ZONE}" \
    --machine-type="${MACHINE_TYPE}" \
    --image-family="${BOOT_IMAGE_FAMILY}" \
    --image-project="${BOOT_IMAGE_PROJECT}" \
    --boot-disk-size="${BOOT_DISK_SIZE}" \
    --boot-disk-type=pd-ssd \
    --tags="${FIREWALL_TAG}" \
    --address="${STATIC_IP_NAME}" \
    --service-account="${SA_EMAIL}" \
    --scopes=cloud-platform \
    --metadata=enable-oslogin=TRUE \
    --shielded-secure-boot \
    --shielded-vtpm \
    --shielded-integrity-monitoring
fi

log ""
log "=========================================="
log "  VM provisioned: ${INSTANCE}"
log "  External IP:    ${EXTERNAL_IP}"
log "=========================================="
log ""
log "Next steps:"
log "  1. Point DNS: mainnet.purecortex.ai -> ${EXTERNAL_IP}"
log "  2. SSH into the VM:"
log "       gcloud compute ssh ${INSTANCE} --zone=${ZONE} --project=${PROJECT} --tunnel-through-iap"
log "  3. Run the setup script on the VM:"
log "       bash scripts/setup_mainnet_vm.sh"
log "  4. After setup, deploy with:"
log "       PURECORTEX_GCP_INSTANCE=${INSTANCE} scripts/deploy_remote_vm.sh"
