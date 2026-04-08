# PURECORTEX Bug Bounty Program — Immunefi

## Overview

PURECORTEX operates an active bug bounty program on [Immunefi](https://immunefi.com/) to incentivize responsible disclosure of security vulnerabilities in the protocol's smart contracts, backend infrastructure, and AI agent framework.

## Scope

### In Scope

| Component | Repository Path | Severity Range |
|-----------|----------------|----------------|
| **AgentFactory** (Puya/TEAL) | `contracts/smart_contracts/agent_factory/` | Critical - Low |
| **GovernanceContract** (Puya/TEAL) | `contracts/smart_contracts/governance/` | Critical - Low |
| **VeCortexStaking** (Puya/TEAL) | `contracts/smart_contracts/staking/` | Critical - Low |
| **SovereignTreasury** (Puya/TEAL) | `contracts/smart_contracts/sovereign_treasury/` | Critical - Low |
| **CreatorVesting** (Puya/TEAL) | `contracts/smart_contracts/creator_vesting/` | Critical - Low |
| **Backend API** (FastAPI) | `backend/src/api/` | High - Low |
| **Tri-Brain Orchestrator** | `backend/orchestrator.py` | High - Low |
| **Signing Vault** | `backend/src/services/signing_vault.py` | Critical - Low |
| **Signer Daemon** | `backend/src/services/signer_daemon.py` | Critical - Low |

### Out of Scope

- Frontend UI (cosmetic issues, UX bugs)
- Third-party dependencies (report upstream)
- Social engineering attacks
- DDoS/rate limiting issues
- Known issues documented in `SECURITY_AUDIT.md`

## Reward Schedule

| Severity | Smart Contracts | Backend / Infra |
|----------|----------------|-----------------|
| **Critical** | $25,000 | $10,000 |
| **High** | $10,000 | $5,000 |
| **Medium** | $2,500 | $1,000 |
| **Low** | $500 | $250 |

Rewards are paid in ALGO or CORTEX (at the reporter's choice, valued at market price at time of payout).

## Severity Definitions

### Critical
- Loss of funds (bonding curve manipulation, unauthorized token minting)
- Bypass of signing vault isolation (private key extraction)
- Governance takeover (unauthorized proposal execution)
- Treasury drain (unauthorized withdrawal from Assistance Fund)

### High
- Privilege escalation (tier bypass in agent sandboxing)
- Prompt injection leading to unauthorized agent actions
- Authentication bypass in API/admin surfaces
- Consensus manipulation (forcing specific tri-brain outcomes)

### Medium
- Information disclosure (API key leakage, wallet data exposure)
- Denial of service against specific protocol functions
- Race conditions in buy/sell flows causing incorrect pricing
- Memory/state corruption in agent framework

### Low
- Minor rounding errors in bonding curve math
- Non-critical information exposure
- Input validation gaps without security impact

## Rules of Engagement

1. **Responsible Disclosure**: Report vulnerabilities through Immunefi. Do not disclose publicly before the fix is deployed.
2. **No Mainnet Exploitation**: Test on testnet only. Do not attempt to exploit mainnet contracts.
3. **Proof of Concept Required**: Include a clear PoC demonstrating the vulnerability.
4. **One Report per Vulnerability**: Submit separate reports for separate issues.
5. **No Social Engineering**: Attacks against team members are out of scope.

## Contact

- **Immunefi Program Page**: [immunefi.com/bounty/purecortex](https://immunefi.com/bounty/purecortex) *(to be published)*
- **Security Email**: security@purecortex.ai
- **PGP Key**: Available in `SECURITY.md`

## Timeline

- **Program Launch**: March 31, 2026 (coinciding with public repo release)
- **Initial Review Period**: 21 days (enhanced rewards during this period)
- **Ongoing**: Continuous program after initial review period
