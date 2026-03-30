#!/usr/bin/env bash
set -euo pipefail

MARKER_FILE="/root/.purecortex_mainnet_deploy_done"
LOG_FILE="/var/log/purecortex-mainnet-deploy.log"
ARTIFACT_URI="${PURECORTEX_ARTIFACT_URI:-gs://purecortex-mainnet-artifacts/purecortex_mainnet_bundle.tar.gz}"

exec > >(tee -a "${LOG_FILE}") 2>&1

if [[ -f "${MARKER_FILE}" ]]; then
  echo "[deploy] marker exists, skipping repeat deploy"
  exit 0
fi

echo "[deploy] stage begin"
TMP_ARCHIVE="/tmp/purecortex_mainnet_bundle.tar.gz"
ENV_BACKUP="/tmp/purecortex_mainnet_vm.env"
MANIFEST_BACKUP="/tmp/purecortex_mainnet_deployment.mainnet.json"
gcloud storage cp "${ARTIFACT_URI}" "${TMP_ARCHIVE}"
if [[ -f /root/PureCortex/.env ]]; then
  cp /root/PureCortex/.env "${ENV_BACKUP}"
fi
if [[ -f /root/PureCortex/deployment.mainnet.json ]]; then
  cp /root/PureCortex/deployment.mainnet.json "${MANIFEST_BACKUP}"
fi
rm -rf /root/PureCortex
mkdir -p /root/PureCortex
# Suppress macOS extended-attribute warnings from tar extraction.
tar -xzf "${TMP_ARCHIVE}" -C /root/PureCortex 2>/dev/null
if [[ -f "${ENV_BACKUP}" ]]; then
  cp "${ENV_BACKUP}" /root/PureCortex/.env
elif [[ -f /root/PureCortex/contracts/.env && ! -f /root/PureCortex/.env ]]; then
  cp /root/PureCortex/contracts/.env /root/PureCortex/.env
fi
if [[ -f "${MANIFEST_BACKUP}" ]]; then
  cp "${MANIFEST_BACKUP}" /root/PureCortex/deployment.mainnet.json
fi
cd /root/PureCortex

# Hotfix deploy script on VM in case artifact lags behind local patches.
python3 - <<'PY'
from pathlib import Path

p = Path("/root/PureCortex/scripts/deploy_mainnet.py")
txt = p.read_text()

if "import math" not in txt:
    txt = txt.replace("import tempfile\n", "import tempfile\nimport math\n")

if "extra_pages=" not in txt:
    txt = txt.replace(
        "    approval_program = b64decode(approval_result[\"result\"])\n    clear_program = b64decode(clear_result[\"result\"])\n",
        "    approval_program = b64decode(approval_result[\"result\"])\n    clear_program = b64decode(clear_result[\"result\"])\n    extra_pages = max(0, math.ceil(max(0, len(approval_program) - 2048) / 2048))\n",
    )
    txt = txt.replace(
        "        local_schema=StateSchema(num_uints=0, num_byte_slices=0),\n    )\n",
        "        local_schema=StateSchema(num_uints=0, num_byte_slices=0),\n        extra_pages=extra_pages,\n    )\n",
    )

if "sp.fee = 4_000" not in txt:
    txt = txt.replace(
        "    atc = AtomicTransactionComposer()\n",
        "    sp = client.suggested_params()\n"
        "    sp.flat_fee = True\n"
        "    sp.fee = 4_000\n\n"
        "    atc = AtomicTransactionComposer()\n",
    )
    txt = txt.replace(
        "        sp=client.suggested_params(),\n",
        "        sp=sp,\n",
    )

