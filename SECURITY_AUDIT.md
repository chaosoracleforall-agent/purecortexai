# PURECORTEX: Internal Security Audit & Hardening Report 🦞

## 1. Smart Contract Audit (Algorand/Puya)

### 1.1. Mathematical Precision (Bonding Curve)
- **Vulnerability Found:** In `calculate_buy_price`, the term `amount_sq // UInt64(2)` uses integer division. For an `amount` of 1, this results in `0`, effectively giving the buyer the slope-based portion of the price for free.
- **Risk:** High (at small scales). Aggregated over many small transactions, this drains the intended liquidity of the curve.
- **Fix:** Implement fixed-point arithmetic or scale the entire calculation by `10^6` (6 decimals) before division to maintain precision.

### 1.2. Reentrancy & State Safety
- **Assessment:** Algorand's atomic transaction model and the use of Inner Transactions in Puya naturally mitigate EVM-style reentrancy. However, the `AgentFactory` must ensure that `agent_supplies` is updated **after** the inner transaction succeeds to maintain state integrity.
- **Status:** Secured via Puya's synchronous execution.

### 1.3. Authorization (Sovereignty)
- **Assessment:** The contract correctly sets `manager`, `reserve`, `freeze`, and `clawback` to the `application_address`.
- **Status:** **HARDENED.** No external EOA can freeze or claw back agent tokens.

## 2. AI Orchestration Audit (OpenClaw/Tri-Brain)

### 2.1. Prompt Injection Mitigation
- **Vulnerability Found:** The `user_prompt` is currently concatenated directly into the `system_prompt` for Gemini and Claude. An attacker could use "Ignore previous instructions" to hijack the agent.
- **Fix:** Implement a "Structural Guardrail" that wraps user input in XML tags (e.g., `<user_query>`) and instructs the models to never escape that context.

### 2.2. Consensus Bypass
- **Assessment:** If one brain returns `NONE` and the other returns an action, the system currently fails. This is safe (Fail-Closed).
- **Status:** **SECURED.**

## 3. Infrastructure & IAM (GCP)

### 3.1. Secret Management
- **Status:** Using GCP Secret Manager is correct.
- **Hardening:** Ensure the VM service account has `roles/secretmanager.secretAccessor` **ONLY** for the specific keys required, not the entire project.

### 3.2. Sandboxing (Emancipation Protocol)
- **Requirement:** Agents must run in a "Restricted Execution Environment."
- **Implementation:** All agent tool-calls via MCP must be routed through a "Permission Proxy" that checks a whitelist of allowed actions (Tiered Escalation).

## 4. Internal Audit Sprint Update (2026-03-25)

### 4.1. New Security Regression Coverage Added

- **Contracts:** Extended adversarial and boundary tests in:
  - `contracts/tests/test_agent_factory.py`
  - `contracts/tests/test_governance_contract.py`
  - `contracts/tests/test_creator_vesting.py`
- **Backend:** Added dedicated security suites:
  - `backend/tests/test_orchestrator_security.py`
  - `backend/tests/test_auth_middleware_security.py`
  - `backend/tests/test_websocket_auth_security.py`
- **Airdrop/Merkle:** Added proof validation tests in:
  - `scripts/test_airdrop_snapshot.py`

### 4.2. Findings Triaged and Remediated

- **High:** Sell-fee minimum floor could underflow `calculate_sell_price` at tiny gross values.
  - **Fix:** Clamp fee to `<= gross` and only apply minimum fee when `gross > 0`.
  - **Code:** `contracts/smart_contracts/agent_factory/contract.py`
- **High:** Graduation valuation path could overflow on large `current_supply` square arithmetic.
  - **Fix:** Replaced direct `supply^2` pattern with overflow-safe split scaling.
  - **Code:** `contracts/smart_contracts/agent_factory/contract.py`
- **High:** Rounding asymmetry in small-value buy/sell flow could reduce fee capture to zero in edge cases.
  - **Fix:** Raised protocol fee floor to non-zero by setting `MIN_FEE_BPS = 1` and added anti-profit symmetry regression coverage.
  - **Code:** `contracts/smart_contracts/agent_factory/contract.py`, `contracts/tests/test_agent_factory.py`
- **Medium:** Treasury referenced external transactions without strict caller-binding and adjacency checks.
  - **Fix:** Added sender binding (`payment.sender == Txn.sender` / `cortex_transfer.sender == Txn.sender`) and group adjacency assertions for `process_revenue` and `execute_burn`.
  - **Code:** `contracts/smart_contracts/sovereign_treasury/contract.py`, `contracts/tests/test_sovereign_treasury.py`
- **Medium:** Staking reward pool accounting existed without a distribution path.
  - **Fix:** Added creator-gated `distribute_reward(...)` flow and `get_reward_pool()` accessor, with active-staker enforcement tests.
  - **Code:** `contracts/smart_contracts/staking/contract.py`, `contracts/tests/test_staking_contract.py`
- **Medium:** `ve_power` remained non-zero after lock expiry.
  - **Fix:** Updated `get_ve_power()` to return zero once `Global.round >= unlock_round`, and added explicit expiry regression coverage.
  - **Code:** `contracts/smart_contracts/staking/contract.py`, `contracts/tests/test_staking_contract.py`

### 4.3. Validation Status

- **Contracts:** `51 passed` via `PYTHONPATH=. poetry run pytest tests/ -v`
- **Focused security regressions (newly remediated paths):** `31 passed` via `PYTHONPATH=. poetry run pytest tests/test_agent_factory.py tests/test_sovereign_treasury.py tests/test_staking_contract.py -q`
- **Contract artifact regeneration:** completed via `poetry run python -m smart_contracts build` (updated TEAL / ARC56 / typed clients under `contracts/smart_contracts/artifacts/*`)
- **Backend:** `53 passed, 2 skipped` via `venv/bin/python -m pytest tests/ -v`
- **Airdrop tests:** `14 passed` via `venv/bin/python -m pytest scripts/test_airdrop_snapshot.py -v`

### 4.4. Residual Launch Blockers (Operational)

- Playwright runtime blocker is resolved in this environment:
  - `npm run test:e2e:admin:smoke` -> `4 passed`
  - `npx playwright test` -> `8 passed, 1 skipped`
- Live testnet smoke remains blocked until:
  - disposable trader wallet funding is completed, and
  - `DEPLOYER_MNEMONIC` is available in environment.
