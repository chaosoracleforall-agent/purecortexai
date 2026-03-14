# PureCortex: Master Development Context & Migration Guide 🦞

**Project Vision:** Build a superior, hardened, and sovereign alternative to Virtuals.io on the Algorand Blockchain.
**Status:** Testnet Production Live | Hardened Security Certified.
**Date:** March 13, 2026

---

## 1. Project Background & Strategy
PureCortex is a launchpad for autonomous AI agents. Unlike EVM-based alternatives, it leverages Algorand’s sub-second finality and a "Dual-Brain" consensus engine (Claude 3.5 + Gemini 1.5) orchestrated via OpenClaw. The project focuses on "Agent Emancipation"—where code becomes an independent economic actor.

## 2. Technical Architecture

### 2.1. Blockchain Layer (Algorand/Puya)
- **Master Factory:** `AgentFactory` (App ID: `757091997`).
- **Protocol Token:** `$CORTEX` (Asset ID: `757092088`).
- **Bonding Curve:** Custom hybrid quadratic integral. 
- **Sovereignty:** All administrative roles (Manager/Freeze/Clawback) are locked to the contract address itself.

### 2.2. Intelligence Layer (The Dual-Brain)
- **Engine:** Python 3.12 + FastAPI + OpenClaw.
- **Consensus:** Every critical action requires JSON-alignment between Claude and Gemini.
- **Sandboxing:** A `PermissionProxy` enforcing 4 tiers of escalation:
    - Tier 0: Read-Only (Basic Chat)
    - Tier 1: Social (Twitter/Farcaster)
    - Tier 2: Asset Management (Deploying Agents)
    - Tier 3: Treasury (ALGO/CORTEX Swaps)

### 2.3. Infrastructure (GCP)
- **Compute:** GCP VM `purecortex-master` (e2-standard-4: 4 vCPU, 16GB RAM).
- **Security:** Secret Manager for all keys; Cloud KMS for HSM-backed signing (Ready for implementation).
- **Reverse Proxy:** Nginx + Certbot (HTTPS live at https://purecortex.ai).

## 3. Completed Milestones (What We Built)
- [x] **Hardened Smart Contracts:** Precision-engineered Puya contracts with box-storage fixes.
- [x] **$CORTEX Tokenomics:** Bootstrap protocol and utility fee enforcement (100 $CORTEX/launch).
- [x] **Social Identity:** Programmatic Twitter integration for `@purecortexai`.
- [x] **High-Fidelity UI:** Next.js 15 interface with "Modern Tech" branding.
- [x] **Documentation Hub:** API, MCP, and CLI docs served statically.
- [x] **Formal Verification:** Internal audit of bonding curve monotonicity and precision.

## 4. Key Security Fixes (The Hardening Log)
1. **Mathematical Truncation:** Fixed integer division in bonding curve that allowed "free" tokens.
2. **Prompt Injection:** Implemented XML-tagged structural guardrails to prevent instruction hijacking.
3. **Unrestricted Execution:** Introduced `PermissionProxy` to stop AI from making unauthorized on-chain or social moves.
4. **Credential Safety:** Migrated all secrets from `.env` to GCP Secret Manager.

## 5. The "Modern Tech" Brand Identity
- **Concept:** Concept 1 (Modern Tech).
- **Typography:** Inter Bold (Primary), JetBrains Mono (Technical).
- **Palette:** Obsidian (#050505) and Neural Blue (#007AFF).
- **Logo:** Typographic "PureCortex" with a minimalist geometric neuron mark.

## 6. Challenge Log (Obstacles Encountered)
- **Twitter API Permissions:** Encountered "Read-only" blocks; required upgrade to "Read and Write" and token rotation.
- **Twitter PFP Validation:** Automated PFP uploads failed initially due to low entropy; required high-resolution, textured images to pass filters.
- **Algokit SDK Versioning:** Navigation of positional vs keyword arguments in `AccountManager` during deployment scripts.
- **DNS Multicasting:** Domain initially resolved to GoDaddy parked IPs, blocking Let's Encrypt SSL issuance. Resolved by purging old A-records.

## 7. Pending & Future Roadmap (Next Steps for Claude Code)
1. **Cortex Points System:** Implement an off-chain/on-chain hybrid to track Testnet engagement for the Genesis Airdrop.
2. **Mainnet Migration:** Prepare the "Point of Emancipation" transition for March 31, 2026.
3. **KMS Signing:** Replace mnemonic-based signing in `AgentFactory` with GCP Cloud KMS for institutional security.
4. **Advanced MCP Tools:** Implement `get_alpha_score` and `audit_contract_bytecode` as tools for the agents.
5. **UI Interactivity:** Enable full "Neural Search" and "Filter" logic in the Marketplace.

---
*PureCortex: Documented for the next level of intelligence.*
