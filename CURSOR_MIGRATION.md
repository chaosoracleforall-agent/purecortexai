# PURECORTEX — Cursor Migration & Transition Document

**Created**: 2026-03-15
**Author**: David Garcia (via Claude Code)
**Purpose**: Complete knowledge transfer for continuing PURECORTEX development in Cursor IDE with Claude API, GPT-5 API, and Gemini Pro AI Ultra API.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Infrastructure & Deployment](#2-infrastructure--deployment)
3. [Backend Architecture](#3-backend-architecture)
4. [Frontend Architecture](#4-frontend-architecture)
5. [Smart Contract Architecture](#5-smart-contract-architecture)
6. [Security Infrastructure](#6-security-infrastructure)
7. [AI Agent Framework (OpenClaw)](#7-ai-agent-framework-openclaw)
8. [API Reference](#8-api-reference)
9. [All Files Reference](#9-all-files-reference)
10. [Dependencies](#10-dependencies)
11. [Work Completed](#11-work-completed)
12. [Pending Work](#12-pending-work)
13. [Security Audit Findings](#13-security-audit-findings)
14. [Critical Knowledge](#14-critical-knowledge)
15. [Cursor IDE Setup](#15-cursor-ide-setup)

---

## 1. Project Overview

**PURECORTEX** is a sovereign AI agent launchpad on Algorand — "Virtuals.io of Algorand" with:

- **Tri-Brain Consensus**: Claude Opus 4.6 + Gemini 2.5 Pro + GPT-5 evaluate every agent action. High-risk actions require 2-of-3 majority. Fail-closed if all disagree.
- **Bonding Curve Token Factory**: Agents are tokenized with quadratic bonding curves. Users buy/sell agent tokens with ALGO. Graduated agents move to AMM liquidity.
- **On-Chain Governance**: Senator AI drafts proposals from metrics analysis, Curator AI reviews for constitutional compliance, veCORTEX holders vote with time-locked boost.
- **Enterprise GPG Encryption**: Inter-agent secrets encrypted with Ed25519/Curve25519 keypairs. Transaction signing in isolated subprocess (private keys never in main process).
- **Revenue Model**: 90% protocol revenue → buyback-burn CORTEX (deflationary), 10% → operations.

| Attribute | Value |
|-----------|-------|
| GitHub | `https://github.com/chaosoracleforall-agent/purecortexai` |
| GitHub Account | `chaosoracleforall@gmail.com` |
| GCP Project | `purecortexai` (506678981456) |
| GCP Org | 955455623441 |
| Domain | `purecortex.ai` (served behind managed DNS and HTTPS) |
| VM | `purecortex-master` (e2-standard-4, us-central1-a) |
| Network | Algorand Testnet |
| TGE | March 31, 2026 |
| SSL | Let's Encrypt, expires 2026-06-12 |

---

## 2. Infrastructure & Deployment

### VM Access
```bash
# SSH via IAP tunnel (direct SSH blocked by firewall)
gcloud compute ssh purecortex-master --zone=us-central1-a --project=purecortexai --tunnel-through-iap

# Alternative access should continue to use the managed GCP SSH path above; do not document raw public IP access in tracked docs.
```

### Docker Compose Architecture
```
┌─────────────────────────────────────────────────────────────┐
│                    docker-compose.yml                         │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌─────────┐  :80/:443   ┌──────────┐  :3000                │
│  │  nginx   │ ──────────► │ frontend │                       │
│  │  :80/443 │             └──────────┘                       │
│  │  (proxy) │  :8000                                          │
│  │          │ ──────────► ┌──────────┐  :6379  ┌──────────┐ │
│  └─────────┘              │ backend  │ ──────► │  redis   │ │
│                           └──────────┘         └──────────┘ │
│                                                               │
│  Networks:                                                    │
│    proxy:    nginx, frontend, backend (external)             │
│    internal: backend, redis (isolated, no external access)   │
├─────────────────────────────────────────────────────────────┤
│  Volumes: redis_data (persistent AOF)                        │
└─────────────────────────────────────────────────────────────┘
```

### Deploy Process
```bash
# 1. Build locally or on VM
cd ~/PureCortex
docker-compose build

# 2. Start all services
docker-compose up -d

# 3. Verify
curl https://purecortex.ai/health
docker-compose ps
docker-compose logs -f backend
```

### Key Infrastructure Files
- `docker-compose.yml` — Service definitions, networks, volumes, resource limits
- `nginx.conf` — SSL termination, proxy rules, security headers, WebSocket upgrade
- `backend/Dockerfile` — Python 3.12-slim, gnupg, non-root user
- `frontend/Dockerfile` — Next.js production build
- `.env` on VM at `~/PureCortex/.env` (chmod 600, not in git)

### Security Hardening Applied
- Backend container: `no-new-privileges`, `cap_drop: ALL`, tmpfs /tmp
- Redis: password required, internal network only, AOF persistence
- Nginx: HSTS, X-Frame-Options DENY, CSP, AEAD-only ciphers
- SSH: IAP tunnel only, no direct SSH

---

## 3. Backend Architecture

### Entry Point: `backend/main.py`

```python
# Lifespan sequence:
# 1. Connect Redis cache
# 2. Initialize API key auth (Redis-backed)
# 3. Register APIKeyMiddleware
# 4. Start Agent Orchestration Loop (Senator, Curator, Social)
#    - Connect agent memories
#    - Initialize GPG + signing vaults
#    - Create background tasks
# 5. yield (app running)
# 6. Stop agent loop (cancel tasks, cleanup crypto, disconnect memories)
# 7. Disconnect cache and Redis
```

### Tri-Brain Consensus: `backend/orchestrator.py`

The `ConsensusOrchestrator` class:
1. Initializes Claude (Anthropic), Gemini (Google), GPT-5 (OpenAI) clients from Secret Manager
2. Runs all 3 in parallel via `asyncio.gather`
3. Evaluates consensus:
   - 3/3 unanimous → accept
   - 2/3 majority → accept (blocked if dissenter proposes conflicting high-risk)
   - Soft consensus for low-risk (POST/REPLY/MONITOR)
   - Otherwise → fail-closed (returns None)

**High-risk actions**: SWAP, PROPOSE, EXECUTE, CANCEL, APPROVE, REJECT
**Low-risk actions**: POST, REPLY, MONITOR, NONE

### Permission Sandboxing: `backend/sandboxing.py`

```python
class PermissionTier(Enum):
    READ_ONLY = 0        # Can only read data
    SOCIAL_POST = 1      # Can post to social media
    ASSET_MGMT = 2       # Can create/manage assets
    TREASURY_SWAP = 3    # Can execute treasury operations
```

Each agent has a declared tier. Actions are validated against the tier before execution. Escalation requires the `SANDBOX_ESCALATION_TOKEN` (HMAC-verified).

### Service Layer

| Service | File | Purpose |
|---------|------|---------|
| Algorand | `src/services/algorand.py` | AlgoNode indexer queries (apps, assets, accounts, txns) |
| API Keys | `src/services/api_keys.py` | SHA-256 hashed keys, tiered rate limits (free: 30/min, paid: 300/min) |
| Cache | `src/services/cache.py` | Redis cache with TTL decorators |
| GPG Crypto | `src/services/gpg_crypto.py` | Per-agent GPG keyring, encrypt/decrypt/sign/verify |
| Signing Vault | `src/services/signing_vault.py` | Isolated subprocess for Algorand transaction signing |

### Agent Memory: `src/agents/memory.py`

Redis-backed with three tiers:
- **Short-term** (1h TTL): Recent context for current conversation
- **Long-term** (permanent): Learned patterns, successful strategies
- **Episodic** (90-day TTL): {action, context, outcome, score} for each decision

Agents retrieve relevant past episodes to inform future decisions (few-shot learning).

---

## 4. Frontend Architecture

### Next.js 16 App Router

```
frontend/src/app/
├── page.tsx                    # Landing page (redirects to /marketplace)
├── layout.tsx                  # Root layout, metadata, fonts, Providers
├── globals.css                 # Tailwind 4 + theme variables
├── sitemap.ts                  # SEO sitemap generation
├── (dashboard)/                # Authenticated route group
│   ├── layout.tsx              # Nav header, wallet button, mobile menu
│   ├── marketplace/page.tsx    # Agent discovery + bonding curve trading
│   ├── chat/page.tsx           # WebSocket tri-brain chat
│   ├── governance/page.tsx     # Constitution, proposals, voting
│   └── transparency/page.tsx   # Supply, treasury, burn history
└── docs/
    ├── layout.tsx              # Doc sidebar
    └── [slug]/page.tsx         # Dynamic markdown rendering
```

### Key Components

| Component | Lines | Purpose |
|-----------|-------|---------|
| `Marketplace.tsx` | 367 | Agent cards, bonding curve visualization, buy/sell modal |
| `Chat.tsx` | 201 | WebSocket client, message history, typing indicators |
| `WalletButton.tsx` | 163 | Multi-wallet connect (Pera, Defly, Lute, WalletConnect) |
| `LandingPage.tsx` | 170 | Hero section, features, benefits, CTA |
| `Providers.tsx` | 28 | WalletProvider + state wrappers |
| `Logo.tsx` | 33 | Atomic Neuron logo SVG |

### Key Libraries

| Module | Purpose |
|--------|---------|
| `lib/algorand.ts` | algosdk client, asset/account queries, opt-in transactions |
| `lib/marketplace.ts` | Bonding curve math, price calculation, locked liquidity |
| `lib/transactions.ts` | Transaction builders (create agent, buy/sell tokens, stake) |
| `lib/docs.ts` | Markdown loading + rendering (remark/rehype pipeline with sanitization) |
| `hooks/useMarketplace.ts` | Market state management, bonding curve calculations |

### Styling
- **Tailwind CSS 4** with PostCSS plugin
- **Theme**: Obsidian (#050505) background, Neural Blue (#007AFF) accent
- **Fonts**: Inter (body), JetBrains Mono (code)
- **Animations**: Framer Motion for transitions and interactions
- **Charts**: Recharts for transparency visualizations

---

## 5. Smart Contract Architecture

All contracts use Algorand's **Puya** compiler (algopy) targeting AVM (Algorand Virtual Machine). Contracts follow **ARC4** standard for ABI compatibility.

### AgentFactory (`contracts/smart_contracts/agent_factory/contract.py`)

The core contract. Creates the master $CORTEX token and manages agent token lifecycle.

**State:**
```python
agent_supplies = BoxMap(UInt64, UInt64, key_prefix=b"")  # asset_id → supply
cortex_token = UInt64(0)       # Master CORTEX asset ID
latest_asset_id = UInt64(0)    # Highest created agent token
BASE_PRICE = UInt64(10_000)    # Bonding curve base (microalgos)
SLOPE = UInt64(1_000)          # Bonding curve slope
buy_fee_bps = UInt64(100)      # 1% buy fee
sell_fee_bps = UInt64(200)     # 2% sell fee
creation_fee = UInt64(100_000_000)  # 100 CORTEX creation fee
GRADUATION_THRESHOLD = UInt64(50_000_000_000)  # 50K CORTEX
MAX_TX_AMOUNT = UInt64(100_000_000_000)  # Overflow protection
```

**Methods:**
- `bootstrap_protocol()` — Creates CORTEX token (creator only, one-time)
- `create_agent(cortex_payment, name, unit_name)` — Creates new agent token
- `buy_token(payment, asset)` — Buy via bonding curve
- `sell_token(token_transfer, asset)` — Sell via bonding curve
- `distribute_cortex(receiver, amount)` — Community distribution (creator only)
- `graduate_agent(asset_id)` — Move to AMM when threshold reached

**CRITICAL NOTE**: `BoxMap` MUST use explicit `key_prefix`. The default prefix is the variable name, which causes `op.Box.get()` mismatches. This was the #1 critical bug — buys were always priced at supply=0 and sells always reverted.

### GovernanceContract (`contracts/smart_contracts/governance/contract.py`)

**Methods:**
- `initialize(staking_app)` — Link to VeCortexStaking (creator only)
- `create_proposal(title, description, proposal_type)` — Submit proposal
- `vote(proposal_id, vote, signer)` — veCORTEX-weighted vote
- `execute(proposal_id)` — Execute after timelock
- `finalize_voting(proposal_id)` — Close voting period

**Lifecycle:** Discussion (48h) → Voting (5d) → Timelock (7d) → Execution
**Thresholds:** 25% quorum, 67% supermajority

### VeCortexStaking (`contracts/smart_contracts/staking/contract.py`)

**State:**
```python
stakes = BoxMap(Bytes, Bytes, key_prefix=b"s")       # account → stake data
delegations = BoxMap(Bytes, Bytes, key_prefix=b"d")   # account → delegate
total_staked = UInt64(0)
reward_pool = UInt64(0)
```

**Methods:**
- `initialize(cortex_asset)` — Opt into CORTEX (creator only)
- `stake(payment, lock_days)` — Lock CORTEX, get veCORTEX power
- `unstake(signer)` — Withdraw after lock expires
- `delegate(delegate_address)` — Delegate voting power

### SovereignTreasury (`contracts/smart_contracts/sovereign_treasury/contract.py`)

**Methods:**
- `process_revenue()` — Split incoming revenue 90/10 (creator only)
- `swap_for_buyback(payment, amount_out_min)` — Buy CORTEX with revenue
- `execute_burn(amount)` — Burn CORTEX permanently

### Deployed Contract IDs (Testnet)
| Contract | App ID |
|----------|--------|
| AgentFactory | 757172168 |
| GovernanceContract | 757157787 |
| VeCortexStaking | 757172306 |
| SovereignTreasury | 757172354 |
| CORTEX Token | Asset ID 757172171 |

---

## 6. Security Infrastructure

### GPG Key Hierarchy

```
LOCAL MACHINE (David's Mac)
├── deployer@purecortex.ai (Ed25519, no passphrase) — Key ID 8DC1321A19192223
└── Full keyring, can decrypt all

VM (purecortex-master)
├── vm@purecortex.ai (Ed25519, passphrase) — Key ID 34FA86D2FA535C19
└── Decrypts secrets at runtime

AGENTS (backend containers)
├── agent@purecortex.ai (shared) — Key ID 7C05CD31FB248111
├── senator@purecortex.ai — Key ID 7156CA4D37077505
├── curator@purecortex.ai — Key ID 608011AF5B4D2DC5
└── social@purecortex.ai — Key ID 538709130CF8950E
```

All keys: Ed25519 + Curve25519 (ECDH), expire 2027-03-15. Stored in GCP Secret Manager.

### GCP Secret Manager (13 secrets)

| Secret | Purpose |
|--------|---------|
| `PURECORTEX_DEPLOYER_MNEMONIC_GPG` | GPG-encrypted Algorand mnemonic |
| `PURECORTEX_AGENT_GPG_SECRET_KEY` | Agent private key (armored) |
| `PURECORTEX_AGENT_GPG_PASSPHRASE` | Agent key passphrase |
| `PURECORTEX_SENATOR_GPG_SECRET_KEY` | Senator private key |
| `PURECORTEX_SENATOR_GPG_PASSPHRASE` | Senator passphrase |
| `PURECORTEX_CURATOR_GPG_SECRET_KEY` | Curator private key |
| `PURECORTEX_CURATOR_GPG_PASSPHRASE` | Curator passphrase |
| `PURECORTEX_SOCIAL_GPG_SECRET_KEY` | Social private key |
| `PURECORTEX_SOCIAL_GPG_PASSPHRASE` | Social passphrase |
| `PURECORTEX_VM_GPG_SECRET_KEY` | VM private key |
| `PURECORTEX_VM_GPG_PASSPHRASE` | VM passphrase |
| `PURECORTEX_GPG_PUBLIC_KEYS` | All public keys (armored) |
| `PURECORTEX_DEPLOYER_MNEMONIC` | DEPRECATED (use GPG version) |

### Signing Vault Protocol

```
Main Process (has network)        Signing Vault (isolated subprocess)
┌──────────────────────┐         ┌────────────────────────────┐
│ 1. Build unsigned txn │         │ 3. Create temp GPG keyring │
│ 2. Serialize + send   │ ──────► │ 4. Import keys             │
│                       │         │ 5. Decrypt mnemonic        │
│                       │         │ 6. Sign transaction        │
│ 8. Broadcast signed   │ ◄────── │ 7. Zero all key material   │
│    transaction        │         │    Return signed bytes     │
└──────────────────────┘         └────────────────────────────┘

Subprocess properties:
- No PYTHONPATH (prevents module injection)
- No inherited env vars (clean environment)
- No network access (no exfiltration)
- 30s timeout with cleanup on kill
- Concurrency limited to 3 simultaneous operations
- Passphrase via --passphrase-fd 0 (never CLI args)
- stderr sanitized (never exposed in error messages)
```

---

## 7. AI Agent Framework (OpenClaw)

### BaseAgent (Abstract)

Every agent inherits from `BaseAgent` which provides:

```python
class BaseAgent(ABC):
    # Core
    async def think(system_prompt, user_input, task_type) → Optional[Dict]
    async def chat(user_message) → str
    @abstractmethod async def act() → Optional[Dict]

    # GPG Encryption
    async def init_crypto() → None
    async def encrypt_to(plaintext, recipients) → str
    async def decrypt(ciphertext) → str
    async def sign_message(message) → str
    async def verify_message(signed_message) → tuple[bool, str]

    # Algorand Signing
    async def sign_transaction(unsigned_txn_bytes) → bytes
    async def sign_transaction_group(unsigned_txns) → list[bytes]

    # Lifecycle
    async def cleanup_crypto() → None
    async def get_status() → Dict
```

### Senator Agent

**Schedule:** Every 2 weeks
**Responsibilities:**
1. Gather on-chain metrics (token price, volume, governance participation)
2. Analyze metrics via tri-brain consensus
3. Draft governance proposals if warranted
4. Submit proposals on-chain

**System Prompt:** Loaded from constitution (PREAMBLE.md + ARTICLES.md) + metrics context

### Curator Agent

**Schedule:** Event-driven (triggered when Senator produces proposal) + hourly sweep
**Responsibilities:**
1. Load on-chain Constitution
2. Analyze proposal for constitutional compliance
3. Assess risks and impact
4. Produce recommendation: APPROVE/REJECT with rationale

### Social Agent

**Schedule:** Every 4 hours
**Responsibilities:**
1. Generate content about PURECORTEX ecosystem
2. Post to Twitter (@purecortexai) and Farcaster
3. Engage with community

### Orchestration Loop

The `AgentOrchestrationLoop` manages all agent lifecycles:

```python
# Startup sequence:
await senator.memory.connect()
await curator.memory.connect()
await social.memory.connect()
await senator.init_crypto()    # GPG + signing vault
await curator.init_crypto()
await social.init_crypto()

# Background tasks:
senator_loop (14 days)
social_loop (4 hours)
curator_sweep_loop (1 hour)

# Shutdown:
cancel all tasks
await agent.cleanup_crypto()   # Zero keyrings
await agent.memory.disconnect()
```

---

## 8. API Reference

### Health
```
GET /health
→ {status: "ok"|"degraded", version: "0.7.0",
   dependencies: {redis, orchestrator, agent_loop}}
```

### Transparency (Public)
```
GET /api/transparency/supply
→ {total_supply, circulating, burned, vesting, allocation[]}

GET /api/transparency/treasury
→ {assistance_fund, operations, total_revenue, revenue_split}

GET /api/transparency/burns
→ {total_burned, burn_history: [{txn_id, amount, round, timestamp}]}

GET /api/transparency/governance
→ {total_proposals, active_proposals, participation_rate, total_vecortex}
```

### Governance
```
GET /api/governance/constitution
→ {preamble, articles, preamble_status, articles_status}

POST /api/governance/proposals  [X-API-Key required]
→ {id, title, description, type, status, created_at}

GET /api/governance/proposals/{id}
→ {proposal + votes + curator_review}

POST /api/governance/proposals/{id}/vote  [X-API-Key required]
Body: {vote: 0|1, signer: "ALGO_ADDRESS"}
→ {status: "voted"}
```

### Agents
```
GET /api/agents/registry
→ {total_agents, agents: [{name, role, address, status}]}

POST /api/agents/{name}/chat  [X-API-Key required]
Body: {message: "string"}
→ {agent, response, timestamp}

GET /api/agents/{name}/activity
→ {agent, total_actions, recent_activity[]}
```

### Admin
```
POST /api/admin/keys  [X-Admin-Secret required]
Body: {owner, tier}
→ {api_key: "ctx_...", owner, tier}

POST /api/admin/keys/revoke  [X-Admin-Secret required]
Body: {api_key: "ctx_..."}
→ {status: "revoked"}
```

### WebSocket
```
WS /ws/chat?token=ctx_...
← {message: "user input"}
→ "tri-brain response text"
```

---

## 9. All Files Reference

### Backend (Python)

| File | Purpose |
|------|---------|
| `backend/main.py` | FastAPI app, lifespan, WebSocket, CORS, rate limiting |
| `backend/orchestrator.py` | Tri-brain consensus (Claude + Gemini + GPT-5) |
| `backend/sandboxing.py` | Permission tiers and action validation |
| `backend/social.py` | Twitter/Farcaster social media integration |
| `backend/mcp_server.py` | Model Context Protocol server |
| `backend/requirements.txt` | Pinned Python dependencies |
| `backend/Dockerfile` | Container image (Python 3.12-slim + gnupg) |
| `backend/src/agents/base_agent.py` | Abstract agent with tri-brain + crypto + memory |
| `backend/src/agents/senator_agent.py` | Governance analysis + proposal drafting |
| `backend/src/agents/curator_agent.py` | Constitutional compliance review |
| `backend/src/agents/social_agent.py` | Social content generation |
| `backend/src/agents/orchestrator_loop.py` | Agent lifecycle management |
| `backend/src/agents/memory.py` | Redis episodic + semantic memory |
| `backend/src/api/health.py` | Health check endpoint |
| `backend/src/api/agents_api.py` | Agent registry, chat, activity |
| `backend/src/api/governance.py` | Constitution, proposals, voting |
| `backend/src/api/transparency.py` | Supply, treasury, burn data |
| `backend/src/api/admin.py` | API key management |
| `backend/src/api/auth.py` | API key authentication middleware |
| `backend/src/services/algorand.py` | AlgoNode indexer client |
| `backend/src/services/api_keys.py` | Redis API key management |
| `backend/src/services/cache.py` | Redis caching service |
| `backend/src/services/gpg_crypto.py` | GPG encryption/decryption |
| `backend/src/services/signing_vault.py` | Isolated signing subprocess |

### Frontend (TypeScript/React)

| File | Purpose |
|------|---------|
| `frontend/src/app/page.tsx` | Landing page |
| `frontend/src/app/layout.tsx` | Root layout + metadata |
| `frontend/src/app/(dashboard)/layout.tsx` | Nav + wallet button |
| `frontend/src/app/(dashboard)/marketplace/page.tsx` | Agent marketplace |
| `frontend/src/app/(dashboard)/chat/page.tsx` | Chat interface |
| `frontend/src/app/(dashboard)/governance/page.tsx` | Governance UI |
| `frontend/src/app/(dashboard)/transparency/page.tsx` | Transparency dashboard |
| `frontend/src/app/docs/[slug]/page.tsx` | Dynamic doc pages |
| `frontend/src/components/Marketplace.tsx` | Agent cards + bonding curve |
| `frontend/src/components/Chat.tsx` | WebSocket chat |
| `frontend/src/components/WalletButton.tsx` | Multi-wallet connect |
| `frontend/src/components/LandingPage.tsx` | Hero + features |
| `frontend/src/components/Providers.tsx` | Wallet provider wrappers |
| `frontend/src/components/Logo.tsx` | Brand logo |
| `frontend/src/lib/algorand.ts` | Algorand SDK client |
| `frontend/src/lib/marketplace.ts` | Bonding curve math |
| `frontend/src/lib/transactions.ts` | Transaction builders |
| `frontend/src/lib/docs.ts` | Markdown loading + rendering |
| `frontend/src/hooks/useMarketplace.ts` | Market state hook |

### Smart Contracts (Puya/AVM)

| File | Purpose |
|------|---------|
| `contracts/smart_contracts/agent_factory/contract.py` | Bonding curve factory |
| `contracts/smart_contracts/governance/contract.py` | Proposal + voting |
| `contracts/smart_contracts/staking/contract.py` | veCORTEX staking |
| `contracts/smart_contracts/sovereign_treasury/contract.py` | Revenue treasury |
| `contracts/smart_contracts/*/deploy_config.py` | Deployment configs |
| `contracts/smart_contracts/artifacts/*/` | Generated client code |
| `contracts/tests/test_agent_factory.py` | Unit tests |
| `contracts/tests/live_testnet_verify.py` | Testnet verification |

### Infrastructure

| File | Purpose |
|------|---------|
| `docker-compose.yml` | 4-container orchestration |
| `nginx.conf` | Reverse proxy + SSL + headers |
| `.env.example` | Required environment variables |
| `.gitignore` | Comprehensive exclusions |

### Documentation

| File | Purpose |
|------|---------|
| `docs/API.md` | API reference |
| `docs/CLI.md` | CLI guide |
| `docs/MCP.md` | MCP integration |
| `docs/tokenomics/constitution/PREAMBLE.md` | Immutable preamble |
| `docs/tokenomics/constitution/ARTICLES.md` | 9 amendable articles |
| `docs/tokenomics/TOKENOMICS_SUMMARY.md` | Supply + vesting |
| `SPECIFICATION.md` | Feature specifications |
| `TECHNICAL_ROADMAP.md` | Phase roadmap |
| `SECURITY_AUDIT.md` | Security findings |
| `README.md` | Project overview |
| `BRAND_STRATEGY.md` | Brand guidelines |

---

## 10. Dependencies

### Backend (requirements.txt)
```
fastapi[all]==0.115.6
uvicorn==0.34.0
redis==5.2.1
httpx==0.28.1
anthropic==0.42.0
google-genai==1.1.0
openai==2.28.0
google-cloud-secret-manager==2.21.1
mcp==1.3.0
tweepy==4.15.0
farcaster==0.7.11
pydantic==2.10.5
python-dotenv==1.0.1
py-algorand-sdk==2.7.0
```

### Frontend (package.json — key deps)
```
next: 16.1.6
react: 19.2.3
@txnlab/use-wallet-react: 4.6.0
algosdk: 3.5.2
tailwindcss: 4
framer-motion: 12.36.0
recharts: 3.8.0
lucide-react: 0.577.0
remark/rehype: latest (markdown pipeline)
```

### Contracts (pyproject.toml)
```
algopy (Puya compiler)
algokit-utils
py-algorand-sdk
pytest
```

---

## 11. Work Completed

### Phase 1: Fix Broken Website Features (2026-03-14) ✅
- Layout metadata (title, OG tags, fonts)
- Dynamic doc pages at `/docs/[slug]`
- Multi-wallet support (Pera, Defly, Lute, WalletConnect)
- WebSocket URL fix (localhost → production)
- Backend ConnectionManager, CORS, health endpoint

### Phase 2: New Website Pages (2026-03-14) ✅
- Multi-page App Router refactor
- Transparency page (supply, treasury, burns)
- Governance page (constitution, proposals, voting)

### Phase 3: Backend API Expansion (2026-03-14) ✅
- Restructured into `src/api/`, `src/agents/`, `src/services/`
- Algorand service layer, transparency API, governance API
- Redis caching with TTL decorators

### Phase 4: AI Agent Architecture (2026-03-14) ✅
- Base agent framework with tri-brain consensus
- Senator, Curator, Social agents with conversational AI
- Redis episodic memory with feedback loops
- Agent API endpoints and orchestration loop

### Phase 5: Smart Contract Expansion (2026-03-14) ✅
- AgentFactory v2 (buy/sell tokens, graduation)
- VeCortexStaking (lock 7-1460 days, 1-2.5x boost)
- SovereignTreasury (90/10 buyback-burn/ops)
- GovernanceContract (proposals, voting, finalization)

### Phase 6: Infrastructure & Deployment (2026-03-14) ✅
- Nginx proxy with HTTPS, security headers
- Docker Compose with 4 containers
- SSL via Let's Encrypt

### Brand Rename (2026-03-15) ✅
- ~500 instances renamed from "PureCortex" to "PURECORTEX"

### Security Audit #1 (2026-03-15) ✅
- 79 findings (10 CRITICAL, 20 HIGH, 28 MEDIUM, 21 LOW)
- All CRITICAL and HIGH fixed
- See section 13 for details

### GPG Infrastructure (2026-03-15) ✅
- 6 Ed25519/Curve25519 keypairs generated
- Keys deployed to GCP Secret Manager
- Per-agent GPG keys with isolated keyrings
- Inter-agent encryption tested

### Signing Vault (2026-03-15) ✅
- Isolated subprocess implementation
- Tested with real Algorand testnet transaction (TxID: U5H6TX2SLEAKJL5GTBBPRPZLRHPF7Q3POXAFCK65HRAKLI2PL47Q, round 61457069)
- Wired into all agents via base_agent.py

### Penetration Test (2026-03-15) ✅
- 28 findings (4 CRITICAL, 6 HIGH, 10 MEDIUM, 5 LOW, 2 INFO)
- All CRITICAL and HIGH fixed (see section 13)

---

## 12. Pending Work

### High Priority (Before TGE March 31)
1. **Marketplace real data** (Phase 2D): Replace hardcoded `AGENTS_DATA` in `Marketplace.tsx` with live indexer queries to AgentFactory contract
2. **Launch Agent modal** (Phase 2E): Wire "Initialize Emancipation" to compose real transactions (CORTEX transfer + create_agent ABI call)
3. **Canonical testnet deployment hardening**: Complete the final smoke, monitoring, and rollback checks on the current testnet contracts
4. **Deploy latest security fixes to VM**: Current VM deployment is pre-audit

### Medium Priority
5. **Remaining pen test findings**: PEN-002 (string immutability), PEN-004 (env var fallbacks), PEN-016 (hardcode GCP project ID), PEN-021 (WS token in URL)
6. **Agent account management**: Generate dedicated Algorand accounts per agent, fund from treasury
7. **Tinyman LP integration**: Graduation mechanism sends liquidity to Tinyman AMM

### Lower Priority
8. **Testnet monitoring**: Grafana dashboard for contract state, agent health
9. **MCP server expansion**: More tools for cross-agent discovery
10. **Social media analytics**: Track engagement metrics, optimize content

---

## 13. Security Audit Findings

### Audit #1 — Code Review (2026-03-15)

**Smart Contracts (4 CRITICAL, 7 HIGH fixed):**
- BoxMap `key_prefix=b""` fix (was the #1 bug — broke all buys/sells)
- Integer overflow protection (MAX_TX_AMOUNT cap)
- Box initialization in create_agent
- Strict equality on payment amounts
- Minimum fee bounds, distribution caps
- Governance quorum, vote validation, proposal type validation
- Staking BoxMap prefix fix (b"s"/b"d")
- Treasury creator-only access control

**Backend (3 CRITICAL, 5 HIGH fixed):**
- API key auth system (SHA-256, Redis-backed)
- Auth middleware on POST/PUT/DELETE
- WebSocket auth, Redis rate limiting
- Environment-aware CORS
- Governance race condition (WATCH/MULTI/EXEC)
- Gemini prompt injection fix
- Path traversal guard, mnemonic not cached

**Frontend (3 HIGH, 6 MEDIUM fixed):**
- Path traversal in doc loading
- XSS via rehype-sanitize
- BigInt safety, security headers

**Infrastructure (3 CRITICAL, 5 HIGH fixed):**
- .gitignore expansion
- Redis health check, nginx CSP
- Dockerfile hardening

### Audit #2 — Penetration Test (2026-03-15)

**Fixed (4 CRITICAL, 6 HIGH):**
- PEN-001: GPG passphrase via `--passphrase-fd 0` (not CLI arg)
- PEN-003: Passphrase no longer cached in GPGCrypto instance
- PEN-005: Temp file cleanup
- PEN-006: PYTHONPATH removed from clean env
- PEN-007: Orphaned temp dir cleanup on timeout
- PEN-008: Sender verification in group signing
- PEN-009: Stderr sanitized in error messages
- PEN-010: Concurrency semaphore (max 3)
- PEN-013: Identity-specific key lookup in create_agent_gpg
- PEN-019: Removed blanket GET passthrough
- PEN-020: hmac.compare_digest for admin secret
- PEN-022: APIKeyMiddleware registered with app
- PEN-025: Docker no-new-privileges + cap_drop ALL
- PEN-026: gnupg installed in container

**Remaining (acceptable risk for testnet):**
- PEN-002: Python string immutability (mitigated by subprocess short lifetime)
- PEN-004: Env var fallbacks (disable for mainnet)
- PEN-011: Same-UID temp dir access (short window)
- PEN-012: Trust model always (keys pre-trusted at init)
- PEN-016: GCP project ID via env (hardcode for mainnet)
- PEN-021: WS token in query params
- PEN-028: CSP unsafe-inline (Next.js requirement)

---

## 14. Critical Knowledge

### Things That Will Break If You Change Them Wrong

1. **BoxMap key_prefix**: MUST be explicit. Default prefix is the Python variable name, causing `op.Box.get()` mismatches. Always use `key_prefix=b""` or `key_prefix=b"x"`.

2. **Bonding curve overflow**: `amount * amount` overflows uint64 near 1e9. That's why MAX_TX_AMOUNT exists (100K tokens per tx).

3. **GPG passphrase passing**: MUST use `--passphrase-fd 0` (stdin). Never `--passphrase` (exposed in `/proc/PID/cmdline`).

4. **Docker networks**: Redis is on `internal` (isolated). Backend is on both `internal` and `proxy`. Frontend is only on `proxy`. Breaking this isolation exposes Redis.

5. **Algorand mnemonic**: The mnemonic in `contracts/.env` is testnet-only. The production mnemonic is GPG-encrypted in Secret Manager as `PURECORTEX_DEPLOYER_MNEMONIC_GPG`. Never store plaintext mnemonics in production.

6. **VM SSH**: Direct SSH times out. Must use `--tunnel-through-iap` flag or IAP tunnel.

7. **Docker on VM**: Uses `docker-compose` (hyphenated, v1), not `docker compose` (v2).

8. **create_agent_gpg**: Now uses identity-specific key lookup. If you add a new agent, you must add its key/passphrase secrets to the `key_secret_map` and `passphrase_map` dictionaries.

9. **SigningVault.initialize()**: Stores encrypted materials, not decrypted. Actual decryption only happens inside the subprocess. Don't try to decrypt in the main process.

10. **Redis WATCH/MULTI/EXEC**: Governance voting uses optimistic locking with 3 retries. If you add new concurrent write operations, use the same pattern.

### Algorand Accounts

| Role | Address | Notes |
|------|---------|-------|
| New Deployer | R7CLPM...XMWI | ~6.62 ALGO, active, mnemonic GPG-encrypted |
| Old Deployer | 2AB6YA...B3XA | 2.32 ALGO (locked), mnemonic rotated |

### Contract Interaction Pattern (from frontend)
```typescript
// 1. Build transaction
const txn = buildBuyTokensTxn(assetId, amount, suggestedParams);
// 2. Sign via wallet SDK
const signedTxns = await signTransactions([txn]);
// 3. Submit to network
const result = await algodClient.sendRawTransaction(signedTxns).do();
```

### Contract Interaction Pattern (from backend agent)
```python
# 1. Build unsigned transaction (main process)
unsigned_txn = build_transaction(...)
unsigned_bytes = encoding.msgpack_encode(unsigned_txn)

# 2. Sign in isolated vault (subprocess)
signed_bytes = await self.sign_transaction(unsigned_bytes)

# 3. Broadcast (main process)
txid = algod_client.send_raw_transaction(signed_bytes)
```

---

## 15. Cursor IDE Setup

### 1. Install Cursor Rules
The `.cursorrules` file is already created at `PureCortex/.cursorrules`. Cursor will automatically load it.

### 2. Workspace Configuration
Open the PureCortex directory as the workspace root. The project has three main working directories:
- `frontend/` — TypeScript/React (Next.js)
- `backend/` — Python (FastAPI)
- `contracts/` — Python (Puya/algopy)

### 3. AI Model Configuration
Configure Cursor to use these models for different tasks:

| Task | Recommended Model | Reason |
|------|-------------------|--------|
| Code generation | Claude Opus 4.6 | Best at Python/TS, understands complex architectures |
| Code review | GPT-5 | Strong at spotting logic errors and edge cases |
| Documentation | Gemini 2.5 Pro | Good at structured documentation and analysis |
| Debugging | Claude Opus 4.6 | Best at reading stack traces and understanding async code |
| Smart contracts | Claude Opus 4.6 | Understands algopy/Puya, ARC4, AVM constraints |

### 4. Required Extensions
- Python (Pylance)
- ESLint
- Tailwind CSS IntelliSense
- Docker
- TOML

### 5. Environment Setup
```bash
# Backend
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend && npm install

# Contracts
cd contracts && poetry install

# Copy environment variables
cp .env.example .env  # Then fill in actual values
```

### 6. Running Locally
```bash
# Terminal 1: Redis
docker run -d -p 6379:6379 redis:7.2-alpine redis-server --requirepass devpassword

# Terminal 2: Backend
cd backend && REDIS_URL=redis://:devpassword@localhost:6379/0 uvicorn main:app --reload

# Terminal 3: Frontend
cd frontend && npm run dev
```

---

*End of migration document. This file captures the complete state of PURECORTEX as of 2026-03-15.*
