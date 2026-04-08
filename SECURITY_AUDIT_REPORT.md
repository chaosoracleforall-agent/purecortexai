# PURECORTEX — Comprehensive Security Audit Report

> **Classification:** CONFIDENTIAL — Pre-Mainnet
> **Report Version:** 1.0
> **Audit Date:** March 23, 2026
> **Target TGE:** March 31, 2026
> **Branch:** `mainnet-launch` (commit `d9541a2`)
> **Methodology:** Full-spectrum line-by-line manual review
> **Audited By:** AI Security Audit Engine (OpenZeppelin/Trail of Bits methodology)

---

## Executive Summary

This report documents a comprehensive security audit of the PureCortex protocol covering **all smart contracts, the Python/FastAPI backend, the Next.js frontend, and all deployment infrastructure**. The audit was conducted using the same methodology employed by firms such as OpenZeppelin and Trail of Bits: line-by-line manual review of every function, every arithmetic operation, every authorization check, every input validation path, and every infrastructure configuration.

### Findings Overview

| Severity | Smart Contracts | Backend | Frontend | Infrastructure | **Total** |
|----------|:-:|:-:|:-:|:-:|:-:|
| **CRITICAL** | 2 | 2 | 0 | 0 | **4** |
| **HIGH** | 5 | 6 | 1 | 3 | **15** |
| **MEDIUM** | 8 | 9 | 5 | 5 | **27** |
| **LOW** | 8 | 3 | 4 | 5 | **20** |
| **INFORMATIONAL** | 5 | 7 | 1 | 4+ | **17+** |
| **Total** | **28** | **27** | **11** | **17+** | **83+** |

### Audit Verdict

**DO NOT DEPLOY TO MAINNET** until all CRITICAL and HIGH findings are remediated. The protocol contains 4 critical vulnerabilities that would result in complete governance takeover (SC-01/SC-02) and authentication bypass (BE-01/BE-02) in production. The 15 HIGH findings include broken protocol economics (SC-03), rug-pull vectors (SC-07), and multiple fail-open security paths.

### 2026-03-25 Internal Sprint Addendum

This report has an implementation-validation addendum from the internal audit sprint executed on 2026-03-25.

- New benchmark and control-traceability artifacts:
  - `docs/ALGOLAND_AUDIT_BENCHMARK_MATRIX.md`
  - `docs/PURECORTEX_CONTROL_TRACEABILITY.md`
- New security-focused tests added for contracts, backend auth/orchestrator/websocket, and Merkle proofs.
- Contract remediations in this sprint now include:
  - `AgentFactory`: sell-fee underflow hardening, overflow-safe graduation arithmetic, and non-zero fee floor (`MIN_FEE_BPS=1`) with symmetry regression tests.
  - `SovereignTreasury`: sender-binding plus strict adjacency checks for `process_revenue` and `execute_burn` referenced transactions.
  - `VeCortexStaking`: creator-gated reward distribution path (`distribute_reward`) with reward-pool read method, and `ve_power` expiry after unlock.
- Verified post-fix regression results:
  - contracts: `51 passed` via `PYTHONPATH=. poetry run pytest tests/ -v`,
  - focused remediated-path regressions: `31 passed`,
  - backend: `53 passed, 2 skipped`,
  - airdrop snapshot tests: `14 passed`.
- Contract artifacts were rebuilt after remediation via `poetry run python -m smart_contracts build`, refreshing TEAL/ARC56/client outputs under `contracts/smart_contracts/artifacts/*`.
- Playwright runtime and spec stabilization completed in this environment:
  - admin smoke: `4 passed` via `npm run test:e2e:admin:smoke`,
  - full frontend E2E: `8 passed, 1 skipped` via `npx playwright test`.

---

## Table of Contents

