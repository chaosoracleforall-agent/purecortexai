# PURECORTEX: Technical Roadmap & Architecture

This roadmap reflects the stack deployed on Algorand MainNet as of April 2, 2026 (v0.9.3).

## 1. Current Production Architecture

### Infrastructure
- **GCP project:** `purecortexai`
- **Production VM:** `purecortex-mainnet` (e2-standard-4, us-central1-a)
- **Testnet VM:** `purecortex-master` (same zone, fully isolated)
- **Runtime:** Docker Compose (7 containers) + Nginx + Cloud SQL
- **Public domain:** `https://purecortex.ai`
- **Stateful dependencies:** Redis (auth, cache, agent memory), PostgreSQL via Cloud SQL (governance, developer access, airdrop registrations)

### Application Stack
- **Frontend:** Next.js 16 (Turbopack)
- **Backend:** FastAPI (Python 3.12)
- **Contracts:** 6 Puya/algopy smart contracts on Algorand MainNet
- **Token:** $CORTEX (ASA 3501164627, 10 quadrillion supply, 6 decimals)
- **DEX:** Tinyman V2 + Pact (1.5T CORTEX + 11,000 ALGO)

### Tri-Brain Consensus
- **Claude:** Opus 4.6 (primary)
- **Gemini:** 2.5 Pro (secondary)
- **OpenAI:** GPT-5 with GPT-4.1 fallback
- **High-risk policy:** 2-of-3 majority, fail-closed
- **Input sanitization:** 8KB cap, control char stripping, prompt injection detection

### Security Posture
- **Signer:** Isolated container (no network, read-only FS, Unix socket)
- **Auth:** API key HMAC + oauth2-proxy SSO + reCAPTCHA Enterprise
- **Treasury:** 2-of-3 multisig for operations fund
- **TLS:** HSTS + TLS 1.2+ with OCSP stapling
- **Docker:** `no-new-privileges`, `cap_drop: ALL`, resource limits

## 2. What Has Been Hardened (v0.7.0 → v0.9.3)

- 6 smart contracts deployed to MainNet with overflow-safe bonding curve math
- Enterprise security audit: no CRITICAL findings, LOW risk rating
- All 19 admin methods verified for sender authorization
- CEI pattern compliance across all contracts
- Centralized LLM input sanitization with injection detection
- Fail-closed API auth on Redis outage
- Governance write-through to PostgreSQL (survives Redis restart)
- Airdrop Merkle-proof claims with SHA-256 integrity verification
- Social agent with 12 campaign targets and tri-brain content generation
- 127+ tests (51 contracts + 56 backend + 8 E2E + 12 campaign)

## 3. Roadmap

### Phase A: External Security (April 2026)
1. Engage external audit firm (Halborn or Runtime Verification) — drafts ready.
2. Publish Immunefi bug bounty program ($500-$25,000 rewards).
3. Complete penetration testing checklist (24 tests across contracts, backend, infra).

### Phase B: Governance Maturity (April-May 2026)
1. Phase 2 voting: replace CORTEX-transfer voting with veCORTEX-weighted voting to eliminate flash-vote vulnerability.
2. On-chain Constitution ratification (Proposal 0 in voting).
3. Enable Senator Agent weekly protocol health reports.
4. Open governance proposal creation to community (currently admin-only).

### Phase C: Airdrop & Community Growth (April-July 2026)
1. Fix governor/developer airdrop tiers (paginated indexer queries).
2. Open airdrop claims (April 21).
3. Algorand Foundation ecosystem listing + grant application.
4. Partnership integrations: Vestige analytics, NFD co-promotion, ASA Stats metadata.
5. Community task completion tracking for airdrop tier.

### Phase D: Product Expansion (Q2-Q3 2026)
1. Agent SDK: Python + TypeScript packages for building on PURECORTEX.
2. MCP server: remote transport for AI tool marketplace.
3. Agent graduation: bonding curve → DEX migration flow.
4. Cross-chain agent operations via Algorand state proofs.
5. Advanced marketplace: agent discovery, reputation scoring, revenue analytics.

### Phase E: Infrastructure Evolution (Q3 2026)
1. Evaluate managed Kubernetes vs current VM model for scaling.
2. Multi-region deployment for latency reduction.
3. Advanced monitoring: Grafana dashboards, alerting for unusual on-chain activity.
4. KMS-backed signing as alternative to GPG-based signer daemon.

---
*PURECORTEX: Sovereign intelligence infrastructure on Algorand MainNet.*
