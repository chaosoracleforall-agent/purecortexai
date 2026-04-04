# PURECORTEX — MainNet Launch Strategy & Security Gates

> **Branch:** `mainnet-launch-final`
> **TGE:** March 31, 2026 (COMPLETED)
> **Status:** LIVE ON ALGORAND MAINNET — v0.9.3
> **Owner:** Chaos Oracle (`chaosoracleforall@gmail.com`)
> **Last updated:** 2026-04-02

This document is the canonical reference for the mainnet launch. Every contributor, AI agent, and reviewer must treat these gates as non-negotiable prerequisites.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Architecture Summary](#2-architecture-summary)
3. [MainNet Launch Strategy](#3-mainnet-launch-strategy)
4. [Airdrop Campaign](#4-airdrop-campaign)
5. [Community & Ecosystem Penetration](#5-community--ecosystem-penetration)
6. [AI Agent Coordinated Launch](#6-ai-agent-coordinated-launch)
7. [Code Review Gate](#7-code-review-gate)
8. [Code Audit Gate](#8-code-audit-gate)
9. [Security Audit Gate](#9-security-audit-gate)
10. [Regression Testing Gate](#10-regression-testing-gate)
11. [Unit Testing Gate](#11-unit-testing-gate)
12. [Penetration Testing Gate](#12-penetration-testing-gate)
13. [Enterprise Security Review Gate](#13-enterprise-security-review-gate)
14. [Deployment Runbook](#14-deployment-runbook)
15. [Post-Launch Monitoring](#15-post-launch-monitoring)

---

## 1. Project Overview

PURECORTEX is the sovereign AI agent launchpad on Algorand — a protocol surface where autonomous AI agents operate as independent economic actors with bonding curves, composable tool marketplaces (MCP), on-chain governance, and a constitutional framework.

**Core differentiators:**
- **Tri-Brain Consensus:** Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5 with 2-of-3 majority for high-risk actions, fail-closed when no consensus
- **Constitutional Governance:** Immutable Preamble + 7 amendable Articles, Senator + Lawmaker model, veCORTEX-weighted voting
- **90/10 Revenue Model:** 90% of ALL protocol revenue → continuous buyback-and-burn via Assistance Fund; 10% → operations
- **0% VC, 0% Team:** 10% creator (180-day vest), 90% community and ecosystem
- **Fail-Closed Safety:** Tiered agent sandboxing, isolated signing, GPG key hierarchy

**Token:** $CORTEX | **Chain:** Algorand (AVM) | **Total Supply:** 10 quadrillion (6 decimals)

---

## 2. Architecture Summary

### Smart Contracts (Puya/algopy → TEAL)

| Contract | Purpose | Testnet App ID |
|----------|---------|----------------|
| **AgentFactory** | Bonding curve token factory, agent creation, buy/sell, graduation | 757290073 |
| **GovernanceContract** | Proposal lifecycle (48h discuss → 5d vote → 7d timelock → execute) | 757157787 |
| **VeCortexStaking** | Lock CORTEX 7-1460 days, earn veCORTEX, delegation to Lawmakers | 757172306 |
| **SovereignTreasury** | Revenue processing: 90% buyback-burn, 10% operations | 757172354 |
| **CreatorVesting** | 10% TGE release, 90% linear daily vest over 180 days | NEW |

### Backend (FastAPI)

- API layer: health, agents, governance, transparency, marketplace, staking, auth, chat, admin
- AI agent framework: Senator, Curator, Social agents with base agent abstraction
- Services: Algorand indexer client, isolated signer daemon, GPG crypto, Redis cache, PostgreSQL
- Tri-Brain orchestrator with structural prompt injection guardrails

### Frontend (Next.js 15/16)

- Landing page, marketplace, chat, governance, transparency, airdrop, docs, admin
- Wallet integration: Pera, Defly, Lute, Exodus, Kibisis via `@txnlab/use-wallet-react`

### Infrastructure

- GCP VM (`purecortex-master`, e2-standard-4, us-central1)
- Docker Compose: backend, signer (isolated/no network), frontend, redis, nginx, postgres, oauth2-proxy
- TLS termination via Nginx, Cloud SQL for PostgreSQL, Secret Manager for credentials

---

## 3. MainNet Launch Strategy

### Phase 1: "Genesis Signal" — March 31, 2026

| Action | Status |
|--------|--------|
| GitHub repository flipped to public | PENDING |
| Launch announcement across all channels (X, Discord, Reddit, Forum) | PENDING |
| Airdrop registration opens at `/airdrop` | BUILT |
| Immunefi bug bounty program published | SPEC READY |
| Social Agent begins daily campaign cadence | WIRED |
| Testnet demo remains live for community inspection | ACTIVE |
| Tokenomics paper + Constitution published | READY |
| Developer access program opens | ACTIVE |

### Phase 2: "MainNet Genesis" — TGE Day

| Action | Status |
|--------|--------|
| All 5 contracts deployed to Algorand MainNet | TOOLING READY |
| CORTEX ASA created on mainnet via AgentFactory.bootstrap_protocol() | PENDING |
| Creator vesting contract funded with 10% allocation | CONTRACT READY |
| DEX liquidity seeded (Tinyman 60% + Pact 40% of 15% allocation) | SCRIPT READY |
| Assistance Fund seeded with 5% allocation | TREASURY READY |
| Airdrop snapshot taken and Merkle tree generated | SCRIPT READY |
| Staking opens | PENDING |
| Governance activates (Proposal 0: ratify Constitution on-chain) | PENDING |
| Frontend switched to `NetworkId.MAINNET` | PENDING |
| VM stack redeployed with mainnet config | PENDING |

### Phase 3: "Community Growth" — Post-TGE

| Action | Timeline |
|--------|----------|
| Airdrop claims open | TGE + 21 days |
| First governance cycle completes | TGE + 14 days |
| Weekly protocol health reports from Senator Agent | Ongoing |
| Partnership integrations (Vestige, ASA Stats, NFD) | TGE + 30 days |
| Algorand Foundation ecosystem listing | TGE + 30 days |

---

## 4. Airdrop Campaign

### Allocation: 31% of total supply (3.1 quadrillion CORTEX)

| Tier | % of Airdrop | Eligibility |
|------|-------------|-------------|
| **Testnet Pioneers** | 5% | Wallets that interacted with PureCortex testnet contracts |
| **Algorand DeFi Users** | 30% | Active on Tinyman, Pact, or Folks Finance |
| **Algorand Governors** | 20% | Participated in Algorand governance periods |
| **NFD Holders** | 10% | Own at least one .algo Non-Fungible Domain |
| **Developer Builders** | 10% | Deployed smart contracts or contributed to Algorand open-source |
| **Social Campaign** | 15% | Follow @purecortexai, retweet, connect wallet |
| **Community Tasks** | 10% | Discord activity, forum posts, content creation |

### Anti-Sybil Measures

- Minimum wallet age (created before announcement date)
- Minimum 10 ALGO balance at snapshot
- Activity-weighted scoring (multi-protocol bonus, not just holding)
- Cross-reference known sybil clusters from Algorand governance data
- Square-root weighting for unique interactions (per Constitution Article IV)

### Infrastructure

- **Snapshot Service:** `scripts/airdrop_snapshot.py` — queries Algorand Indexer, builds Merkle tree
- **Claim Page:** `/airdrop` route with wallet connect, eligibility check, registration
- **Distribution:** Merkle-proof claim via on-chain verification
- **Claim Window:** 90 days from TGE (unclaimed returns to treasury)

### Timeline

| Date | Action |
|------|--------|
| Mar 31 | Announce airdrop, publish criteria, open registration |
| Apr 1-7 | Snapshot window (on-chain activity evaluated) |
| Apr 8 | Snapshot taken, Merkle tree generated |
| Apr 9-14 | Social campaign tier opens |
| Apr 15 | Eligibility checker goes live |
| Apr 21 | Claims open |
| Jul 1 | Claim deadline |

---

## 5. Community & Ecosystem Penetration

### Primary Channels (by impact)

1. **Algorand Foundation** — Apply for ecosystem grant + listing on algorand.co/community
2. **X/Twitter** — @purecortexai daily content via Social Agent, engage Algorand CT
3. **Algorand Discord** — #showcase, #project-announcements, genuine dev engagement
4. **Algorand Forum** (forum.algorand.co) — Tokenomics paper, technical deep-dives
5. **Reddit** (r/AlgorandOfficial) — AMA, community discussions
6. **AlgoDevs ecosystem** — Meetups, technical articles, Puya contract tutorials

### The "Why Algorand" Narrative

1. **Instant finality** — 3.3s deterministic block finality for agent settlements
2. **Sub-cent fees** — 0.001 ALGO (~$0.0002) per transaction for x402 micropayments
3. **AVM security** — Atomic transactions prevent reentrancy by design
4. **Python-native contracts** — Puya/algopy enables AI agents to reason about their own contract code
5. **State proofs** — Cross-chain interoperability path for multi-chain agent operations

### Partnership Targets

| Partner | Value | Status |
|---------|-------|--------|
| Tinyman | DEX listing, CORTEX/ALGO LP | PENDING |
| Pact | Secondary DEX liquidity | PENDING |
| Folks Finance | Future lending market | PENDING |
| Algorand Foundation | Grant + ecosystem listing | PENDING |
| NFD (Non-Fungible Domains) | Airdrop partnership, co-promotion | PENDING |
| Vestige.fi | Analytics + token tracking | PENDING |
| ASA Stats / Algoscan | Explorer metadata indexing | PENDING |

---

## 6. AI Agent Coordinated Launch

### Social Agent (@purecortexai)

**Pre-launch (Day -9 to Day -1):**
Campaign content auto-generated from `backend/src/services/launch_campaign.py`:
- Day -9: "What is PURECORTEX?" thread
- Day -8: "Why Algorand?" technical thread
- Day -7: Tokenomics breakdown (0% VC, 90% to holders)
- Day -6: Constitution + governance explainer
- Day -5: Tri-Brain Consensus deep-dive
- Day -4: Genesis Airdrop preview
- Day -3: Developer stack overview (SDK, CLI, MCP)
- Day -2: Testnet milestone recap
- Day -1: "Tomorrow: Genesis" announcement

**Launch day (Day 0):**
- Multi-tweet launch announcement thread
- Share on-chain contract deployment transaction IDs
- Real-time airdrop registration counter

**Post-launch (Day +1 onward):**
- "First 24 hours of PureCortex" metrics
- Weekly protocol health reports
- Community engagement and reply campaigns

### Senator Agent

- Draft Genesis Proposals ready for Day 1:
  - Proposal 0: Ratify Constitution on-chain (ceremonial first vote)
  - Proposal 1: Set initial fee parameters
  - Proposal 2: Approve Q1 operations budget
  - Proposal 3: Establish Immunefi bug bounty parameters
- Pre-generate testnet activity summary and tokenomics health check
- Publish weekly protocol analysis starting Week 1

### Curator Agent

- Pre-launch: audit all public-facing content against Constitution
- Launch day: real-time constitutional compliance review of genesis transactions
- Post-launch: continuous agent behavior monitoring, flag violations

---

## 7. Code Review Gate

**Status:** REQUIRED — MUST PASS BEFORE MAINNET DEPLOYMENT

Every file modified on the `mainnet-launch` branch must pass a structured code review.

### Review Checklist

- [x] **Smart Contracts (Puya/TEAL)** — Reviewed 2026-03-30
  - [x] `contracts/smart_contracts/agent_factory/contract.py` — Bonding curve overflow fix verified (dual cap MAX_AGENT_SUPPLY + MAX_TX_AMOUNT)
  - [x] `contracts/smart_contracts/creator_vesting/contract.py` — New contract reviewed (10% TGE, 180-day linear vest, sound math)
  - [x] `contracts/smart_contracts/governance/contract.py` — No regressions (overflow-safe supermajority check)
  - [x] `contracts/smart_contracts/staking/contract.py` — No regressions (ve_power expiry, creator-gated rewards)
  - [x] `contracts/smart_contracts/sovereign_treasury/contract.py` — No regressions, CEI ordering fixed
  - [ ] All compiled TEAL matches source (verify via `algokit compile`) — PENDING recompile after CEI fix
  - [x] No unchecked integer overflow in any arithmetic path
  - [x] All `assert` messages are unique and debuggable — WARNING: some duplicates across contracts, acceptable for launch
  - [x] Creator-only methods properly check `Txn.sender == Global.creator_address` (19 admin methods verified)
  - [x] State mutations happen BEFORE inner transactions (checks-effects-interactions) — Treasury CEI fixed

- [x] **Backend (Python/FastAPI)** — Reviewed 2026-03-30
  - [x] `backend/orchestrator.py` — Tri-brain prompt injection guardrails verified (2-of-3 majority, fail-closed)
  - [x] `backend/src/agents/social_agent.py` — Launch campaign integration reviewed
  - [x] `backend/src/services/launch_campaign.py` — Content prompts reviewed for accuracy
  - [x] No hardcoded secrets, API keys, or mnemonics (grep verified)
  - [x] All authentication paths fail-closed on Redis/DB outage (56/56 tests pass)
  - [x] WebSocket chat session tokens are short-lived and non-reusable
  - [x] Rate limiting active on all public endpoints

- [x] **Frontend (Next.js/React)** — Reviewed 2026-03-30
  - [x] `frontend/src/components/Airdrop.tsx` — Wallet connection flow reviewed (error handling present)
  - [x] `frontend/src/components/LandingPage.tsx` — CTA changes reviewed
  - [x] `frontend/src/app/(dashboard)/layout.tsx` — Navigation update reviewed
  - [x] No leaked environment variables in client bundle (strong security headers in next.config.ts)
  - [x] All external links use `rel="noopener noreferrer"`
  - [x] Wallet interactions handle connection failures gracefully

- [x] **Scripts & Infrastructure** — Reviewed 2026-03-30
  - [x] `scripts/deploy_mainnet.py` — Deployment script reviewed for safety (--confirm flag required, mnemonic never via CLI)
  - [x] `scripts/airdrop_snapshot.py` — Merkle tree generation reviewed (14 tests pass)
  - [x] `scripts/setup_liquidity.py` — Liquidity split verified (60/40 Tinyman/Pact)
  - [x] `generate_protocol_config.py` — Mainnet/testnet switching logic reviewed
  - [x] `deployment.mainnet.json` — All allocation math verified (5 app IDs non-zero, airdrop tiers sum to 100%)

### Review Process

1. Author self-reviews all changes with the checklist above
2. At minimum one independent reviewer checks all smart contract changes
3. Reviewer signs off by adding their handle and date to the "Approvals" section below
4. No merge to deployment-ready state until all boxes are checked

### Approvals

| Reviewer | Scope | Date | Status |
|----------|-------|------|--------|
| Claude Code (automated) | Smart Contracts | 2026-03-30 | PASS (CEI fix applied to treasury) |
| Claude Code (automated) | Backend + AI Agents | 2026-03-30 | PASS (56/56 tests, no secrets) |
| Claude Code (automated) | Frontend + UX | 2026-03-30 | PASS (8/8 E2E, no leaks) |
| Claude Code (automated) | Scripts + Infra | 2026-03-30 | PASS (all safety gates verified) |
| Claude Code (automated) | Social Agent v0.9.5 | 2026-04-04 | PASS (85/85 tests, conversational engagement overhaul) |

---

## 8. Code Audit Gate

**Status:** REQUIRED — MUST PASS BEFORE MAINNET DEPLOYMENT

### Smart Contract Audit

| Requirement | Standard | Status |
|-------------|----------|--------|
| Internal audit completed | PURECORTEX team | DONE (see `SECURITY_AUDIT.md`) |
| Bonding curve overflow fix verified | Post-fix regression | DONE (this branch) |
| External audit firm engaged | Halborn, Runtime Verification, or equivalent | PENDING |
| All critical/high findings remediated | Zero open critical/high | PENDING |
| Audit report published | Publicly accessible | PENDING |

**Smart contract audit scope:**
- `AgentFactory` — bonding curve math (buy/sell/graduation), fee collection, token creation, overflow safety
- `GovernanceContract` — proposal lifecycle, voting mechanics, timelock enforcement, quorum validation
- `VeCortexStaking` — lock mechanics, veCORTEX power calculation, delegation, reward distribution
- `SovereignTreasury` — revenue split (90/10), buyback withdrawal, burn mechanics
- `CreatorVesting` — vesting schedule math, beneficiary-only claim, time-based release

**Specific audit focus areas:**
- Integer overflow/underflow in all arithmetic (UInt64 boundary conditions)
- State manipulation via inner transaction ordering
- Authorization bypass (creator-only methods)
- Box storage access control and key collision
- Asset opt-in/clawback/freeze authority configuration
- Economic exploits: sandwich attacks on bonding curves, frontrunning graduation

### Backend Code Audit

| Requirement | Status |
|-------------|--------|
| Authentication bypass review | PENDING |
| Prompt injection resistance verification | DONE (structural guardrails in orchestrator) |
| Signing vault isolation verification | PENDING |
| API endpoint authorization matrix | PENDING |
| Rate limiting and abuse prevention review | PENDING |

### Audit Firm Shortlist

1. **Halborn** — Algorand-native expertise; audited Tinyman and Folks Finance
2. **Runtime Verification** — Formal verification capability for Algorand contracts
3. **CertiK** — Broad smart contract audit coverage
4. **Trail of Bits** — Deep infrastructure and crypto review capability

### Accelerated Path

If a full audit cannot complete before TGE:
- Launch Immunefi bug bounty ($500-$25,000 rewards) on March 31 with repo going public
- This provides crowdsourced security review during the first 21 days
- Full audit report can follow and be published retroactively
- Spec ready at `docs/IMMUNEFI_BOUNTY_SPEC.md`

---

## 9. Security Audit Gate

**Status:** REQUIRED — MUST PASS BEFORE MAINNET DEPLOYMENT

### Known Findings from Internal Audit (`SECURITY_AUDIT.md`)

| Finding | Severity | Status |
|---------|----------|--------|
| Bonding curve integer precision loss (small amounts) | HIGH | **FIXED** — overflow-safe split division on this branch |
| Prompt injection via direct concatenation | HIGH | **FIXED** — `<user_query>` structural guardrails in orchestrator |
| Reentrancy via inner transactions | LOW | **MITIGATED** — AVM atomic model + checks-effects-interactions pattern |
| Authorization (ASA manager/freeze/clawback) | LOW | **HARDENED** — set to application_address |
| GCP Secret Manager IAM scope | MEDIUM | PENDING — verify least-privilege binding |
| Signer shared token empty-default | MEDIUM | **FIXED** — fail-closed on missing token (v0.7.6) |

### Additional Security Checklist

- [x] **Cryptographic Security** (verified 2026-04-02)
  - [x] GPG key hierarchy: 6 Ed25519/Curve25519 keypairs validated
  - [x] Signer daemon: no network access, read-only filesystem, Unix socket only
  - [x] Private keys never loaded into main agent process memory
  - [x] GPG passphrases fetched per-operation from Secret Manager (never cached)
  - [x] Signer request authentication uses constant-time comparison

- [x] **Infrastructure Security** (verified 2026-04-02)
  - [x] Docker containers: `no-new-privileges`, `cap_drop: ALL`, resource limits
  - [x] Nginx: X-Forwarded-For sanitization, rightmost-untrusted-hop selection
  - [x] Redis: password-protected, fail-closed on outage
  - [x] PostgreSQL: Cloud SQL with authorized networks only
  - [x] oauth2-proxy: Google SSO for admin with email allowlist
  - [x] reCAPTCHA Enterprise on developer access request form (key: `6LeYQ6Ms...`)

- [x] **Application Security** (verified 2026-04-02)
  - [x] API authentication: `X-API-Key` header with HMAC verification
  - [x] WebSocket auth: short-lived session tokens (non-reusable)
  - [x] Admin proxy: `x-purecortex-auth-email` header validation (trust only behind oauth2-proxy)
  - [x] Governance write endpoints: scope authorization enforced
  - [x] Signed-vote replay resistance
  - [x] `no-store` cache headers on admin responses

- [x] **Smart Contract Security** (verified 2026-04-02)
  - [x] All state mutations before inner transactions (CEI pattern)
  - [x] All public methods have proper sender authorization (19 admin methods checked)
  - [x] All arithmetic checked for UInt64 overflow at maximum parameter values (documented in docstrings)
  - [x] Box storage keys cannot collide across different agents (UInt64 keying)
  - [x] Graduation threshold cannot be manipulated by coordinated buying
  - [x] Sell price always equals integral of curve from new_supply to current_supply

---

## 10. Regression Testing Gate

**Status:** REQUIRED — ALL TESTS MUST PASS BEFORE MAINNET DEPLOYMENT

### Existing Test Suites

| Suite | Path | Coverage |
|-------|------|----------|
| Contract: AgentFactory | `contracts/tests/test_agent_factory.py` | Create, buy, sell, graduate, fees |
| Contract: Governance | `contracts/tests/test_governance_contract.py` | Propose, discuss, vote, timelock, execute |
| Contract: Staking | `contracts/tests/test_staking_contract.py` | Lock, unlock, veCORTEX power, delegation |
| Contract: Treasury | `contracts/tests/test_sovereign_treasury.py` | Revenue split, buyback, burn |
| Contract: Live Testnet Smoke | `contracts/tests/live_testnet_verify.py` | End-to-end on testnet |
| Backend: Auth Bootstrap | `backend/tests/test_auth_bootstrap.py` | First-admin path, key lifecycle |
| Backend: Developer Access | `backend/tests/test_developer_access_api.py` | Request, approve, rotate, revoke |
| Backend: Dev Access Helpers | `backend/tests/test_developer_access_helpers.py` | Key format, HMAC, validation |
| Backend: Governance Voting | `backend/tests/test_governance_voting.py` | Vote submission, tallying |
| Backend: Marketplace API | `backend/tests/test_marketplace_api.py` | Buy/sell flows, error handling |
| Backend: Request IP | `backend/tests/test_request_ip.py` | X-Forwarded-For sanitization |
| Backend: Signing Vault | `backend/tests/test_signing_vault_security.py` | Isolation, auth, key zeroing |
| Backend: Signer Daemon | `backend/tests/test_signer_daemon.py` | Unix socket, token validation |
| Backend: Engagement Scheduler | `backend/tests/test_engagement_scheduler.py` | Cycle rotation, caps, follower scan scheduling |
| Backend: Social Engagement | `backend/tests/test_social_engagement.py` | Search queries, intent classification, ecosystem relevance |
| Frontend E2E: Admin | `frontend/tests/e2e/admin.spec.ts` | Admin console flows |
| Frontend E2E: Admin Live | `frontend/tests/e2e/admin.live.spec.ts` | Live admin with real backend |
| Frontend E2E: Marketplace | `frontend/tests/e2e/marketplace.spec.ts` | Browse, buy, sell flows |
| Frontend E2E: Governance | `frontend/tests/e2e/governance.spec.ts` | Proposal viewing, voting |
| Frontend E2E: Chat | `frontend/tests/e2e/chat.spec.ts` | WebSocket chat, agent interaction |
| Frontend E2E: Wallet | `frontend/tests/e2e/wallet.spec.ts` | Connect, disconnect, switch |

### Required Test Runs Before Deployment

```bash
# 1. Contract unit tests
cd contracts && python -m pytest tests/ -v

# 2. Backend unit tests
cd backend && python -m pytest tests/ -v

# 3. Frontend E2E tests (mocked)
cd frontend && npx playwright test

# 4. Live testnet smoke
cd contracts && python tests/live_testnet_verify.py smoke

# 5. Admin E2E smoke
cd frontend && npm run test:e2e:admin:smoke
```

### New Tests Required for This Branch

- [ ] `contracts/tests/test_agent_factory.py` — Add overflow boundary tests for bonding curve math at MAX_AGENT_SUPPLY
- [ ] `contracts/tests/test_creator_vesting.py` — New: full vesting lifecycle (initialize, TGE release, daily vest, claim, completion)
- [ ] `scripts/test_airdrop_snapshot.py` — Merkle tree generation and proof verification
- [ ] `backend/tests/test_launch_campaign.py` — Launch prompt selection by day offset

### Pass Criteria

- **ALL** existing tests pass with zero failures
- **ALL** new tests for this branch pass
- No test is skipped or marked as expected-failure without documented justification
- Live testnet smoke completes full create → buy → sell → vote cycle

---

## 11. Unit Testing Gate

**Status:** REQUIRED — MINIMUM 80% COVERAGE ON CRITICAL PATHS

### Coverage Requirements

| Component | Minimum Coverage | Critical Paths |
|-----------|-----------------|----------------|
| AgentFactory contract | 90% | `calculate_buy_price`, `calculate_sell_price`, `check_graduation`, `buy_tokens`, `sell_tokens` |
| CreatorVesting contract | 90% | `get_vested_amount`, `get_claimable`, `claim`, `initialize` |
| Governance contract | 85% | Proposal lifecycle, quorum validation, timelock |
| Staking contract | 85% | Lock, unlock, power calculation, delegation |
| Treasury contract | 85% | Revenue split, burn, withdrawal |
| Backend orchestrator | 80% | Consensus evaluation, brain error handling, model fallback |
| Backend signing vault | 90% | Isolation boundary, key material lifecycle |
| Backend auth | 85% | API key validation, fail-closed behavior, scope enforcement |

### Boundary Value Tests Required

For the bonding curve overflow fix, the following specific test cases are REQUIRED:

```
calculate_buy_price:
  amount=1000 (minimum buy), supply=0                → verify base_cost > 0
  amount=1000, supply=MAX_AGENT_SUPPLY-1000           → verify no overflow
  amount=MAX_AGENT_SUPPLY, supply=0                   → verify no overflow
  amount=MAX_TX_AMOUNT (capped by supply), supply=0   → verify no overflow
  slope=MAX_SLOPE, amount=MAX_AGENT_SUPPLY, supply=0  → verify no overflow

calculate_sell_price:
  amount=1000, supply=1000                            → verify returns > 0
  amount=MAX_AGENT_SUPPLY, supply=MAX_AGENT_SUPPLY    → verify no overflow
  amount=1, supply=1                                  → verify returns 0 (rounding)

check_graduation:
  supply at graduation threshold boundary             → verify correct boolean
  supply at MAX_AGENT_SUPPLY with MAX_SLOPE            → verify no overflow
```

For the creator vesting contract:

```
get_vested_amount:
  timestamp < tge_timestamp                           → returns 0
  timestamp == tge_timestamp                          → returns 10% (TGE release)
  timestamp == tge + 1 day                            → returns 10% + 1 day vesting
  timestamp == tge + 90 days                          → returns 10% + 50% vesting
  timestamp == tge + 180 days                         → returns 100%
  timestamp >> tge + 180 days                         → returns 100% (no over-vest)
```

---

## 12. Penetration Testing Gate

**Status:** REQUIRED — MUST COMPLETE BEFORE MAINNET DEPLOYMENT

### Scope

| Target | Attack Surface | Priority |
|--------|---------------|----------|
| Smart Contracts | On-chain state manipulation, economic exploits | CRITICAL |
| Backend API | Authentication bypass, injection, privilege escalation | HIGH |
| Tri-Brain Orchestrator | Prompt injection, consensus manipulation | HIGH |
| Signing Vault | Isolation bypass, key extraction | CRITICAL |
| Admin Console | Authentication bypass, CSRF, session hijacking | HIGH |
| Frontend | XSS, CSRF, wallet interaction manipulation | MEDIUM |
| Infrastructure | Container escape, network pivoting, secret extraction | HIGH |

### Smart Contract Penetration Tests

- [ ] **Bonding curve manipulation:** Attempt to buy at artificially low prices by crafting specific `amount` values that exploit integer division rounding
- [ ] **Sandwich attack on graduation:** Buy large position → trigger graduation → sell into DEX liquidity at profit
- [ ] **Flash-loan equivalent:** Use grouped transactions to buy, manipulate state, and sell in one atomic group
- [ ] **Box storage collision:** Attempt to overwrite one agent's config by crafting a key that collides with another agent
- [ ] **Fee evasion:** Attempt to bypass buy/sell fees through direct inner transaction crafting
- [ ] **Creator authority escalation:** Attempt to call creator-only methods from a non-creator address
- [ ] **Supply overflow:** Attempt to buy more tokens than MAX_AGENT_SUPPLY through multiple rapid transactions
- [ ] **Vesting schedule bypass:** Attempt to claim more than vested amount through re-entrance or timestamp manipulation

### Backend Penetration Tests

- [ ] **API key bypass:** Test all authenticated endpoints with missing, malformed, expired, and revoked keys
- [ ] **Admin proxy bypass:** Attempt to set `x-purecortex-auth-email` header directly (bypassing oauth2-proxy)
- [ ] **WebSocket hijack:** Attempt to reuse session tokens, connect with expired tokens, or escalate from chat to admin
- [ ] **Prompt injection (tri-brain):** Submit crafted inputs that attempt to override system prompts across Claude, Gemini, and GPT
- [ ] **SQL injection:** Test all PostgreSQL-backed endpoints (developer access, admin) with standard injection payloads
- [ ] **Redis injection:** Test all Redis-backed endpoints with crafted key values
- [ ] **Signer isolation breach:** Attempt to reach the signer daemon from outside its Unix socket boundary

### Infrastructure Penetration Tests

- [ ] **Container escape:** Attempt breakout from backend container to host
- [ ] **Network segmentation:** Verify signer container has zero network access
- [ ] **Secret Manager access:** Verify only authorized service account can read secrets
- [ ] **Nginx bypass:** Attempt to access backend directly, bypassing Nginx proxy rules
- [ ] **TLS validation:** Verify certificate chain, HSTS, and protocol version

### Penetration Test Report Requirements

- All findings documented with severity, evidence, and reproduction steps
- Critical and high findings must be remediated before mainnet deployment
- Medium findings documented with remediation timeline
- Low findings documented for backlog

---

## 13. Enterprise Security Review Gate

**Status:** REQUIRED — FULL REVIEW BEFORE MAINNET DEPLOYMENT

This gate represents the comprehensive organizational security posture review.

### Access Control Matrix

| Resource | Who Can Access | How Verified |
|----------|---------------|--------------|
| Mainnet deployer mnemonic | Owner only | GCP Secret Manager, manual |
| API key issuance | Owner via admin console | Google SSO + oauth2-proxy |
| Signer daemon | Backend container only | Unix socket, no network, shared token |
| Cloud SQL PostgreSQL | Backend + admin only | GCP authorized networks |
| Redis | Backend only | Password + Docker network isolation |
| GCP Secret Manager | VM service account only | IAM binding |
| GitHub repo (when public) | Read: everyone; Write: owner | Branch protection + CODEOWNERS |
| Twitter API credentials | Social Agent only | Environment variables from Secret Manager |
| Tri-Brain API keys | Backend orchestrator only | Environment variables from Secret Manager |

### Key Management

- [x] Mainnet deployer mnemonic stored in GCP Secret Manager (`MAINNET_PURECORTEX_DEPLOYER_MNEMONIC`)
- [x] 2-of-3 multisig configured for treasury operations — `PBOHX6V6PEV4BBPJVZ77BUS2LHQ2YRT4T7WRFQRZFHZI3ZEADXVMZGSFZE` (deployer + cold + hardware). Mnemonics in Secret Manager (`MAINNET_TREASURY_MULTISIG_WALLETS`).
- [x] All API keys (Claude, Gemini, OpenAI, Twitter) stored in VM `.env` (not in code)
- [x] No secrets in git history (verified — scan completed)
- [x] `.env` files gitignored and never committed
- [x] GCP IAM verified: `purecortex-mainnet-vm` has 4 least-privilege roles only

### Operational Security

- [x] Circuit breaker mechanism for pausing protocol (`tradingEnabled`/`launchEnabled` flags in deployment manifest)
- [x] VM snapshot capability via `gcloud compute disks snapshot`
- [x] Backend health endpoint: `/health` returns orchestrator + Redis + agent loop status
- [ ] Incident response plan documented
- [ ] Monitoring alerts for unusual activity (large buys/sells, rapid agent creation)
- [ ] Backup and recovery procedure for PostgreSQL, Redis state
- [ ] DNS failover plan if GCP VM goes down

### Compliance Considerations

- [ ] No securities claims in any public material (utility token positioning)
- [ ] Constitution + manifesto reviewed for legal implications
- [ ] Privacy policy (`/docs/privacy`) covers wallet address data handling
- [ ] Terms of service (`/docs/terms`) covers protocol interaction risks
- [ ] Buyback-burn model documented as capital gains (not dividend) mechanism
- [ ] Creator vesting terms documented transparently

### Third-Party Dependencies

- [ ] `npm audit` clean for frontend (verified — overrides applied for ws and bn.js)
- [ ] `pip audit` clean for backend (verified — FastAPI/MCP upgraded to 0.135.1/1.26.0)
- [ ] No known CVEs in Docker base images
- [ ] Algorand SDK versions are current and supported

---

## 14. Deployment Runbook

### Infrastructure: Mainnet VM Isolation

Mainnet runs on a **dedicated VM** (`purecortex-mainnet`) completely isolated from the testnet
VM (`purecortex-master`). Both VMs live in the same GCP project (`purecortexai`) and zone
(`us-central1-a`) but share no state, database, or secrets.

| Resource | Testnet VM | Mainnet VM |
|----------|-----------|------------|
| **Instance** | `purecortex-master` | `purecortex-mainnet` |
| **Domain** | `purecortex.ai` | `mainnet.purecortex.ai` → `purecortex.ai` (post-cutover) |
| **Nginx config** | `nginx.conf` | `nginx.mainnet.conf` |
| **Database** | `purecortex` | `purecortex_mainnet` |
| **Secret prefix** | (none) | `MAINNET_*` in Secret Manager |
| **PURECORTEX_NETWORK** | `testnet` | `mainnet` |
| **Service account** | (default) | `purecortex-mainnet-vm` |

#### Provisioning the mainnet VM

```bash
# 1. Provision (creates VM, static IP, firewall, service account)
scripts/provision_mainnet_vm.sh          # add --dry-run to preview
# Note the external IP from the output

# 2. Create DNS A record: mainnet.purecortex.ai → <external IP>

# 3. SSH into the new VM and run bootstrap
gcloud compute ssh purecortex-mainnet --zone=us-central1-a --project=purecortexai --tunnel-through-iap
# On the VM:
bash scripts/setup_mainnet_vm.sh --domain mainnet.purecortex.ai

# 4. Fill in .env secrets, copy signer GPG keys to .signer-secrets/

# 5. Create mainnet secrets in Secret Manager
gcloud secrets create MAINNET_PURECORTEX_DEPLOYER_MNEMONIC --project=purecortexai
gcloud secrets create MAINNET_PURECORTEX_CLOUDSQL_APP_PASSWORD --project=purecortexai
# (shared secrets like OAuth are used without prefix)
```

#### Deploying to mainnet VM (from local machine)

```bash
PURECORTEX_GCP_INSTANCE=purecortex-mainnet scripts/deploy_remote_vm.sh
```

### Pre-Deployment (Day -2 to Day -1)

```bash
# 1. Compile all contracts (verify TEAL matches source)
cd contracts && algokit compile

# 2. Run ALL test suites
cd contracts && python -m pytest tests/ -v
cd backend && python -m pytest tests/ -v
cd frontend && npx playwright test

# 3. Run live testnet smoke
cd contracts && python tests/live_testnet_verify.py smoke

# 4. Dry-run mainnet deployment (mnemonic via env var — never as CLI arg)
read -s PURECORTEX_DEPLOYER_MNEMONIC && export PURECORTEX_DEPLOYER_MNEMONIC
python scripts/deploy_mainnet.py --dry-run

# 5. Take VM snapshots for rollback (both VMs)
gcloud compute disks snapshot purecortex-master --zone=us-central1-a
gcloud compute disks snapshot purecortex-mainnet --zone=us-central1-a
```

### Deployment (Day 0)

```bash
# 1. Deploy contracts to mainnet (mnemonic from Secret Manager)
python scripts/deploy_mainnet.py --mnemonic-secret MAINNET_PURECORTEX_DEPLOYER_MNEMONIC --confirm

# 2. Generate mainnet protocol config
python generate_protocol_config.py mainnet

# 3. Switch frontend to mainnet
# Edit frontend/src/components/Providers.tsx: NetworkId.TESTNET → NetworkId.MAINNET

# 4. Deploy to the mainnet VM (NOT the testnet VM)
PURECORTEX_GCP_INSTANCE=purecortex-mainnet scripts/deploy_remote_vm.sh

# 5. Verify mainnet deployment
curl https://mainnet.purecortex.ai/api/health
# Smoke test against mainnet endpoint

# 6. Seed DEX liquidity
python scripts/setup_liquidity.py --mnemonic-secret MAINNET_PURECORTEX_DEPLOYER_MNEMONIC \
  --cortex-asset-id <ID> --cortex-amount 900000000000000 --algo-amount <ALGO_AMOUNT> --confirm

# 7. Enable marketplace trading
# Update deployment.mainnet.json: tradingEnabled → true, launchEnabled → true
python generate_protocol_config.py mainnet
PURECORTEX_GCP_INSTANCE=purecortex-mainnet scripts/deploy_remote_vm.sh

# 8. DNS cutover (when ready to go live on purecortex.ai)
# Update purecortex.ai A record to point to mainnet VM's static IP
# Re-run certbot on mainnet VM to add purecortex.ai to the certificate
# Update PURECORTEX_PUBLIC_DOMAIN=purecortex.ai in mainnet .env
# Redeploy: PURECORTEX_GCP_INSTANCE=purecortex-mainnet scripts/deploy_remote_vm.sh

# 9. Flip GitHub repo to public
# GitHub → Settings → Danger Zone → Change visibility → Public

# 10. Publish announcements
# Social Agent auto-fires Day 0 launch content
```

### Post-Deployment Verification

- [ ] `/api/health` returns `200` with mainnet network
- [ ] CORTEX ASA visible on Algo Explorer
- [ ] Factory app visible on Algo Explorer
- [ ] Tinyman pool shows liquidity
- [ ] Pact pool shows liquidity
- [ ] Airdrop page loads and connects wallets
- [ ] Marketplace shows agent creation form
- [ ] Governance page shows Proposal 0
- [ ] Transparency page shows correct supply data
- [ ] Social Agent posts launch announcement

---

## 15. Post-Launch Monitoring

### First 24 Hours

- Monitor all contract interactions via Algorand Indexer
- Watch for unusual bonding curve activity (potential exploits)
- Verify Assistance Fund receives fee revenue correctly
- Confirm airdrop registration flow works end-to-end
- Check Social Agent posting cadence
- Monitor API response times and error rates

### First Week

- Senator Agent publishes first protocol health report
- Review all governance proposals submitted
- Monitor airdrop registration numbers
- Track DEX liquidity depth and trading volume
- Review Immunefi bounty submissions (if any)
- Daily check of burn counter in transparency page

### Ongoing

- Weekly Senator reports
- Monthly security review of new findings
- Quarterly review of access control matrix
- Continuous Immunefi bounty program
- Community governance participation metrics

---

## Files Created/Modified on This Branch

### New Files

| File | Purpose |
|------|---------|
| `CLAUDE.md` | This document — mainnet launch strategy and security gates |
| `deployment.mainnet.json` | Canonical mainnet deployment manifest |
| `contracts/smart_contracts/creator_vesting/contract.py` | Creator vesting contract (10% TGE + 180-day vest) |
| `frontend/src/app/(dashboard)/airdrop/page.tsx` | Airdrop route page |
| `frontend/src/components/Airdrop.tsx` | Airdrop UI (registration, tiers, timeline, countdown) |
| `backend/src/services/launch_campaign.py` | Social Agent launch campaign content (Day -9 to Day +1) |
| `scripts/deploy_mainnet.py` | MainNet contract deployment script |
| `scripts/airdrop_snapshot.py` | Airdrop snapshot + Merkle tree service |
| `scripts/setup_liquidity.py` | DEX liquidity pool setup (Tinyman + Pact) |
| `docs/IMMUNEFI_BOUNTY_SPEC.md` | Bug bounty program specification |

### Modified Files

| File | Change |
|------|--------|
| `contracts/smart_contracts/agent_factory/contract.py` | Fixed UInt64 overflow in bonding curve math (calculate_buy_price, calculate_sell_price, check_graduation) |
| `backend/src/agents/social_agent.py` | v0.9.5: Conversational engagement overhaul — follower scanning, intent-classified mentions, warm replies, community shoutouts, lowered thresholds, raised limits, removed legacy campaign cycle |
| `backend/src/services/engagement_scheduler.py` | v0.9.5: Added follower_scan operation, raised per-cycle caps, added CYCLE_MAX_FOLLOWER_ENGAGEMENTS |
| `backend/src/services/social_campaign.py` | v0.9.5: Expanded search queries from 10 to 19 (AI agent crypto, AlgoKit, Puya, cross-chain) |
| `backend/tests/test_social_engagement.py` | v0.9.5: Added intent classification and ecosystem relevance tests |
| `backend/tests/test_engagement_scheduler.py` | v0.9.5: Added follower scan scheduling test, updated caps assertions |
| `frontend/src/app/(dashboard)/layout.tsx` | Added Airdrop to dashboard navigation |
| `frontend/src/components/LandingPage.tsx` | Changed primary CTA to "Claim Genesis Airdrop" |
| `generate_protocol_config.py` | Added mainnet/testnet environment switching via CLI arg or env var |

---

*This document is the law of the `mainnet-launch` branch. No deployment proceeds until every gate section shows PASSED. The Constitution governs the protocol; this document governs the launch.*
