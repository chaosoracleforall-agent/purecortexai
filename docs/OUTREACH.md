# PURECORTEX Outreach

This document contains draft communications for audit firms, the Algorand Foundation, ecosystem partners, and the Immunefi bug bounty publication process.

All drafts reference the mainnet deployment completed on March 31, 2026.

---

## Table of Contents

1. [Audit Firm Outreach](#1-audit-firm-outreach)
2. [Algorand Foundation Application](#2-algorand-foundation-application)
3. [Partnership Outreach](#3-partnership-outreach)
4. [Immunefi Publication Checklist](#4-immunefi-publication-checklist)

---

## 1. Audit Firm Outreach

### 1a. Halborn

**Subject:** Algorand Smart Contract Audit Request -- PURECORTEX (6 Contracts, Puya/algopy)

Hello Halborn team,

We are writing to request a quote for a smart contract audit of the PURECORTEX protocol, a sovereign AI agent launchpad deployed on Algorand MainNet.

**Scope:** 6 smart contracts written in Python using Algorand's Puya/algopy framework, compiled to TEAL and running on AVM:

| Contract | MainNet App ID | Description |
|----------|---------------|-------------|
| AgentFactory | 3501164435 | Bonding curve token factory -- agent creation, buy/sell, graduation |
| GovernanceContract | 3501164276 | Proposal lifecycle (discuss, vote, timelock, execute) |
| VeCortexStaking | 3501164346 | Time-locked staking with vote-escrowed power and delegation |
| SovereignTreasury | 3501164386 | Revenue processing -- 90% buyback-burn, 10% operations |
| CreatorVesting | 3501164479 | 10% TGE release + 180-day linear daily vesting |
| AirdropClaim | 3502246857 | Merkle-proof airdrop distribution with claim deadline |

**Source language:** Python (Puya/algopy), compiled to TEAL. We can provide both the Python source and compiled TEAL artifacts.

**CORTEX token ASA:** 3501164627 (10 quadrillion supply, 6 decimals)

**Areas of focus:**
- Integer overflow/underflow in all bonding curve arithmetic (UInt64 boundaries)
- State manipulation via inner transaction ordering
- Authorization bypass on creator-only administrative methods (19 admin methods across contracts)
- Box storage access control and key collision vectors
- Economic exploits: sandwich attacks on bonding curves, frontrunning graduation events
- Vesting schedule correctness and timestamp manipulation resistance

**Internal audit status:** We have completed a comprehensive internal security audit. Key findings (bonding curve integer precision, checks-effects-interactions ordering in treasury) have been remediated on the current branch. The full internal audit report is available for your review.

**Timeline:** The protocol is live on MainNet as of March 31, 2026. We have an active Immunefi bug bounty program providing crowdsourced security coverage in the interim, but we want a professional audit completed as soon as possible.

**Budget:** We would appreciate a quote based on the scope above. We are flexible on engagement structure (fixed-price or time-and-materials).

**Repository:** https://github.com/chaosoracleforall-agent/purecortexai (public)

We understand Halborn has deep Algorand-native expertise, having audited Tinyman and Folks Finance, which is why you are our first choice for this engagement.

Please let us know your availability and we can schedule a kickoff call at your convenience.

Best regards,
PureCortex Team
security@purecortex.ai
https://purecortex.ai

---

### 1b. Runtime Verification

**Subject:** Algorand Smart Contract Audit Request -- PURECORTEX (6 Contracts, Formal Verification Interest)

Hello Runtime Verification team,

We are reaching out to request a smart contract audit of the PURECORTEX protocol on Algorand MainNet.

PURECORTEX is a sovereign AI agent launchpad with bonding curves, on-chain governance, vote-escrowed staking, treasury management, creator vesting, and Merkle-proof airdrop distribution.

**Scope:** 6 smart contracts written in Python (Puya/algopy), compiled to TEAL.

| Contract | MainNet App ID |
|----------|---------------|
| AgentFactory | 3501164435 |
| GovernanceContract | 3501164276 |
| VeCortexStaking | 3501164346 |
| SovereignTreasury | 3501164386 |
| CreatorVesting | 3501164479 |
| AirdropClaim | 3502246857 |

We are particularly interested in Runtime Verification's formal verification capabilities. The bonding curve math in AgentFactory involves UInt64 arithmetic at scale (10 quadrillion token supply, 6 decimals), and we would value formal proofs of overflow safety and economic invariant preservation across the buy/sell/graduation lifecycle.

**Current status:**
- Mainnet live since March 31, 2026
- Internal security audit completed with all critical/high findings remediated
- Active Immunefi bug bounty program ($500 - $25,000 rewards)
- Public repository: https://github.com/chaosoracleforall-agent/purecortexai

**Timeline:** ASAP. We would like to begin engagement within the next 2-4 weeks.

We would appreciate a quote and availability estimate. Happy to provide source code access, internal audit report, and schedule a technical walkthrough.

Best regards,
PureCortex Team
security@purecortex.ai
https://purecortex.ai

---

## 2. Algorand Foundation Application

### Ecosystem Grant and Listing Application

**Project Name:** PURECORTEX

**One-line description:** Sovereign AI agent launchpad on Algorand with bonding curves, constitutional governance, and a tri-brain consensus safety model.

**Website:** https://purecortex.ai

**GitHub:** https://github.com/chaosoracleforall-agent/purecortexai

**Team:** Independent builder. Built and deployed by a solo developer. No VC funding, no team allocation. 10% creator vesting (180-day linear vest), 90% community and ecosystem.

**Token:** $CORTEX (ASA 3501164627) -- 10 quadrillion supply, 6 decimals. Live on MainNet since March 31, 2026.

### What PURECORTEX Does

PURECORTEX is a protocol where autonomous AI agents operate as independent economic actors on Algorand. Each agent is launched through a bonding curve token factory, accumulates value through usage fees, and graduates to DEX liquidity when a market cap threshold is reached.

The protocol includes:
- **Agent Factory** with continuous bonding curves for price discovery
- **Constitutional Governance** with a vote-escrowed staking model (veCORTEX)
- **Tri-Brain Consensus** (Claude + Gemini + GPT, 2-of-3 majority for high-risk actions)
- **Sovereign Treasury** with 90% of all revenue going to continuous buyback-and-burn
- **Composable tool marketplace** (MCP-based) for agent capabilities

### Technical Architecture

**Smart Contracts:** 6 contracts written in Python using Puya/algopy, compiled to TEAL:

| Contract | App ID | Purpose |
|----------|--------|---------|
| AgentFactory | 3501164435 | Bonding curve factory, buy/sell, graduation |
| GovernanceContract | 3501164276 | Proposal lifecycle with timelock |
| VeCortexStaking | 3501164346 | Time-locked staking, delegation |
| SovereignTreasury | 3501164386 | 90/10 revenue split, buyback-burn |
| CreatorVesting | 3501164479 | 10% TGE + 180-day vest |
| AirdropClaim | 3502246857 | Merkle-proof distribution |

**Backend:** FastAPI with AI agent framework (Senator, Curator, Social agents), isolated signing vault, Redis cache, PostgreSQL.

**Frontend:** Next.js with Algorand wallet integration (Pera, Defly, Lute, Exodus, Kibisis) via @txnlab/use-wallet-react.

**Infrastructure:** GCP VM with Docker Compose, Nginx TLS termination, Cloud SQL, Secret Manager.

### Why Algorand

1. **Instant finality** -- 3.3s deterministic block finality is essential for agent settlements and bonding curve transactions where price depends on current supply.
2. **Sub-cent fees** -- 0.001 ALGO per transaction enables micropayments for AI agent tool usage (x402 pattern) without fee friction destroying the economics.
3. **AVM security model** -- Atomic transactions prevent reentrancy by design. This is a structural advantage over EVM for a protocol handling bonding curve math with real funds.
4. **Python-native contracts** -- Puya/algopy allows AI agents to reason about their own contract code in a language they understand natively. This is a unique capability for the AI agent thesis.
5. **State proofs** -- Future cross-chain interoperability path for multi-chain agent operations.

### Community Metrics

- **Airdrop registrations:** 950+ wallets across 7 eligibility tiers (Algorand DeFi users, governors, NFD holders, testnet pioneers, developers, social campaign, community tasks)
- **Genesis Distribution:** 31% of total supply allocated to community airdrop
- **DEX liquidity:** Active CORTEX/ALGO pools on Tinyman and Pact
- **Governance:** Active on-chain governance with Proposal 0 (Constitution ratification)
- **Bug bounty:** Immunefi program live with $500 - $25,000 rewards
- **Tokenomics:** 0% VC, 0% team beyond 10% creator vest. 90% of protocol revenue to buyback-burn.

### What We Are Requesting

1. **Ecosystem listing** on algorand.co/community and the Algorand ecosystem directory
2. **Grant consideration** for funding a professional smart contract audit (Halborn or Runtime Verification)
3. **Co-promotion** of PURECORTEX as a flagship AI-native project on Algorand

### Contact

- Email: security@purecortex.ai
- Twitter: @purecortexai
- Website: https://purecortex.ai

---

## 3. Partnership Outreach

### 3a. Tinyman

**Subject:** PURECORTEX -- CORTEX/ALGO Pool Live, Requesting Token Verification

Hi Tinyman team,

PURECORTEX has an active CORTEX/ALGO pool on Tinyman (pool address: HMLZPDAKN2XO4F47KR656U3SMTMGKLSLS5HO6NHFT2JGFGT7JP6UCK66XE, pool token ASA: 3502697927).

We would like to request:
1. **Token verification** for $CORTEX (ASA 3501164627) so it displays with our name, logo, and unit name in the Tinyman interface.
2. **Listing visibility** in the Tinyman token directory.

PURECORTEX is an AI agent launchpad on Algorand with bonding curves and constitutional governance. We launched on MainNet on March 31, 2026. Our token has a 0% VC / 0% team model (10% creator with 180-day vest, 90% community).

Website: https://purecortex.ai
GitHub: https://github.com/chaosoracleforall-agent/purecortexai

Happy to provide any additional information needed for verification.

Thanks,
PureCortex Team

---

### 3b. Pact

**Subject:** PURECORTEX -- CORTEX/ALGO Pool Live on Pact, Token Verification Request

Hi Pact team,

We have deployed a CORTEX/ALGO liquidity pool on Pact (pool app ID: 3502703728, pool token ASA: 3502703733).

We would like to request token verification for $CORTEX (ASA 3501164627) to ensure correct display in the Pact interface.

PURECORTEX is a sovereign AI agent launchpad on Algorand. Launched March 31, 2026. 0% VC, 90% community distribution.

Website: https://purecortex.ai
GitHub: https://github.com/chaosoracleforall-agent/purecortexai

Let us know if you need anything else for the verification process.

Thanks,
PureCortex Team

---

### 3c. Vestige.fi

**Subject:** PURECORTEX -- Token Tracking and Analytics Request

Hi Vestige team,

We would like to request that $CORTEX (ASA 3501164627) be added to Vestige.fi for token tracking and analytics.

Key details:
- **Token:** CORTEX (ASA 3501164627)
- **Total supply:** 10 quadrillion (6 decimals)
- **DEX pools:** Tinyman CORTEX/ALGO + Pact CORTEX/ALGO
- **Project:** PURECORTEX -- AI agent launchpad on Algorand
- **Website:** https://purecortex.ai
- **GitHub:** https://github.com/chaosoracleforall-agent/purecortexai

We are live on MainNet since March 31, 2026 with active liquidity on both Tinyman and Pact. Vestige analytics would help our community track price, volume, and liquidity data.

Thanks,
PureCortex Team

---

### 3d. NFD (Non-Fungible Domains)

**Subject:** PURECORTEX Airdrop Partnership -- NFD Holder Tier

Hi NFD team,

PURECORTEX has launched a genesis airdrop with 31% of total $CORTEX supply distributed across 7 eligibility tiers. One of those tiers is **NFD Holders** (10% of the airdrop allocation), rewarding anyone who owns at least one .algo domain.

We would be interested in discussing:
1. **Co-promotion** of the NFD holder airdrop tier to drive awareness for both projects.
2. **NFD integration** in our platform (displaying .algo names instead of raw addresses in the marketplace and governance UI).
3. **Cross-community engagement** between the NFD and PURECORTEX communities.

We believe rewarding NFD holders aligns both communities around Algorand ecosystem growth. NFD holders represent engaged, identity-verified Algorand participants, which is exactly the user base we want in our governance system.

Website: https://purecortex.ai/airdrop
GitHub: https://github.com/chaosoracleforall-agent/purecortexai

Would love to set up a quick call to discuss.

Thanks,
PureCortex Team

---

### 3e. ASA Stats / Algoscan

**Subject:** PURECORTEX -- Explorer Metadata for CORTEX Token and Contracts

Hi team,

We would like to submit metadata for the following Algorand MainNet assets and applications for display in your explorer:

**Token:**
- CORTEX (ASA 3501164627) -- PureCortex protocol token

**Applications:**
| Name | App ID |
|------|--------|
| AgentFactory | 3501164435 |
| GovernanceContract | 3501164276 |
| VeCortexStaking | 3501164346 |
| SovereignTreasury | 3501164386 |
| CreatorVesting | 3501164479 |
| AirdropClaim | 3502246857 |

**Project:** PURECORTEX -- Sovereign AI agent launchpad on Algorand
**Website:** https://purecortex.ai
**GitHub:** https://github.com/chaosoracleforall-agent/purecortexai

Please let us know the process for submitting logo assets and contract descriptions for your explorer.

Thanks,
PureCortex Team

---

## 4. Immunefi Publication Checklist

Reference: `docs/IMMUNEFI_BOUNTY_SPEC.md`

### Steps to Publish

1. **Create Immunefi account**
   - Sign up at https://immunefi.com/ with the project email (security@purecortex.ai)
   - Complete project owner verification

2. **Prepare required assets**
   - [ ] Project logo (256x256 PNG and SVG) -- available at `frontend/public/logo-256.png` and `frontend/public/logo-square.svg`
   - [ ] Project description (1-2 paragraphs for the Immunefi listing page)
   - [ ] Links: website (https://purecortex.ai), GitHub, documentation

3. **Define program scope**
   - [ ] Smart contracts in scope (6 contracts, paths per `IMMUNEFI_BOUNTY_SPEC.md`):
     - `contracts/smart_contracts/agent_factory/`
     - `contracts/smart_contracts/governance/`
     - `contracts/smart_contracts/staking/`
     - `contracts/smart_contracts/sovereign_treasury/`
     - `contracts/smart_contracts/creator_vesting/`
     - AirdropClaim (add to scope -- not in original spec)
   - [ ] Backend components in scope:
     - `backend/src/api/`
     - `backend/orchestrator.py`
     - `backend/src/services/signing_vault.py`
     - `backend/src/services/signer_daemon.py`
   - [ ] Out-of-scope items documented (frontend UI, third-party deps, social engineering, DDoS)

4. **Configure rewards table**

   | Severity | Smart Contracts | Backend / Infra |
   |----------|----------------|-----------------|
   | Critical | $25,000 | $10,000 |
   | High | $10,000 | $5,000 |
   | Medium | $2,500 | $1,000 |
   | Low | $500 | $250 |

   - Payment method: ALGO or CORTEX at reporter's choice (market price at payout time)

5. **Set severity definitions**
   - Map each severity level to specific vulnerability categories per `IMMUNEFI_BOUNTY_SPEC.md`
   - Critical: loss of funds, signing vault bypass, governance takeover, treasury drain
   - High: privilege escalation, prompt injection, auth bypass, consensus manipulation
   - Medium: info disclosure, DoS, race conditions, state corruption
   - Low: rounding errors, non-critical exposure, validation gaps

6. **Define rules of engagement**
   - Responsible disclosure via Immunefi only
   - No mainnet exploitation (testnet only for PoC)
   - Proof of concept required
   - One report per vulnerability
   - No social engineering

7. **Submit for Immunefi review**
   - Immunefi reviews and approves the program listing
   - Typical review time: 3-5 business days

8. **Publish and announce**
   - [ ] Program goes live on Immunefi
   - [ ] Announce on Twitter (@purecortexai)
   - [ ] Post in Algorand Discord #showcase
   - [ ] Update CLAUDE.md and project README with bounty link
   - [ ] Social Agent includes bounty link in launch content rotation

### Note on AirdropClaim

The `IMMUNEFI_BOUNTY_SPEC.md` was written before AirdropClaim was deployed. Update the spec to add AirdropClaim (App ID: 3502246857, path: `contracts/smart_contracts/airdrop_claim/`) to the in-scope table before publishing.
