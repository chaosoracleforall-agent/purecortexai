# PURECORTEX

[![Admin E2E Mocked](https://github.com/chaosoracleforall-agent/purecortexai/actions/workflows/admin-e2e-mocked.yml/badge.svg)](https://github.com/chaosoracleforall-agent/purecortexai/actions/workflows/admin-e2e-mocked.yml)
[![Admin E2E Live](https://github.com/chaosoracleforall-agent/purecortexai/actions/workflows/admin-e2e-live.yml/badge.svg)](https://github.com/chaosoracleforall-agent/purecortexai/actions/workflows/admin-e2e-live.yml)

PURECORTEX is a sovereign AI agent launchpad and operating surface on **Algorand MainNet**. The stack combines Algorand smart contracts (Puya/algopy), a FastAPI backend, a Next.js 16 frontend, Redis-backed auth/session services, and a tri-brain orchestration layer (Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5) for agent chat, governance, and marketplace flows.

## Current Status
- **App:** [https://purecortex.ai](https://purecortex.ai)
- **Health:** [https://purecortex.ai/health](https://purecortex.ai/health)
- **Network:** Algorand MainNet (TGE: March 31, 2026)
- **Token:** $CORTEX (ASA `3501164627`) — 10 quadrillion supply, 6 decimals
- **Version:** 0.9.3
- **Social:** [@purecortexai](https://x.com/purecortexai) on X

### MainNet Contracts

| Contract | App ID | Purpose |
|----------|--------|---------|
| AgentFactory | `3501164435` | Bonding curve token factory, agent creation, buy/sell, graduation |
| Governance | `3501164276` | Proposal lifecycle, discussion, voting, timelock, execution |
| VeCortexStaking | `3501164346` | Lock CORTEX, earn veCORTEX, delegate to Lawmakers |
| SovereignTreasury | `3501164386` | Revenue split: 90% buyback-burn, 10% operations |
| CreatorVesting | `3501164479` | 10% TGE release, 90% linear daily vest over 180 days |
| AirdropClaim | `3502246857` | Merkle-proof airdrop claims with deadline enforcement |

### DEX Liquidity

| DEX | CORTEX | ALGO |
|-----|--------|------|
| Tinyman V2 (60%) | 900B | 6,600 |
| Pact (40%) | 600B | 4,400 |

### Treasury
- **Operations multisig:** `PBOHX6V6PEV4BBPJVZ77BUS2LHQ2YRT4T7WRFQRZFHZI3ZEADXVMZGSFZE` (2-of-3)
- **Revenue model:** 90% buyback-burn via Assistance Fund, 10% operations

## Tri-Brain Orchestration
Parallel model inference across:
- **Claude Opus 4.6** — primary reasoning
- **Gemini 2.5 Pro** — secondary validation
- **GPT-5** with `gpt-4.1` fallback

High-risk actions use **2-of-3 majority consensus** (fail-closed). Lower-risk conversational flows can degrade to soft consensus. Input sanitization with 8KB cap, control character stripping, and prompt injection detection.

## What Is Live
- **Smart contracts:** 6 contracts deployed on Algorand MainNet with bonding curves, governance, staking, treasury, vesting, and airdrop claims.
- **Backend:** FastAPI APIs for transparency, governance, agent registry/chat, health, admin bootstrap, developer access, and airdrop eligibility.
- **Frontend:** Marketplace, governance, transparency, airdrop, docs, and chat UX at `purecortex.ai`.
- **AI Agents:** Senator (governance analyst), Curator (constitutional compliance), Social (X/Twitter community engagement) — all running autonomously.
- **Security/auth:** `X-API-Key` protected REST flows, short-lived WebSocket chat sessions, fail-closed auth, isolated signer daemon (no network, read-only FS), reCAPTCHA Enterprise on developer access.
- **Testing:** 115+ tests (51 contracts + 56 backend + 8 E2E + 12 campaign).

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
- Admin E2E smoke: `cd frontend && npm run test:e2e:admin:smoke`

Live admin smoke options:
- Mocked-only admin coverage runs by default through `npm run test:e2e:admin:smoke`.
- Add `PURECORTEX_RUN_LIVE_ADMIN_E2E=1` to include the real browser flow against a live backend.
- Override `PURECORTEX_E2E_BACKEND_URL`, `PURECORTEX_ADMIN_E2E_AUTH_MODE`, and `PURECORTEX_ADMIN_E2E_EMAIL` when pointing the live test at a different local or staging environment.
- `PURECORTEX_ADMIN_E2E_AUTH_MODE` accepts `dev-session` or `header`; the GitHub Actions workflow dispatch now exposes the same choice for stricter live runs.

## CI
- `Admin E2E Mocked` runs automatically on pull requests and pushes that touch the admin/browser smoke coverage paths.
- `Admin E2E Live` is manual-only and should be launched from GitHub Actions when you want a real browser pass against the CI-started local stack.
- Use `dev-session` for the default live run, or choose `header` when you want stricter trusted-header coverage for the admin surface.

## Deployment

PURECORTEX runs on two isolated GCP VMs in `us-central1-a` (project: `purecortexai`):

| VM | Purpose | Stack |
|----|---------|-------|
| `purecortex-mainnet` | **Production** (MainNet) | Docker Compose + `nginx.mainnet.conf` |
| `purecortex-master` | Testnet / staging | Docker Compose + `nginx.conf` |

Deploy to mainnet:
```bash
PURECORTEX_GCP_INSTANCE=purecortex-mainnet bash scripts/deploy_remote_vm.sh --pull
```

Deploy to testnet:
```bash
bash scripts/deploy_remote_vm.sh --pull
```

Runbook: [DEPLOYMENT.md](./DEPLOYMENT.md)

## Key Docs
- [DEPLOYMENT.md](./DEPLOYMENT.md) — Deployment runbook and security flags
- [MAINNET_LAUNCH_CHECKLIST.md](./MAINNET_LAUNCH_CHECKLIST.md) — TGE checklist
- [SECURITY_AUDIT.md](./SECURITY_AUDIT.md) — Internal security audit findings
- [SECURITY_AUDIT_REPORT.md](./SECURITY_AUDIT_REPORT.md) — Comprehensive audit report
- [docs/OUTREACH.md](./docs/OUTREACH.md) — Audit firm, partnership, and Immunefi outreach
- [docs/IMMUNEFI_BOUNTY_SPEC.md](./docs/IMMUNEFI_BOUNTY_SPEC.md) — Bug bounty program spec
- [docs/ENTERPRISE_DEVELOPER_ACCESS_SPEC.md](./docs/ENTERPRISE_DEVELOPER_ACCESS_SPEC.md) — Developer access API
- [docs/API.md](./docs/API.md) — REST API reference
- [docs/CLI.md](./docs/CLI.md) — CLI reference
- [docs/MCP.md](./docs/MCP.md) — MCP server reference
- [CHANGELOG.md](./CHANGELOG.md) — Version history
