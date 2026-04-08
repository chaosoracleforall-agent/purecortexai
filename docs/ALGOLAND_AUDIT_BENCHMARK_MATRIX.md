# PURECORTEX Internal Audit Benchmark Matrix

This document normalizes findings patterns from publicly available Algorand audit corpora and maps them into actionable control checks for PURECORTEX mainnet readiness.

## Source Corpus (Best-Effort Public Set)

- [Blockshake Algorand ecosystem audit index](https://raw.githubusercontent.com/blockshake-io/algorand-ecosystem-audits/main/README.md)
- [Runtime Verification smart-contract reports index](https://api.github.com/repos/runtimeverification/publications/contents/reports/smart-contracts)
- [Folks Finance public audit repository](https://github.com/Folks-Finance/audits)
- [Tinyman audits and security](https://docs.tinyman.org/audits-and-security)

Representative protocols and reports used as benchmark anchors:

- Tinyman (v1/v1.1/v2) reports and security reviews
- Pact (DEX/router/stableswap) reports
- Folks Finance (design + code audits and later revisions)
- Algofi (lending v1/v2 + AMM/nanoswap)
- Algodex
- Additional public audits listed in the Blockshake index (best-effort coverage)

## Normalized Control Families

### 1) Authorization and Caller Binding

- Creator-only/admin-only methods must assert sender identity.
- Group transaction references must enforce sender binding (for example, `gtxn.sender == Txn.sender` where required).
- Privileged parameter updates should be constrained and auditable.

### 2) Transaction Structure and Input Validation

- Validate asset IDs, receivers, amounts, and expected group semantics.
- Reject ambiguous/unsafe transaction compositions.
- Enforce proposal/state existence checks before all reads/writes.

### 3) Arithmetic, Rounding, and Overflow Safety

- Validate all pricing and threshold arithmetic at UInt64 boundary values.
- Exercise division/rounding corner cases (minimum units, tiny amounts, extreme supply).
- Verify monotonicity and economic invariants under stress.

### 4) State Isolation and Box/Key Safety

- Use explicit key namespaces/prefixes.
- Prove no collisions between logical domains (config, supply, votes, params).
- Delete or rotate reclaimable state safely to prevent replay.

### 5) Governance Integrity and Anti-Replay

- Snapshot governance parameters at proposal creation.
- Protect against vote recycling and duplicate/replay vote records.
- Validate quorum and supermajority calculations across edge values.

### 6) Backend Auth and Fail-Closed Posture

- Fail closed when auth/rate-limit dependencies are unavailable.
- Enforce API key validity, IP allowlists, and tier rate limits.
- Require authenticated bootstrap flows for websocket sessions.

### 7) Signer Isolation and Secret Hygiene

- Use unix-socket boundary with shared token verification in constant time.
- Keep key material outside primary process memory when feasible.
- Fetch passphrases per operation and avoid long-lived secret caches.

### 8) Deployment and Operational Security

- Require explicit confirmation gates in deploy scripts.
- Verify immutable manifest integrity and environment separation.
- Ensure runbooks include rollback, snapshot, and post-deploy verification.

## PURECORTEX Control Mapping (Execution Targets)

- Smart contracts:
  - `contracts/smart_contracts/agent_factory/contract.py`
  - `contracts/smart_contracts/governance/contract.py`
  - `contracts/smart_contracts/staking/contract.py`
  - `contracts/smart_contracts/sovereign_treasury/contract.py`
  - `contracts/smart_contracts/creator_vesting/contract.py`
- Contract tests:
  - `contracts/tests/test_agent_factory.py`
  - `contracts/tests/test_governance_contract.py`
  - `contracts/tests/test_staking_contract.py`
  - `contracts/tests/test_sovereign_treasury.py`
  - `contracts/tests/test_creator_vesting.py`
- Backend:
  - `backend/orchestrator.py`
  - `backend/src/api/auth.py`
  - `backend/main.py`
  - `backend/src/services/signing_vault.py`
  - `backend/src/services/signer_daemon.py`
- Backend tests:
  - `backend/tests/test_auth_bootstrap.py`
  - `backend/tests/test_request_ip.py`
  - `backend/tests/test_signer_daemon.py`
  - `backend/tests/test_signing_vault_security.py`
  - `backend/tests/test_developer_access_api.py`

## Evidence Standard

Each control must be covered by one or more of:

- direct unit/integration tests,
- explicit static assertions in code,
- runtime gate checks in deployment scripts,
- or documented risk acceptance with compensating controls.
