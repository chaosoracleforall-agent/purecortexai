# PURECORTEX Mainnet Go/No-Go Packet (2026-03-25)

Cross-reference: documentation status update recorded in `CHANGELOG.md` under `0.8.1 - 2026-03-25`.

## Decision

- **Current Recommendation:** `NO-GO` until operational blockers are cleared.

## What Passed

- **Contract unit tests:** `51 passed`
  - Command: `PYTHONPATH=. poetry run pytest tests/ -v` (from `contracts`)
- **Backend unit tests:** `53 passed, 2 skipped`
  - Command: `venv/bin/python -m pytest tests/ -v` (from `backend`)
- **Airdrop Merkle tests:** `14 passed`
  - Command: `venv/bin/python -m pytest scripts/test_airdrop_snapshot.py -v` (from repo root)

## Security Remediations Applied This Sprint

- `contracts/smart_contracts/agent_factory/contract.py`
  - Clamped sell fee to prevent underflow at tiny gross values.
  - Reworked graduation valuation arithmetic to avoid UInt64 overflow.
  - Enforced non-zero protocol fee floor (`MIN_FEE_BPS=1`) to block zero-fee rounding arbitrage.
- `contracts/smart_contracts/sovereign_treasury/contract.py`
  - Added sender-binding and strict adjacent group-index validation for `process_revenue` and `execute_burn` references.
- `contracts/smart_contracts/staking/contract.py`
  - Added creator-gated reward distribution path (`distribute_reward`) and reward-pool visibility (`get_reward_pool`).
  - Expired `ve_power` after unlock in `get_ve_power()` (`0` when lock is no longer active).
- Added security regression tests:
  - `contracts/tests/test_agent_factory.py`
  - `contracts/tests/test_governance_contract.py`
  - `contracts/tests/test_creator_vesting.py`
  - `contracts/tests/test_sovereign_treasury.py`
  - `contracts/tests/test_staking_contract.py`
  - `backend/tests/test_orchestrator_security.py`
  - `backend/tests/test_auth_middleware_security.py`
  - `backend/tests/test_websocket_auth_security.py`
  - `scripts/test_airdrop_snapshot.py`
- Recompiled contract artifacts after fixes via `poetry run python -m smart_contracts build` (`contracts/smart_contracts/artifacts/*` refreshed).

## Residual Risk Register

| ID | Severity | Risk | Status | Mitigation / Owner |
|---|---|---|---|---|
| R-001 | High | Full frontend Playwright suite not passing in this runtime due browser binary path/arch mismatch. | Resolved (this environment) | Runtime hardened in `frontend/playwright.config.ts`; `npx playwright test` now green (`8 passed, 1 skipped`). |
| R-002 | High | Admin e2e smoke still fails for same browser execution path mismatch. | Resolved (this environment) | E2E specs stabilized and runtime fixed; `npm run test:e2e:admin:smoke` now green (`4 passed`). |
| R-003 | Medium | Live testnet smoke cannot execute without funded disposable trader wallet and `DEPLOYER_MNEMONIC`. | Open | Fund prepared wallet and inject deployer mnemonic securely before rerun. |
| R-004 | Medium | Two signer-daemon tests are skipped where unix socket bind is unavailable in runtime. | Accepted (temporary) | Keep CI/runtime note; validate signer tests in environment permitting unix socket bind. |

## Required Before Mainnet GO

1. Clear `R-003` by running full live smoke after wallet funding and mnemonic provisioning.
2. Reconfirm launch checklist items in `CLAUDE.md` gates using updated evidence.
