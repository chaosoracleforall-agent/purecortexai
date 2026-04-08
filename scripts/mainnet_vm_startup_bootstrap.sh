#!/usr/bin/env bash
set -euo pipefail

DOMAIN="${PURECORTEX_DOMAIN:-mainnet.purecortex.ai}"
HOME="${HOME:-/root}"
INSTALL_DIR="${HOME}/PureCortex"
CERTBOT_EMAIL="chaosoracleforall@gmail.com"
ARTIFACT_URI="${PURECORTEX_ARTIFACT_URI:-gs://purecortex-mainnet-artifacts/purecortex_mainnet_bundle.tar.gz}"
PRELAUNCH_MODE="${PURECORTEX_PRELAUNCH_MODE:-0}"

echo "[startup] bootstrap begin"
sudo apt-get update -qq
sudo apt-get install -y -qq ca-certificates curl gnupg lsb-release git ufw certbot

if ! command -v docker >/dev/null 2>&1; then
  sudo install -m 0755 -d /etc/apt/keyrings
  curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
  sudo chmod a+r /etc/apt/keyrings/docker.gpg
  echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list >/dev/null
  sudo apt-get update -qq
  sudo apt-get install -y -qq docker-ce docker-ce-cli containerd.io docker-compose-plugin
  sudo usermod -aG docker "${USER}" || true
fi

sudo ufw allow OpenSSH || true
sudo ufw allow 80/tcp || true
sudo ufw allow 443/tcp || true
echo "y" | sudo ufw enable 2>/dev/null || true

if [[ ! -d "${INSTALL_DIR}" ]]; then
  TMP_ARCHIVE="/tmp/purecortex_mainnet_bundle.tar.gz"
  gcloud storage cp "${ARTIFACT_URI}" "${TMP_ARCHIVE}"
  tar -xzf "${TMP_ARCHIVE}" -C "${HOME}"
fi
cd "${INSTALL_DIR}"

ENV_FILE="${INSTALL_DIR}/.env"
if [[ ! -f "${ENV_FILE}" ]]; then
  cp "${INSTALL_DIR}/.env.example" "${ENV_FILE}"
fi

if ! rg -q "^PURECORTEX_NETWORK=mainnet$" "${ENV_FILE}"; then
  cat >> "${ENV_FILE}" <<EOF

# ==== Mainnet VM overrides (auto-added by startup bootstrap) ====
PURECORTEX_NETWORK=mainnet
PURECORTEX_PUBLIC_DOMAIN=${DOMAIN}
PURECORTEX_PRELAUNCH_MODE=${PRELAUNCH_MODE}
PURECORTEX_NGINX_CONF=$( [[ "${PRELAUNCH_MODE}" == "1" ]] && echo "nginx.prelaunch.conf" || echo "nginx.mainnet.conf" )
PURECORTEX_TGE_DATE=2026-03-31T00:00:00-05:00
SOCIAL_CAMPAIGN_ENABLED=1
SOCIAL_CAMPAIGN_AUTO_FOLLOW=1
SOCIAL_CAMPAIGN_AUTO_REPLY=1
EOF
fi

mkdir -p "${INSTALL_DIR}/.signer-secrets"
chmod 700 "${INSTALL_DIR}/.signer-secrets"

if [[ ! -d "/etc/letsencrypt/live/${DOMAIN}" ]]; then
  certbot certonly --standalone --non-interactive --agree-tos --email "${CERTBOT_EMAIL}" -d "${DOMAIN}" || true
  sudo systemctl enable certbot.timer || true
  sudo systemctl start certbot.timer || true
fi

echo "[startup] bootstrap complete"
