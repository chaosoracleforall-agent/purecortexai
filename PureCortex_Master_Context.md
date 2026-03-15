# PURECORTEX: Master Development Context & Migration Guide

**Project vision:** Build a hardened sovereign AI agent platform on Algorand.
**Current status:** Public testnet deployment live at `https://purecortex.ai`.
**Repository:** `https://github.com/chaosoracleforall-agent/purecortexai`
**Last updated:** March 15, 2026

---

## 1. Current Snapshot
PURECORTEX is currently organized around a canonical Algorand Testnet deployment and a VM-hosted web stack. The project includes:

- A Next.js frontend for marketplace, governance, transparency, docs, and chat.
- A FastAPI backend for protocol APIs, agent routing, health, auth, and chat session minting.
- Redis-backed API key validation and short-lived WebSocket chat sessions.
- Algorand smart contracts for agent creation, governance, staking, and treasury flows.
- A tri-brain orchestration layer powered by Claude Opus 4.6, Gemini 2.5 Pro, and GPT-5.

## 2. Canonical Testnet Identifiers
- **AgentFactory app ID:** `757172168`
- **CORTEX asset ID:** `757172171`
- **Governance app ID:** `757157787`
- **Staking app ID:** `757172306`
- **Treasury app ID:** `757172354`
- **App / API URL:** `https://purecortex.ai`

These values should come from `deployment.testnet.json` and generated protocol config modules, not from ad hoc hardcoded constants.

## 3. Architecture

### 3.1. Intelligence Layer
- **Claude model:** `claude-opus-4-6`
- **Gemini model:** `gemini-2.5-pro`
- **OpenAI model:** `gpt-5`
- **OpenAI fallback:** `gpt-4.1`
- **High-risk consensus:** 2-of-3 majority
- **Low-risk behavior:** soft consensus when one valid answer is enough

### 3.2. API/Auth Layer
- Public transparency and governance reads stay unauthenticated.
- Protected REST endpoints require `X-API-Key`.
- WebSocket chat uses `POST /api/chat/session` to mint short-lived session tokens.
- Auth fails closed when the API key service is unavailable.

### 3.3. Infrastructure Layer
- **Deployment model:** GCP VM `purecortex-master`
- **Runtime:** Docker Compose + Nginx
- **TLS:** `purecortex.ai` terminated at Nginx with Let's Encrypt
- **Project ID:** `purecortexai`

## 4. What Landed Recently
- Canonicalized deployment constants via `deployment.testnet.json`.
- Switched governance UI to the live backend API until fully on-chain flows are ready.
- Added authenticated chat bootstrap and short-lived WebSocket sessions.
- Replaced placeholder REST agent chat with orchestrator-backed responses.
- Repaired the testnet smoke harness and expanded backend, contract, and Playwright coverage.
- Standardized deployment around the current VM model and cleaned stale public docs.

## 5. Remaining Priorities
1. Finish deployment/runbook polish around the VM model and operational monitoring.
2. Continue trimming stale planning-era documents that no longer reflect the active stack.
3. Improve marketplace and governance depth on top of the canonical testnet deployment.
4. Decide whether MCP will remain stdio-only or gain a documented remote transport.

---
*PURECORTEX: Keep the repo aligned with the testnet reality, not the planning-era architecture.*
