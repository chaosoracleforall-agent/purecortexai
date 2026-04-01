# Mainnet Launch Checklist — TGE 2026-03-31

**Last updated:** 2026-03-30
**Branch:** `mainnet-launch-final` (commit `750f44b`)
**Status:** Code ready. Operational tasks pending.

---

## Completed Today (2026-03-30)

- [x] Code Review Gate 7 — all checklist items reviewed and signed off
- [x] Treasury CEI ordering fix (`execute_burn`, `withdraw_buyback_algo`)
- [x] Hardcoded testnet API URLs replaced with network-aware config (marketplace would have broken on mainnet)
- [x] Hardcoded testnet explorer URLs replaced with `EXPLORER_BASE_URL`
- [x] 20+ user-facing "testnet" labels removed across frontend
- [x] WalletButton `handleDisconnect` error handling added
- [x] Rate limiter fails closed on mainnet when Redis unavailable
- [x] Airdrop registration (`POST /api/airdrop/register`) made public
- [x] npm vulnerabilities fixed (picomatch, brace-expansion) — 0 remaining
- [x] pip audit clean — 0 vulnerabilities
- [x] `.gitignore` updated (tar.gz, .gcloud-tmp, test-results, .npm-cache)
- [x] CI fixed — pytest installed, Redis service added
- [x] All tests green: 51 contracts + 56 backend + 8 E2E = 115 passing
- [x] CI green on GitHub Actions

---

## Pending — Must Complete Before TGE

### 1. Recompile Treasury TEAL Artifacts

The CEI ordering fix changed `sovereign_treasury/contract.py`. The on-chain TEAL must be recompiled.

```bash
cd contracts
poetry run python -m smart_contracts build
```

Verify the new `artifacts/sovereign_treasury/*.teal` files differ from the previous version, then commit.

**Risk if skipped:** Deployed contract bytecode won't match audited source code.

---

### 2. Fund Disposable Trader Wallet

A funded Algorand wallet is needed for the live testnet smoke test.

- Create or designate a disposable wallet
- Fund with testnet ALGO (via dispenser or transfer)
- Export the mnemonic securely

---

### 3. Provision DEPLOYER_MNEMONIC

The deployer mnemonic is required for contract operations and the smoke test.

Options (pick one):
- Environment variable: `export PURECORTEX_DEPLOYER_MNEMONIC="..."`
- File: write to a file with `chmod 600`, path in `PURECORTEX_DEPLOYER_MNEMONIC_FILE`
- GCP Secret Manager: `MAINNET_PURECORTEX_DEPLOYER_MNEMONIC`

**Never pass as a CLI argument.**

---

### 4. Run Live Testnet Smoke Test

This is the final gate from the go/no-go packet (R-003).

```bash
cd contracts
PURECORTEX_DEPLOYER_MNEMONIC="..." PYTHONPATH=. poetry run pytest tests/live_testnet_verify.py::smoke -v
```

Validates end-to-end contract behavior before mainnet switch.

---

### 5. Populate Wallet Addresses in deployment.mainnet.json

All allocation wallet addresses are currently empty. These must be filled:

| Field | Path in JSON | Purpose |
|-------|-------------|---------|
| `allocation.creator.wallet` | Line 59 | Creator vesting recipient |
| `allocation.genesisDistribution.wallet` | Line 64 | Airdrop distribution source |
| `allocation.futureEmissions.wallet` | Line 75 | Emissions schedule source |
| `allocation.liquidity.wallet` | Line 81 | DEX liquidity pool source |
| `allocation.agentIncentives.wallet` | Line 86 | Agent reward pool |
| `allocation.assistanceFund.wallet` | Line 91 | Buyback-and-burn fund |
| `wallets.assistanceFund` | Line 105 | Treasury burn target |
| `wallets.operations` | Line 106 | 10% revenue ops wallet |
| `wallets.creatorVesting` | Line 107 | Vesting contract address |
| `wallets.liquidityPool` | Line 108 | LP token holder |

