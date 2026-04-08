#!/usr/bin/env bash
set -euo pipefail

# Bootstrap a freshly provisioned GCP VM for PureCortex mainnet.
# Run this ON the VM after SSH'ing in. It installs Docker, clones the repo,
# obtains TLS certificates, and prepares the .env for mainnet operation.
#
# Usage (on the VM):
#   bash setup_mainnet_vm.sh [--domain mainnet.purecortex.ai]
#
# The script is idempotent — safe to re-run.

DOMAIN="${PURECORTEX_DOMAIN:-mainnet.purecortex.ai}"
REPO_URL="https://github.com/purecortexai/PureCortex.git"
BRANCH="mainnet-launch"
INSTALL_DIR="${HOME}/PureCortex"
CERTBOT_EMAIL="chaosoracleforall@gmail.com"
PRELAUNCH_MODE=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --domain) DOMAIN="$2"; shift 2 ;;
    --branch) BRANCH="$2"; shift 2 ;;
    --dir)    INSTALL_DIR="$2"; shift 2 ;;
    --prelaunch) PRELAUNCH_MODE=1; DOMAIN="mainnet-prelaunch.purecortex.ai"; shift ;;
    *)        echo "Unknown arg: $1"; exit 1 ;;
  esac
done

log() { printf '[setup] %s\n' "$*"; }

log "Domain: ${DOMAIN}"
log "Branch: ${BRANCH}"
log "Install dir: ${INSTALL_DIR}"
log "Prelaunch mode: ${PRELAUNCH_MODE}"

# --- System packages ---
log "Updating system packages..."
sudo apt-get update -qq
sudo apt-get install -y -qq \
  ca-certificates curl gnupg lsb-release git ufw certbot

# --- Docker ---
if command -v docker >/dev/null 2>&1; then
  log "Docker already installed: $(docker --version)"
else
  log "Installing Docker..."
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
    sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg

  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
    https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
    sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin

  sudo usermod -aG docker "${USER}"
  log "Docker installed. You may need to re-login for group membership."
fi

# --- Firewall (UFW) ---
log "Configuring host firewall..."
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
echo "y" | sudo ufw enable 2>/dev/null || true
sudo ufw status

# --- Clone repo ---
if [[ -d "${INSTALL_DIR}/.git" ]]; then
  log "Repo already cloned at ${INSTALL_DIR}. Fetching latest..."
  cd "${INSTALL_DIR}"
  git fetch --all --prune
  git checkout "${BRANCH}"
  git pull --ff-only || log "Pull failed (dirty tree?). Continuing with current state."
else
  log "Cloning repository..."
  git clone --branch "${BRANCH}" "${REPO_URL}" "${INSTALL_DIR}"
  cd "${INSTALL_DIR}"
fi

# --- TLS certificates via Certbot ---
CERT_DIR="/etc/letsencrypt/live/${DOMAIN}"
if [[ -d "${CERT_DIR}" ]]; then
  log "TLS certificate already exists for ${DOMAIN}."
else
  log "Obtaining TLS certificate for ${DOMAIN}..."
  log "Make sure DNS for ${DOMAIN} points to this VM's external IP before proceeding."
  read -rp "Press Enter to continue with certbot, or Ctrl+C to abort..."

  sudo certbot certonly --standalone \
    --non-interactive --agree-tos \
    --email "${CERTBOT_EMAIL}" \
    -d "${DOMAIN}"

  log "Certificate obtained. Setting up auto-renewal..."
  sudo systemctl enable certbot.timer
  sudo systemctl start certbot.timer
fi

# --- Prepare .env ---
ENV_FILE="${INSTALL_DIR}/.env"
if [[ -f "${ENV_FILE}" ]]; then
  log ".env already exists. Skipping template copy."
else
  log "Creating .env from .env.example with mainnet defaults..."
  cp "${INSTALL_DIR}/.env.example" "${ENV_FILE}"

  cat >> "${ENV_FILE}" <<EOF

# ==== Mainnet VM overrides (auto-added by setup_mainnet_vm.sh) ====
PURECORTEX_NETWORK=mainnet
PURECORTEX_PUBLIC_DOMAIN=${DOMAIN}
PURECORTEX_PRELAUNCH_MODE=${PRELAUNCH_MODE}
PURECORTEX_NGINX_CONF=$( [[ "${PRELAUNCH_MODE}" == "1" ]] && echo "nginx.prelaunch.conf" || echo "nginx.mainnet.conf" )
PURECORTEX_TGE_DATE=2026-03-31T00:00:00-05:00
SOCIAL_CAMPAIGN_ENABLED=1
SOCIAL_CAMPAIGN_AUTO_FOLLOW=1
SOCIAL_CAMPAIGN_AUTO_REPLY=1
EOF

  if [[ "${PRELAUNCH_MODE}" == "1" ]]; then
    cat >> "${ENV_FILE}" <<'EOF'
PURECORTEX_PRELAUNCH_BASIC_AUTH_USER=
PURECORTEX_PRELAUNCH_BASIC_AUTH_PASSWORD=
EOF
  fi

  log "IMPORTANT: Edit ${ENV_FILE} and fill in all required secrets before deploying."
fi

# --- Create signer secrets directory ---
SIGNER_DIR="${INSTALL_DIR}/.signer-secrets"
if [[ -d "${SIGNER_DIR}" ]]; then
  log "Signer secrets directory exists."
else
  mkdir -p "${SIGNER_DIR}"
  chmod 700 "${SIGNER_DIR}"
  log "Created ${SIGNER_DIR}. Copy GPG-encrypted signer keys here before deploying."
fi

# --- Summary ---
log ""
log "=========================================="
log "  VM setup complete for: ${DOMAIN}"
log "=========================================="
log ""
log "Remaining manual steps:"
log "  1. Fill in ${ENV_FILE} with mainnet secrets (AI keys, Twitter, etc.)"
log "  2. Copy signer GPG keys to ${SIGNER_DIR}/"
log "  3. Create mainnet secrets in GCP Secret Manager (prefixed MAINNET_):"
log "       - MAINNET_PURECORTEX_DEPLOYER_MNEMONIC"
log "       - MAINNET_PURECORTEX_CLOUDSQL_APP_PASSWORD (if using Cloud SQL)"
log "       - Plus shared secrets (OAuth, reCAPTCHA) if not already created"
log "  4. Deploy from your local machine:"
log "       PURECORTEX_GCP_INSTANCE=purecortex-mainnet scripts/deploy_remote_vm.sh"
log "  5. Or deploy directly on the VM:"
log "       cd ${INSTALL_DIR} && bash scripts/deploy_vm.sh"
