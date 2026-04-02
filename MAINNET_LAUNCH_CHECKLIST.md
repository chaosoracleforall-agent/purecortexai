# Mainnet Launch Checklist — TGE 2026-03-31

**Last updated:** 2026-04-02
**Branch:** `mainnet-launch-final` (commit `4cce1ae`)
**Status:** LAUNCHED. MainNet live since March 31, 2026. Post-launch hardening complete.

---

## Completed — Pre-TGE (2026-03-30)

- [x] Code Review Gate 7 — all checklist items reviewed and signed off
- [x] Treasury CEI ordering fix (`execute_burn`, `withdraw_buyback_algo`)
- [x] Hardcoded testnet API URLs replaced with network-aware config
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

## Completed — TGE Day (2026-03-31)

- [x] All 6 smart contracts deployed to Algorand MainNet
- [x] CORTEX ASA created (Asset ID: 3501164627)
- [x] Protocol bootstrapped via `AgentFactory.bootstrap_protocol()`
- [x] Wallet addresses populated in `deployment.mainnet.json`
- [x] Trading and launch enabled (`tradingEnabled: true`, `launchEnabled: true`)
- [x] AirdropClaim contract deployed (App ID: 3502246857)
- [x] Airdrop snapshot taken (951 wallets, Merkle root generated)
- [x] DEX liquidity seeded — Tinyman 60% (900B CORTEX + 6,600 ALGO), Pact 40% (600B CORTEX + 4,400 ALGO)
- [x] Frontend switched to `NetworkId.MAINNET`
- [x] Protocol configs regenerated (`protocol_config.py`, `protocolConfig.ts`)

---

## Completed — Post-TGE Hardening (2026-04-01 to 2026-04-02)

### Security (v0.9.1 + v0.9.2)
- [x] 9 security audit findings remediated (SEV-001 through BE-003)
- [x] Orchestrator input sanitization: centralized `_sanitize_user_input()` with 8KB cap, control chars, quote escaping, injection detection
- [x] Bonding curve overflow safety documented in contract docstrings
- [x] Nginx CSP updated with mainnet Nodely endpoints

### Infrastructure (v0.9.3)
- [x] Mainnet VM (`purecortex-mainnet`) deployed and operational — all 7 containers healthy
- [x] Frontend Docker healthcheck fixed (IPv6 → IPv4)
- [x] Docker Compose env var warnings silenced
- [x] VM domain cutover: `PURECORTEX_PUBLIC_DOMAIN=purecortex.ai`
- [x] TLS cert paths updated to `purecortex.ai`
- [x] `liquidityPool` added to signer allowed identities
- [x] Bootstrap token passthrough added to Docker Compose

### Operations (v0.9.3)
- [x] All 6 TEAL artifacts recompiled (puyapy 5.7.1 on VM)
- [x] GCP IAM verified — 4 least-privilege roles on `purecortex-mainnet-vm`
- [x] 2-of-3 treasury multisig created (`PBOHX6V6PEV4BBPJVZ77BUS2LHQ2YRT4T7WRFQRZFHZI3ZEADXVMZGSFZE`)
- [x] Multisig mnemonics stored in GCP Secret Manager
- [x] reCAPTCHA Enterprise enabled on GCP, key configured on VM
- [x] Admin API key bootstrapped on mainnet backend
- [x] Governance Proposal 0 submitted ("Ratify the Constitution")
- [x] X bio corrected: "Dual-Brain" → "Tri-Brain"
- [x] Social agent operational — launch thread posted (6 tweets), catch-up logic working

### Airdrop Snapshot (v0.9.2)
- [x] Governor detection fixed (replaced `GOVERRR` prefix with governance app IDs)
- [x] Developer detection fixed (`on-completion` string/int handling)
- [x] Database tier warnings improved
- [x] Snapshot re-run: 951 wallets eligible (442 DeFi + 502 NFD + 6 Pioneers)
- [x] Launch campaign extended to Day +7 with catch-up logic

---

## Post-Launch Monitoring — Verified

- [x] `/health` returns `200` with mainnet network
- [x] CORTEX ASA visible on Algo Explorer
- [x] Tinyman pool shows liquidity
- [x] Pact pool shows liquidity
- [x] Marketplace trading enabled
- [x] Governance page shows proposals (2 proposals, 1 voting)
- [x] Social agent posting to X (@purecortexai, 508 posts)
- [x] Backend health: `{"status":"ok","version":"0.7.7","dependencies":{"redis":"connected","orchestrator":"initialized","agent_loop":"running"}}`

---

## Remaining — Post-Launch Roadmap

### External Security (P1)
- [ ] Engage external audit firm (Halborn or Runtime Verification) — drafts in `docs/OUTREACH.md`
- [ ] Publish Immunefi bug bounty program — spec at `docs/IMMUNEFI_BOUNTY_SPEC.md`
- [ ] Complete penetration testing checklist (12 smart contract + 7 backend + 5 infra tests)

### Airdrop Tiers (P1)
- [ ] Governor tier: Nodely indexer times out on broad `search_transactions` — use paginated queries or dedicated governance data source
- [ ] Developer tier: Same indexer timeout — paginate or use smaller round ranges
- [ ] Social campaign + community tasks: Populate via database registrations (claims open April 21)

### Partnerships (P2)
- [ ] Algorand Foundation ecosystem listing — draft in `docs/OUTREACH.md`
- [ ] Tinyman/Pact token verification
- [ ] Vestige.fi analytics listing
- [ ] NFD co-promotion for airdrop tier
- [ ] ASA Stats / Algoscan explorer metadata

### Protocol (P2)
- [ ] Phase 2 governance: veCORTEX-weighted voting (replaces flash-vote-vulnerable CORTEX voting)
- [ ] On-chain Constitution ratification (Proposal 0 in voting)
- [ ] Weekly Senator protocol health reports (agent running, first cycle awaiting)
- [ ] GitHub repo public release (on hold)

---

## Known Warnings (Non-Blocking)

| Item | Severity | Notes |
|------|----------|-------|
| Assert message duplicates across contracts | Low | Same strings in multiple methods — debuggable by context |
| Governance quorum based on fixed constant | Low | Will need updating as staked supply grows |
| CreatorVesting not funded on-chain at init | Low | Tokens must be transferred separately |
| GitHub Dependabot: 17 vulns on default branch | Low | Our branch is clean; default branch needs separate fix |
| Governor/developer airdrop tiers empty | Medium | Indexer query timeouts; affects 30% of airdrop allocation |
| CSP `unsafe-inline` for scripts | Low | Required for Next.js; mainnet nginx uses `script-src-elem` |