1. [Scope](#1-scope)
2. [Critical Findings](#2-critical-findings)
3. [High Findings](#3-high-findings)
4. [Medium Findings](#4-medium-findings)
5. [Low Findings](#5-low-findings)
6. [Informational Findings](#6-informational-findings)
7. [Positive Security Observations](#7-positive-security-observations)
8. [Remediation Priority Matrix](#8-remediation-priority-matrix)
9. [Test Coverage Gap Analysis](#9-test-coverage-gap-analysis)

---

## 1. Scope

### Smart Contracts (Algorand / Puya / algopy → TEAL)

| Contract | File | Lines |
|----------|------|-------|
| AgentFactory | `contracts/smart_contracts/agent_factory/contract.py` | Bonding curve, token creation, buy/sell, graduation, fees |
| GovernanceContract | `contracts/smart_contracts/governance/contract.py` | Proposal lifecycle, voting, timelock, execution |
| VeCortexStaking | `contracts/smart_contracts/staking/contract.py` | Lock, unlock, veCORTEX power, delegation |
| SovereignTreasury | `contracts/smart_contracts/sovereign_treasury/contract.py` | Revenue split, buyback-burn, operations |
| CreatorVesting | `contracts/smart_contracts/creator_vesting/contract.py` | 10% TGE + 180-day linear vest |

### Backend (Python / FastAPI)

- API layer: auth, agents, marketplace, governance, staking, admin, developer access, internal admin, chat
- AI orchestrator: tri-brain consensus (Claude + Gemini + GPT-5)
- Signing vault and isolated signer daemon
- Services: API key management, chat sessions, governance voting, social campaign, protocol config

### Frontend (Next.js 15/16 / React)

- All components, pages, layouts, and library modules
- Admin console and API proxy routes
- Wallet integration (Pera, Defly, Lute, Exodus, Kibisis)
- Transaction building and signing

### Infrastructure

- Docker Compose (7 services + Cloud SQL proxy)
- Nginx reverse proxy and TLS configuration
- GCP deployment scripts and secret management
- Mainnet VM provisioning and setup

---

## 2. Critical Findings

---

### SC-01 — Governance Vote Recycling Enables Unlimited Vote Multiplication

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **Contract** | GovernanceContract |
| **Function** | `cast_vote` |
| **Impact** | Complete governance takeover |

**Description:** The `cast_vote` function accepts CORTEX tokens as vote weight and **immediately returns them** to the voter via an inner transaction in the same application call. The cost of voting is zero. An attacker holding N CORTEX can:

1. Vote from Account A with N CORTEX (returned immediately)
2. Transfer N CORTEX to Account B
3. Vote from Account B with N CORTEX (returned immediately)
4. Repeat across unlimited Sybil accounts

The one-address-one-vote box check only prevents the **same account** from double-voting — it does not prevent the **same tokens** from being recycled. An attacker with 1M CORTEX could cast 100M+ effective vote weight using 100 accounts.

**Recommendation:** Do NOT return CORTEX immediately. Lock tokens for the voting period and return via a separate `reclaim_vote` method after finalization. Alternatively, integrate with VeCortexStaking and use on-chain veCORTEX power snapshots.

---

### SC-02 — Missing Sender Validation on Vote Transfer Enables Vote Theft

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **Contract** | GovernanceContract |
| **Function** | `cast_vote` |
| **Impact** | Vote weight hijacking + CORTEX theft |

**Description:** The `cortex_txn` parameter is validated for asset ID, receiver, and amount — but **never for sender**. The contract does not assert `cortex_txn.sender == Txn.sender`. In a multi-party group transaction, Alice can include her `cast_vote` call alongside Bob's CORTEX transfer. Alice's vote gets Bob's weight, and the returned CORTEX goes to Alice (Txn.sender), not Bob.

**Recommendation:** Add `assert cortex_txn.sender == Txn.sender, "CORTEX sender must match caller"`.

---

### BE-01 — WebSocket Authentication Bypass When Redis Is Unavailable

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **File** | `backend/main.py` |
| **Endpoint** | `/ws/chat` |
| **Impact** | Unauthenticated access to tri-brain AI pipeline |

**Description:** When Redis is unavailable at startup, both `api_key_manager` and `chat_session_manager` are set to `None`. The WebSocket authentication logic has three conditional branches, all guarded by truthiness checks on these managers. If both are `None`, every branch is skipped and execution falls through to `manager.connect(websocket)`, accepting the connection with **zero authentication**.

**Recommendation:** Add a fail-closed guard:
```python
if not api_key_mgr and not chat_session_mgr:
    await websocket.close(code=4003, reason="Authentication service unavailable")
    return
```

---

### BE-02 — Rate Limiter Fails Open on Redis Outage

| Field | Value |
|-------|-------|
| **Severity** | CRITICAL |
| **File** | `backend/main.py` |
| **Function** | `rate_limit_middleware` |
| **Impact** | Unlimited request throughput for all endpoints |

**Description:** The global rate limiter wraps Redis calls in a bare `except Exception: pass` block. If Redis is down, all rate limiting is silently bypassed. An attacker who causes Redis instability (or waits for a transient outage) gets unlimited throughput for brute-force attacks, LLM API abuse, and governance vote flooding.

**Recommendation:** Fail closed — return 503 or apply a conservative in-memory fallback rate limit when Redis is unavailable.

---

## 3. High Findings

---

### SC-03 — Fee ALGO Permanently Locked in AgentFactory

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Contract** | AgentFactory |
| **Impact** | Protocol economics completely broken |

**Description:** Every buy/sell charges a fee (1%/2%) but there is **no method** to extract this accumulated fee ALGO from the AgentFactory. No sweep, no transfer to SovereignTreasury. The entire 90/10 buyback-burn revenue model is non-functional — fee revenue is irrecoverably locked.

**Recommendation:** Add a creator-only `sweep_fees` method that calculates excess ALGO (balance minus theoretical curve reserve) and transfers it to the SovereignTreasury.

---

### SC-04 — Quorum Percentage Parameter Is Dead Code

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Contract** | GovernanceContract |
| **Impact** | Governance quorum cannot adapt to supply changes |

**Description:** `QUORUM_BPS` (25%) is defined and updatable via admin but **never read**. The finalize function hardcodes `total_votes >= 1_000_000_000_000`. Changing QUORUM_BPS has zero effect.

**Recommendation:** Replace the hardcoded check with `QUORUM_BPS`-based calculation against circulating supply.

---

### SC-05 — Agent Token Freeze/Clawback Not Locked

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Contract** | AgentFactory |
| **Impact** | Centralization risk if contract is upgradeable |

**Description:** Agent tokens are created with `freeze` and `clawback` set to `Global.current_application_address`. No current methods use these, but if the contract is upgradeable, a malicious update could freeze or clawback any user's tokens.

**Recommendation:** Set `freeze=Global.zero_address` and `clawback=Global.zero_address`.

---

### SC-06 — Governance Parameters Mutable During Active Proposals

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Contract** | GovernanceContract |
| **Impact** | Complete bypass of timelocks and thresholds |

**Description:** `update_governance_parameters` can change discussion, voting, and timelock periods while proposals are active. These changes apply retroactively since they're read at execution time, not snapshotted at proposal creation. The creator could set all periods to 1 round and pass any proposal instantly.

**Recommendation:** Snapshot governance parameters per-proposal at creation time.

---

### SC-07 — Unbounded CORTEX Distribution (Rug Pull Vector)

| Field | Value |
|-------|-------|
| **Severity** | HIGH |
| **Contract** | AgentFactory |
| **Impact** | Creator can drain entire token supply |

**Description:** `distribute_cortex` is capped at 1M per call but has no aggregate limit. The creator can call it repeatedly to drain all CORTEX from the factory with no governance approval, timelock, or multi-sig.

**Recommendation:** Add a `total_distributed` counter with an aggregate cap. Require governance approval for distributions above a threshold.

---

### BE-03 — Developer Access Cooldown Fails Open

| **Severity** | HIGH |
| **File** | `src/api/developer_access.py` |
| **Impact** | Mass spam of developer access requests |

Redis errors in the cooldown check return `False` (no cooldown). Should return `True` to fail closed.

---

### BE-04 — API Key Hashing Uses Plain SHA-256 (Not HMAC)

| **Severity** | HIGH |
| **File** | `src/services/api_keys.py` |
| **Impact** | Offline key recovery if Redis data leaks |

The Redis-backed key manager uses plain SHA-256 instead of HMAC-SHA256 with a server-side secret. If Redis data is leaked, keys are vulnerable to offline brute-force.

---

### BE-05 — Prompt Injection in WebSocket Chat

| **Severity** | HIGH |
| **File** | `backend/main.py` |
| **Impact** | System prompt override, LLM instruction hijacking |

User input from WebSocket is passed directly to the orchestrator. The XML-tag escaping only targets `</user_query>` — the opening tag is not escaped, and model-specific control tokens are not filtered.

---

### BE-06 — Chat Session Tokens Not Invalidated After Disconnect

| **Severity** | HIGH |
| **File** | `main.py`, `src/services/chat_sessions.py` |
| **Impact** | Session hijacking via stolen tokens |

Session tokens remain valid for full TTL (15 min) after WebSocket disconnect. Stolen tokens can be reused.

---

### BE-07 — Signed Vote Nonce Not Checked for Replay

| **Severity** | HIGH |
| **File** | `src/services/governance_voting.py` |
| **Impact** | Front-running of governance votes |

Nonces are validated for format but never stored server-side. Used nonces are not rejected. Intercepted signed votes can be front-run.

---

### BE-08 — Internal Admin Health Leaks Configuration Details

| **Severity** | HIGH |
| **File** | `src/api/internal_admin.py` |
| **Impact** | Reconnaissance via configuration disclosure |

Returns `owner_emails`, `database_configured`, `oauth_configured`, and `ip_trust_configured` to anyone with the internal admin token.

---

### FE-02 — CSP `unsafe-inline` Defeats XSS Protection

| **Severity** | HIGH |
| **File** | `nginx.conf`, `nginx.mainnet.conf` |
| **Impact** | Any XSS can execute arbitrary JavaScript |

`script-src 'unsafe-inline'` effectively neuters CSP's XSS protection. Next.js supports nonce-based CSP as the proper alternative.

---

### INFRA-01 — Signer Container Runs as Root

| **Severity** | HIGH |
| **File** | `backend/Dockerfile.signer` |
| **Impact** | Container escape grants root on host |

Unlike backend and frontend Dockerfiles, the signer has no `USER` directive. A container escape vulnerability would grant root-level host access — compromising all signing keys.

---

### INFRA-03 — Deployer Mnemonic Exposed as CLI Argument

| **Severity** | HIGH |
| **Files** | `scripts/deploy_mainnet.py`, `scripts/setup_liquidity.py` |
| **Impact** | Mnemonic visible in process listings and shell history |

Both scripts accept the deployer mnemonic as `--deployer-mnemonic`. Command-line args are visible via `/proc/*/cmdline` and persisted in shell history.

---

## 4. Medium Findings

| ID | Layer | Title |
|----|-------|-------|
| **SC-08** | Contract | CEI violation in `execute_burn` (state after inner txn) |
| **SC-09** | Contract | CEI violation in `withdraw_buyback_algo` |
| **SC-10** | Contract | Stuck pending agent blocks all future creation (DoS) |
| **SC-11** | Contract | Missing authorization on `finalize_agent_config` |
| **SC-12** | Contract | Staking reward pool tracked but never distributable |
| **SC-13** | Contract | CORTEX token manager address not locked after bootstrap |
| **SC-14** | Contract | Missing `payment.sender` validation in `process_revenue` |
| **SC-15** | Contract | Graduation mechanism is read-only with no execution path |
| **BE-09** | Backend | Exception messages forwarded to clients (info disclosure) |
| **BE-10** | Backend | Internal admin IP allowlist defaults to allow-all when empty |
| **BE-11** | Backend | Settings cached forever via `lru_cache` (no secret rotation) |
| **BE-12** | Backend | Admin secrets loaded at module import time (not rotatable) |
| **BE-13** | Backend | Signer daemon returns full exception strings |
| **BE-14** | Backend | Hardcoded owner email for privilege elevation |
| **BE-15** | Backend | No WebSocket scope/tier enforcement (any key = chat access) |
| **BE-16** | Backend | Governance vote weight override for API-key path |
| **BE-17** | Backend | Incomplete XML-tag escaping in prompt injection defense |
| **FE-01** | Frontend | XSS via post-sanitization heading injection in docs |
| **FE-03** | Frontend | API key stored in `sessionStorage` (XSS = key theft) |
| **FE-07** | Frontend | Bigint-to-Number precision loss in buy transactions |
| **FE-08** | Frontend | TOCTOU gap in buy/sell quotes (no slippage protection) |
| **INFRA-02** | Infra | Frontend container missing `no-new-privileges`, `cap_drop` |
| **INFRA-05** | Infra | Docker base images not pinned by digest |
| **INFRA-07** | Infra | `TRUST_PROXY_HEADERS` defaults to 1 in sync script |
| **INFRA-08** | Infra | No automated database backup strategy |

---

## 5. Low Findings

| ID | Layer | Title |
|----|-------|-------|
| **SC-16** | Contract | Bonding curve rounding systematically favors buyers |
| **SC-17** | Contract | Zero veCORTEX power for micro-stakes (no minimum) |
| **SC-18** | Contract | Vesting daily tranche precision loss |
| **SC-19** | Contract | `operations_address` can be set to zero address |
| **SC-20** | Contract | Vote/finalize race condition at period boundary |
| **SC-21** | Contract | Overpayment of creation fee accepted without refund |
| **SC-22** | Contract | `MAX_TX_AMOUNT` is 100x larger than `MAX_AGENT_SUPPLY` |
| **SC-23** | Contract | Supermajority rounding error at large vote totals |
| **BE-18** | Backend | WebSocket session token in query parameter (log leakage) |
| **BE-19** | Backend | `has_active_keys` uses Redis SCAN (O(n) performance) |
| **BE-20** | Backend | CORS missing PATCH method for admin routes |
| **FE-04** | Frontend | No explicit CSRF tokens on admin state-changing routes |
| **FE-05** | Frontend | Dev admin session cookie without `Secure` flag |
| **FE-06** | Frontend | No rate limiting on admin-api routes |
| **FE-09** | Frontend | `dangerouslySetInnerHTML` (mitigated by sanitization) |
| **INFRA-04** | Infra | TLS session tickets not disabled |
| **INFRA-06** | Infra | Signer socket mode 666 (world-accessible within volume) |
| **INFRA-09** | Infra | Redis password visible in healthcheck process |
| **INFRA-10** | Infra | 24-hour WebSocket timeout enables connection exhaustion |

---

## 6. Informational Findings

| ID | Layer | Title |
|----|-------|-------|
| **SC-24** | Contract | Critically insufficient test coverage for state-mutating functions |
| **SC-25** | Contract | No emergency pause mechanism across contracts |
| **SC-26** | Contract | No explicit contract upgrade/immutability declaration |
| **SC-27** | Contract | Cross-contract integration gaps (isolated economic model) |
| **SC-28** | Contract | `execute_burn` callable by anyone (intentional?) |
| **BE-21** | Backend | No test coverage for WebSocket authentication flows |
| **BE-22** | Backend | No test coverage for rate limiting behavior |
| **BE-23** | Backend | No test coverage for session token lifecycle |
| **BE-24** | Backend | No test coverage for internal admin endpoints |
| **BE-25** | Backend | Python `str` reassignment does not zero memory |
| **BE-26** | Backend | Global exception handler masks security-relevant failures |
| **BE-27** | Backend | Signing vault temp cleanup could affect concurrent operations |
| **FE-10** | Frontend | `img-src` CSP allows all HTTPS sources |
| **INFRA-11** | Infra | OAuth2 proxy allows all domains (mitigated by email file) |

---

## 7. Positive Security Observations

The following design decisions were found to be well-implemented:

1. **Network Segmentation:** Only Nginx exposes host ports. Internal services use Docker networks with the `internal` flag. Signer is fully air-gapped (`network_mode: none`).

2. **Admin Header Injection Prevention:** All non-admin Nginx locations explicitly set `X-PURECORTEX-AUTH-EMAIL ""`, preventing spoofing. Admin routes source the header only from authenticated OAuth2 proxy.

3. **Container Hardening (Backend/Signer):** `no-new-privileges`, `cap_drop: ALL`, resource limits, log rotation, healthchecks. Signer additionally uses `read_only: true`.

4. **GCP VM Security:** Mainnet VM uses Shielded VM (Secure Boot, vTPM, Integrity Monitoring), IAP-only SSH, OS Login, and a dedicated service account with least-privilege IAM bindings.

5. **Signing Vault Architecture:** Subprocess isolation for key material, Unix socket communication, shared token authentication, GPG encryption of mnemonics at rest.

6. **Developer Access Key Model:** HMAC-SHA256 key derivation, scope-based authorization, automatic key rotation, audit logging.

---

## 8. Remediation Priority Matrix

### Immediate — MUST FIX BEFORE MAINNET (Blocks TGE)

| # | Finding | Effort | Risk if Unfixed |
|---|---------|--------|-----------------|
| 1 | **SC-01** Governance vote recycling | Medium | Total governance takeover |
| 2 | **SC-02** Missing sender check in cast_vote | Trivial | Vote theft + CORTEX theft |
| 3 | **BE-01** WebSocket auth bypass | Trivial | Unauthenticated AI access |
| 4 | **BE-02** Rate limit fail-open | Trivial | Unlimited abuse |
| 5 | **SC-03** Locked fee ALGO | Medium | Protocol economics dead |
| 6 | **SC-07** Unbounded distribute_cortex | Low | Creator rug pull |
| 7 | **SC-06** Mutable governance parameters | Medium | Timelock bypass |
| 8 | **SC-05** Agent token freeze/clawback | Trivial | Centralization risk |
| 9 | **INFRA-01** Signer runs as root | Trivial | Container escape = root |
| 10 | **INFRA-03** Mnemonic as CLI arg | Low | Key exposure |

### Pre-Launch — Fix Within First Sprint

| # | Finding | Effort |
|---|---------|--------|
| 11 | **BE-04** HMAC for API key hashing | Low |
| 12 | **BE-05** Prompt injection hardening | Medium |
| 13 | **BE-06** Session token invalidation | Low |
| 14 | **BE-07** Nonce replay prevention | Low |
| 15 | **FE-02** CSP nonce-based (remove unsafe-inline) | Medium |
| 16 | **SC-04** Use QUORUM_BPS properly | Low |
| 17 | **SC-10** Pending agent abort mechanism | Low |
| 18 | **SC-13** Lock CORTEX token manager to zero | Trivial |
| 19 | **INFRA-02** Frontend container hardening | Trivial |
| 20 | **INFRA-05** Pin Docker images by digest | Low |

### Post-Launch — Address Within 30 Days

| # | Finding | Effort |
|---|---------|--------|
| 21-27 | All MEDIUM findings (SC-08/09/11/12/14/15, BE-09-17) | Varies |
| 28-38 | All LOW findings | Varies |
| 39 | **SC-24** + **BE-21-24** Comprehensive test coverage | High |
| 40 | **SC-25** Emergency pause mechanism | Medium |
| 41 | **SC-15** + **SC-27** Cross-contract integration | High |

---

## 9. Test Coverage Gap Analysis

The following critical code paths have **zero automated test coverage**:

### Smart Contracts

| Contract | Untested State-Mutating Methods |
|----------|-------------------------------|
| AgentFactory | `bootstrap_protocol`, `create_agent` (full), `finalize_agent_config`, `buy_tokens`, `sell_tokens`, `distribute_cortex`, all fee/parameter updates, all authorization rejection paths |
| GovernanceContract | `create_proposal`, `advance_to_voting`, `cast_vote`, `finalize_proposal`, `execute_proposal`, `cancel_proposal`, double-vote prevention, timing enforcement |
| VeCortexStaking | `stake`, `unstake`, `delegate`, `revoke_delegation`, `fund_reward_pool`, boost calculation, lock expiry enforcement |
| SovereignTreasury | `initialize`, `process_revenue`, `execute_burn`, `withdraw_buyback_algo`, revenue split math, all admin methods |
| CreatorVesting | `claim` (full inner txn flow), `initialize` (full flow), non-beneficiary rejection |

### Backend

| Component | Untested Paths |
|-----------|---------------|
| WebSocket | Auth bypass on Redis unavailability, session token flow, rate limiting per connection |
| Rate Limiting | Fail-open behavior, per-key limits, concurrent request handling |
| Chat Sessions | Token creation, expiry, revocation, reuse |
| Internal Admin | Social agent triggers, API key lifecycle, all CRUD operations |
| Governance Voting | Signed vote verification, nonce tracking, replay prevention |

### Minimum Required Test Additions

To reach the 80-90% coverage required by the CLAUDE.md Unit Testing Gate, the following test files need significant expansion or creation:

1. **Contract integration tests** with full lifecycle flows (create → buy → sell → graduate)
2. **Authorization rejection tests** for every creator-only / beneficiary-only method
3. **WebSocket auth tests** covering all branches including the None-manager path
4. **Rate limit tests** verifying fail-closed behavior
5. **Governance voting tests** with signed vote verification and nonce tracking
6. **Boundary value tests** per the CLAUDE.md Section 11 specification

---

*This report is the canonical security reference for the PureCortex mainnet launch. All CRITICAL and HIGH findings must be remediated and re-verified before any mainnet deployment proceeds. The governance vote recycling vulnerability (SC-01) alone is sufficient to justify a deployment hold.*

---

**End of Report**