if "Funded factory app account" not in txt:
    txt = txt.replace(
        "    sender = account.address_from_private_key(private_key)\n    signer = AccountTransactionSigner(private_key)\n",
        "    sender = account.address_from_private_key(private_key)\n"
        "    signer = AccountTransactionSigner(private_key)\n"
        "    from algosdk import transaction\n"
        "    from algosdk.logic import get_application_address\n",
    )
    txt = txt.replace(
        "    sp = client.suggested_params()\n    sp.flat_fee = True\n    sp.fee = 4_000\n",
        "    factory_app_address = get_application_address(factory_app_id)\n"
        "    factory_balance = client.account_info(factory_app_address).get(\"amount\", 0)\n"
        "    required_factory_balance = 500_000\n"
        "    if factory_balance < required_factory_balance:\n"
        "        top_up = required_factory_balance - factory_balance\n"
        "        fund_sp = client.suggested_params()\n"
        "        fund_sp.flat_fee = True\n"
        "        fund_sp.fee = 1_000\n"
        "        fund_txn = transaction.PaymentTxn(\n"
        "            sender=sender,\n"
        "            sp=fund_sp,\n"
        "            receiver=factory_app_address,\n"
        "            amt=top_up,\n"
        "        )\n"
        "        fund_tx_id = client.send_transaction(fund_txn.sign(private_key))\n"
        "        transaction.wait_for_confirmation(client, fund_tx_id, 10)\n"
        "        print(f\"    Funded factory app account: {fund_tx_id} (+{top_up} microALGO)\")\n\n"
        "    sp = client.suggested_params()\n"
        "    sp.flat_fee = True\n"
        "    sp.fee = 4_000\n",
    )

p.write_text(txt)
PY

apt-get update -qq
apt-get install -y -qq python3-venv python3-pip

python3 -m venv /root/.pc-deploy-venv
source /root/.pc-deploy-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install py-algorand-sdk python-dotenv

if [[ -f "contracts/.env" ]]; then
  set -a
  source contracts/.env
  set +a
fi

echo "[deploy] running mainnet contract deployment"
if python3 - <<'PY'
import json
from pathlib import Path

p = Path("/root/PureCortex/deployment.mainnet.json")
if not p.exists():
    raise SystemExit(1)
data = json.loads(p.read_text())
contracts = data.get("contracts", {})
required_apps = [
    contracts.get("agentFactory", {}).get("appId", 0),
    contracts.get("governance", {}).get("appId", 0),
    contracts.get("staking", {}).get("appId", 0),
    contracts.get("treasury", {}).get("appId", 0),
    contracts.get("creatorVesting", {}).get("appId", 0),
]
asset_id = contracts.get("cortexToken", {}).get("assetId", 0)
raise SystemExit(0 if all(isinstance(v, int) and v > 0 for v in required_apps) and isinstance(asset_id, int) and asset_id > 0 else 1)
PY
then
  echo "[deploy] detected existing mainnet contract IDs in manifest; skipping redeploy"
else
  python scripts/deploy_mainnet.py --mnemonic-secret MAINNET_PURECORTEX_DEPLOYER_MNEMONIC --confirm
fi

echo "[deploy] generating protocol config for mainnet"
python generate_protocol_config.py mainnet

echo "[deploy] syncing runtime environment"
PURECORTEX_NETWORK=mainnet python scripts/sync_runtime_env.py

# Ensure Redis auth secret exists so redis healthcheck can pass.
python3 - <<'PY'
from pathlib import Path
import secrets

env_path = Path("/root/PureCortex/.env")
lines = env_path.read_text().splitlines()
updated = False
for i, line in enumerate(lines):
    if line.startswith("REDIS_PASSWORD="):
        if line.strip() == "REDIS_PASSWORD=":
            lines[i] = f"REDIS_PASSWORD={secrets.token_urlsafe(24)}"
        updated = True
        break
if not updated:
    lines.append(f"REDIS_PASSWORD={secrets.token_urlsafe(24)}")
env_path.write_text("\n".join(lines) + "\n")
PY

echo "[deploy] starting docker stack"
docker compose --env-file .env up -d --build

touch "${MARKER_FILE}"
echo "[deploy] stage complete"
