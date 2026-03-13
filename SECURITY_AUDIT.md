# PureCortex: Internal Security Audit & Hardening Report 🦞

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

## 2. AI Orchestration Audit (OpenClaw/Dual-Brain)

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