After populating, regenerate the frontend config:

```bash
PURECORTEX_NETWORK=mainnet python generate_protocol_config.py
```

---

### 6. Enable Trading and Launch

Currently disabled in `deployment.mainnet.json` (lines 95-97):

```json
"tradingEnabled": false,
"launchEnabled": false,
"maintenanceReason": "Pre-launch: mainnet contracts pending deployment"
```

Set both to `true` and clear `maintenanceReason` when ready. Then regenerate config.

---

### 7. Seed DEX Liquidity Pools

Both Tinyman and Pact pool IDs are `null` in `deployment.mainnet.json`.

```bash
cd scripts
PURECORTEX_DEPLOYER_MNEMONIC="..." python setup_liquidity.py --confirm
```

Note: automated pool creation is a TODO (line 176-183 in the script). Manual pool creation via DEX UIs may be required. Split is 60% Tinyman / 40% Pact.

After pools are created, update `dex.tinyman.poolId` and `dex.pact.poolId` in the manifest.

---

### 8. Take Airdrop Snapshot

These fields in `deployment.mainnet.json` are currently `null`:
- `airdrop.snapshotBlock`
- `airdrop.merkleRoot`
- `airdrop.distributionContract`

```bash
python scripts/airdrop_snapshot.py --block <BLOCK_NUMBER> --output snapshot.json
```

Update the manifest with the resulting merkle root and snapshot block.

---

### 9. Stage Secrets on VM

Copy to the mainnet VM (`gcloud compute ssh chaos-sovereign-host --zone=us-central1-a`):

**`.env` file** (from `.env.example`):
- `PURECORTEX_NETWORK=mainnet`
- `CLAUDE_API_KEY`, `GEMINI_API_KEY`, `OPENAI_API_KEY`
- Twitter/X API credentials
- `PURECORTEX_BOOTSTRAP_TOKEN`, `PURECORTEX_SIGNER_SHARED_TOKEN`
- `PURECORTEX_ADMIN_SECRET`, Google OAuth client ID/secret
- `PURECORTEX_TGE_DATE=2026-03-31T00:00:00-05:00`
- `POSTGRES_PASSWORD`
- reCAPTCHA site key + secret

**`.signer-secrets/` directory** (mode 700):
- GPG public + secret keys for all 5 identities (agent, senator, curator, social, vm)
- Encrypted mnemonics for each identity

---

### 10. Obtain TLS Certificate on VM

```bash
sudo certbot certonly --standalone -d purecortex.ai -d www.purecortex.ai
```

Certificates are mounted by nginx via `nginx.mainnet.conf`.

---

### 11. Deploy to VM

```bash
# From workstation:
bash scripts/deploy_remote_vm.sh --pull

# Or on the VM directly:
bash scripts/deploy_vm.sh --pull --tail-logs
```

This builds Docker images, applies Alembic migrations, and restarts the stack.

---

## Post-Launch Monitoring

- [ ] Verify health endpoint: `curl https://purecortex.ai/health`
- [ ] Verify marketplace loads agents from mainnet indexer
- [ ] Verify airdrop registration works without API key
- [ ] Verify governance page shows mainnet contract explorer links
- [ ] Verify wallet connect/disconnect works with Pera Wallet
- [ ] Monitor Grafana / Cloud Run logs for errors
- [ ] Confirm social campaign posts are going out (if enabled)

---

## Known Warnings (Non-Blocking)

| Item | Severity | Notes |
|------|----------|-------|
| Assert message duplicates across contracts | Low | Same strings like "Unauthorized" in multiple methods — debuggable by context |
| Governance quorum based on fixed constant | Low | Will need updating as staked supply grows |
| CreatorVesting not funded on-chain at init | Low | Tokens must be transferred separately after `initialize` |
| GitHub Dependabot: 17 vulns on default branch | Low | Our branch is clean; default branch needs separate fix |
| External security audit not engaged | High | Recommended post-launch; internal audit completed |
