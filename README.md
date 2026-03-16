# PURECORTEX

PURECORTEX is a sovereign AI agent launchpad and operating surface on Algorand Testnet. The current stack combines Algorand smart contracts, a FastAPI backend, a Next.js frontend, Redis-backed auth/session services, and a tri-brain orchestration layer for agent chat, governance, and marketplace flows.

## Current Status
- **App:** [https://purecortex.ai](https://purecortex.ai)
- **Health:** [https://purecortex.ai/health](https://purecortex.ai/health)
- **Network:** Algorand Testnet
- **Repository:** [chaosoracleforall-agent/purecortexai](https://github.com/chaosoracleforall-agent/purecortexai)
- **Factory App ID:** `757172168`
- **CORTEX Asset ID:** `757172171`

## Tri-Brain Orchestration
PURECORTEX uses OpenClaw to run parallel model inference across:
- **Claude Opus 4.6**
- **Gemini 2.5 Pro**
- **GPT-5** with `gpt-4.1` fallback support configured through environment variables

High-risk actions use **2-of-3 majority consensus**. Lower-risk conversational flows can degrade to soft consensus when a single valid model response is sufficient.

## What Is Live In This Repo
- **Smart contracts:** AgentFactory, governance, staking, and treasury contracts for Algorand Testnet.
- **Backend:** FastAPI APIs for transparency, governance, agent registry/chat, health, admin bootstrap, and chat session minting.
- **Frontend:** Marketplace, governance, transparency, docs, and chat UX at `purecortex.ai`.
- **Security/auth:** `X-API-Key` protected REST flows, short-lived WebSocket chat sessions, and fail-closed auth behavior on Redis outage.
- **Testing:** Backend pytest coverage, contract tests, Playwright E2E coverage, and a documented testnet smoke harness.

## Local Development
1. Copy `.env.example` to `.env` and fill in required keys.
2. Backend: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`
3. Frontend: `cd frontend && npm install`
4. Contracts: `cd contracts && poetry install`

Useful local commands:
- Backend API: `cd backend && .venv/bin/python -m uvicorn main:app --reload`
- Frontend app: `cd frontend && npm run dev`
- Backend tests: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest`
- Frontend E2E: `cd frontend && npm run test:e2e`

## Deployment
PURECORTEX currently deploys to the `purecortex-master` GCP VM using the root `docker-compose.yml` stack and `nginx.conf`.

- Workstation deploy: `bash scripts/deploy_remote_vm.sh --pull`
- On-VM deploy: `bash scripts/deploy_vm.sh --pull`
- Runbook: [DEPLOYMENT.md](./DEPLOYMENT.md)

## Key Docs
- [DEPLOYMENT.md](./DEPLOYMENT.md)
- [docs/ENTERPRISE_DEVELOPER_ACCESS_SPEC.md](./docs/ENTERPRISE_DEVELOPER_ACCESS_SPEC.md)
- [docs/API.md](./docs/API.md)
- [docs/CLI.md](./docs/CLI.md)
- [docs/MCP.md](./docs/MCP.md)
- [SECURITY_AUDIT.md](./SECURITY_AUDIT.md)
- [VERIFICATION_CERTIFICATE.md](./VERIFICATION_CERTIFICATE.md)
