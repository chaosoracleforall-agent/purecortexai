# PURECORTEX: Master Development Context

**Project vision:** Sovereign AI agent launchpad and operating surface on Algorand.
**Current status:** LIVE on Algorand MainNet since March 31, 2026 (v0.9.3).
**Repository:** `https://github.com/chaosoracleforall-agent/purecortexai`
**App:** `https://purecortex.ai`
**Social:** `https://x.com/purecortexai`
**Last updated:** April 2, 2026

---

## 1. Current Snapshot

PURECORTEX is a fully deployed sovereign AI agent platform on Algorand MainNet:

- **6 smart contracts** deployed and active (AgentFactory, Governance, VeCortexStaking, SovereignTreasury, CreatorVesting, AirdropClaim)
- **$CORTEX token** live (ASA 3501164627, 10 quadrillion supply, 6 decimals)
- **DEX liquidity** seeded on Tinyman V2 (60%) and Pact (40%) — 1.5T CORTEX + 11,000 ALGO
- **2-of-3 treasury multisig** for operations fund
- **3 autonomous AI agents** running: Senator, Curator, Social (@purecortexai)
- **Tri-brain consensus**: Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5
- **Governance active**: Proposal 0 (Ratify Constitution) submitted
- **Airdrop**: 951 wallets eligible, claims open April 21

## 2. Canonical MainNet Identifiers

| Contract | App ID |
|----------|--------|
| AgentFactory | `3501164435` |
| Governance | `3501164276` |
| VeCortexStaking | `3501164346` |
| SovereignTreasury | `3501164386` |
| CreatorVesting | `3501164479` |
| AirdropClaim | `3502246857` |
| CORTEX ASA | `3501164627` |

These values come from `deployment.mainnet.json` and generated protocol config modules.

## 3. Architecture

### 3.1. Intelligence Layer
- **Claude model:** `claude-opus-4-6` (primary)
- **Gemini model:** `gemini-2.5-pro` (secondary)
- **OpenAI model:** `gpt-5` with `gpt-4.1` fallback
- **High-risk consensus:** 2-of-3 majority, fail-closed
- **Input sanitization:** 8KB cap, control char stripping, injection detection

### 3.2. API/Auth Layer
- Public transparency/governance reads: unauthenticated
- Protected REST endpoints: `X-API-Key` with HMAC verification
- WebSocket chat: `POST /api/chat/session` → short-lived tokens
- Admin: oauth2-proxy Google SSO → `x-purecortex-auth-email` header
- Developer access: reCAPTCHA Enterprise protected
- Auth fails closed on Redis outage

### 3.3. Infrastructure Layer
- **Production VM:** `purecortex-mainnet` (GCP e2-standard-4, us-central1-a)
- **Testnet VM:** `purecortex-master` (same zone, fully isolated)
- **Runtime:** Docker Compose (7 containers: backend, signer, frontend, redis, nginx, cloudsql-proxy, oauth2-proxy)
- **Signer:** Isolated container (no network, read-only FS, Unix socket only)
- **TLS:** Let's Encrypt at Nginx, HSTS + TLS 1.2+
- **Database:** Cloud SQL PostgreSQL (`purecortex_mainnet`)
- **GCP project:** `purecortexai`

## 4. Post-Launch Status (April 2, 2026)

### Completed
- All 6 contracts deployed and operational
- Enterprise security audit: no CRITICAL findings, LOW risk rating
- All security gate checklists verified (crypto, infra, app, contracts)
- TEAL artifacts recompiled (puyapy 5.7.1)
- GCP IAM: 4 least-privilege roles verified
- Social agent: 508 posts, launch thread delivered, catch-up logic active
- Governance: Proposal 0 submitted, admin API key bootstrapped
- reCAPTCHA Enterprise: enabled and configured

### Remaining Priorities
1. External audit firm engagement (Halborn/Runtime Verification) — drafts ready in `docs/OUTREACH.md`
2. Immunefi bug bounty publication — spec at `docs/IMMUNEFI_BOUNTY_SPEC.md`
3. Airdrop tier gap: governor/developer tiers need paginated indexer queries
4. Phase 2 governance: veCORTEX-weighted voting
5. Partnership outreach (Algorand Foundation, Tinyman, Pact, Vestige, NFD)
6. GitHub repo public release (on hold)

---
*PURECORTEX: Sovereign intelligence infrastructure on Algorand MainNet.*
