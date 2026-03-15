# PURECORTEX: Technical Roadmap & Architecture

This roadmap reflects the stack that is actually in the repository today, not the earlier planning-era GKE architecture.

## 1. Current Production-Style Testnet Architecture

### Infrastructure
- **GCP project:** `purecortexai`
- **Deployment target:** single VM, `purecortex-master`
- **Runtime:** Docker Compose + Nginx
- **Public domain:** `https://purecortex.ai`
- **Stateful dependencies:** Redis for API keys, rate limits, and chat sessions

### Application Stack
- **Frontend:** Next.js 15
- **Backend:** FastAPI
- **Contracts:** Puya/Python smart contracts targeting Algorand Testnet
- **Docs:** Mintlify docs site plus tracked markdown docs in the repo

### Tri-Brain
- **Claude:** Opus 4.6
- **Gemini:** 2.5 Pro
- **OpenAI:** GPT-5 with GPT-4.1 fallback
- **High-risk policy:** 2-of-3 majority
- **Low-risk policy:** soft consensus when one valid response is enough

## 2. What Has Already Been Hardened
- Canonical testnet deployment manifest and generated protocol config modules
- Fail-closed API auth on Redis outage
- First-admin bootstrap path and API key lifecycle support
- Authenticated WebSocket chat bootstrap via short-lived session tokens
- Backend-driven governance UI in place of premature on-chain assumptions
- Testnet smoke harness for create/buy/sell/vote validation
- Backend pytest, contract tests, and Playwright E2E coverage

## 3. Near-Term Roadmap

### Phase A: Operational Readiness
1. Improve VM deployment observability and post-deploy verification.
2. Keep tracked docs aligned with the active testnet deployment.
3. Continue cleaning up old planning-era references and speculative architecture docs.

### Phase B: Product Depth
1. Expand marketplace detail flows and test coverage around live assets.
2. Mature governance from API-backed workflows toward fully on-chain behavior when the contracts and UX are ready.
3. Clarify MCP transport strategy and publish a stable integration story if remote access becomes supported.

### Phase C: Infrastructure Evolution
1. Decide whether to stay on the VM deployment model long term or intentionally redesign for another hosting target.
2. Introduce stronger operational monitoring and rollback procedures around the canonical testnet stack.
3. Evaluate KMS-backed signing where it materially improves the current deployment without overcomplicating testnet operations.

## 4. Strategic Tools
- `get_tri_brain_consensus`
- `get_alpha_score`
- `audit_contract_bytecode`
- Additional governance and market-intelligence tools as the MCP surface matures

---
*PURECORTEX: Keep the roadmap grounded in the codebase that exists today.*
