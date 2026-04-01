# Changelog

## 0.9.1 - 2026-04-01

### Security Fixes — Smart Contracts
- **SEV-001 (HIGH):** Fixed governance flash-vote attack — added 7-day `VOTE_LOCK_PERIOD` preventing CORTEX reclaim until cooldown after voting ends. Vote lock period is snapshotted per-proposal (immutable).
- **SEV-002 (MEDIUM):** Fixed `AirdropClaim.reclaim_unclaimed` — now sets `total_claimed = total_allocated` before inner transfer, preventing repeated calls from draining excess balance.
- **SEV-003 (MEDIUM):** Added `total_claimed + amount <= total_allocated` ceiling check in `AirdropClaim.claim` to enforce the invariant on-chain regardless of Merkle tree correctness.
- **SEV-004 (MEDIUM):** Added `clear_pending_agent` creator-only method to `AgentFactory` to prevent permanent DoS on agent creation from abandoned pending agents.
- **SEV-005 (LOW):** Explicitly set `freeze=Global.zero_address` and `clawback=Global.zero_address` in `bootstrap_protocol` CORTEX ASA creation for defense-in-depth.
- **SEV-008 (LOW):** Added `cortex_transfer.sender == Txn.sender` check in `VeCortexStaking.fund_reward_pool` for consistency with other transfer-accepting methods.

### Security Fixes — Backend
- **BE-001 (HIGH):** Airdrop snapshot files are now verified via SHA-256 companion hash on load. Snapshot script generates `.sha256` integrity file. Tampered snapshots are rejected with a CRITICAL log.
- **BE-002 (HIGH):** Governance proposals are now write-through persisted to PostgreSQL. Redis remains fast-path cache; proposals survive Redis restarts. Counter re-seeds from PostgreSQL max ID to prevent ID collisions.
- **BE-003 (HIGH):** Removed `/internal/admin` from `PUBLIC_PREFIXES`. Admin endpoints now require `x-purecortex-auth-email` header (set by oauth2-proxy) to pass the API key middleware gate.

### Added
- `GovernanceProposal` SQLAlchemy model + Alembic migration `20260401_0003`.
- Updated admin endpoint tests to cover the new middleware gate.

## 0.9.0 - 2026-04-01

### Added — Social Agent Community Engagement
- **Retweet**: Social agent can now retweet relevant Algorand ecosystem content (5/day limit, score >= 7).
- **Quote Tweet**: Tri-brain-powered commentary on ecosystem tweets (3/day limit, score >= 8).
- **Like**: Lightweight engagement signal on quality community posts (10/day limit, score >= 5).
- **Mention Monitoring**: Detects @purecortexai mentions and auto-replies to high-scoring ones (5/day limit).
- **Search Discovery**: Searches for Algorand community conversations using hashtags/keywords (#Algorand, #AlgoFam, AI agents, etc.).
- New scoring function `score_engagement_candidate()` in `social_campaign.py` for retweet/like/quote decisions.
- All features independently toggleable via env vars: `SOCIAL_CAMPAIGN_AUTO_RETWEET`, `SOCIAL_CAMPAIGN_AUTO_LIKE`, `SOCIAL_CAMPAIGN_AUTO_QUOTE_TWEET`, `SOCIAL_CAMPAIGN_AUTO_MENTION_REPLY`, `SOCIAL_CAMPAIGN_SEARCH_DISCOVERY`.
- Engagement history persisted in Redis with deduplication to prevent double-actions.
- Registered `QUOTE_TWEET`, `RETWEET`, `LIKE` actions in sandboxing permission tier.

### Added — Non-Custodial Airdrop Claim Contract
- New `AirdropClaim` smart contract (`contracts/smart_contracts/airdrop_claim/contract.py`): users claim CORTEX by submitting Merkle proofs on-chain. Fully non-custodial — user pays all fees.
- On-chain Merkle proof verification using SHA256 with domain separation (0x00 leaf, 0x01 internal).
- Box storage for double-claim prevention. Claim deadline enforcement. Creator-only `reclaim_unclaimed()` after deadline.
- Updated `wallet_leaf()` encoding in `airdrop_snapshot.py` to use raw bytes matching AVM contract.
- Added `pack_proof_for_avm()` for binary proof format (33-byte packed steps).

### Added — Complete Airdrop Snapshot Tiers
- Implemented all 7 tiers in `airdrop_snapshot.py`: testnet pioneers, DeFi users, governors, NFD holders, developers, social campaign, community tasks.
- Previously only 2 of 7 tiers were implemented; now all tiers produce eligibility data.
- Snapshot output now includes per-wallet Merkle proofs (JSON + packed hex for AVM).

### Added — Airdrop Backend Endpoints
- `GET /api/airdrop/eligibility/{address}` — check wallet eligibility, allocation, and qualified tiers.
- `GET /api/airdrop/proof/{address}` — return Merkle proof for on-chain claim submission.
- Endpoints load from the most recent snapshot file in `/snapshots/`.

### Added — Frontend Claim Flow
- New claim section in Airdrop page: eligibility check, allocation display, and on-chain claim button.
- Uses `AtomicTransactionComposer` to build ABI method calls to the AirdropClaim contract.
- User signs with their connected wallet (Pera/Defly/Lute/etc.) — fully non-custodial.
- Shows transaction explorer link after successful claim.
- Gracefully handles: contract not yet deployed, claims not yet open, ineligible wallets.

## 0.8.3 - 2026-03-30

### Fixed
- Fixed checks-effects-interactions (CEI) ordering violation in `contracts/smart_contracts/sovereign_treasury/contract.py`: `execute_burn` and `withdraw_buyback_algo` now update state BEFORE inner transactions, matching the pattern used across all other contracts.

### Security
- Completed Code Review Gate (Gate 7) — all checklist items reviewed and signed off.
- Fixed all npm dependency vulnerabilities in frontend (picomatch high, brace-expansion moderate).
- Backend Python dependencies audited clean (pip-audit: 0 vulnerabilities).
- Updated `.gitignore` to exclude build bundles, GCP temp, test artifacts, and cache directories.

### Verified
- Full test suite green:
  - Contracts: 51/51 passed
  - Backend: 56/56 passed
  - Frontend E2E: 8/8 passed (1 skipped — live admin requires running instance)
  - Airdrop Merkle: 14/14 passed
- Smart contract review: all 5 contracts audited for overflow safety, auth checks, CEI pattern, assert uniqueness.
- No hardcoded secrets found across backend, frontend, or scripts (grep + pip-audit verified).
- `deployment.mainnet.json` verified: 5 app IDs non-zero, airdrop tiers sum to 100%.
- Signer daemon network isolation confirmed (`network_mode: "none"`, read-only filesystem).

### Fixed (Frontend)
- Replaced all hardcoded testnet explorer URLs (`testnet.explorer.perawallet.app`) with network-aware `EXPLORER_BASE_URL` derived from `protocolConfig.network` in Marketplace, Governance, and WalletButton components.
- Replaced hardcoded testnet Algod/Indexer API URLs in `marketplace.ts` with imports from `algorand.ts` (already network-aware).
- Removed all user-facing "testnet" text labels from Marketplace, Governance, Chat, and WalletButton components.
- Added try/catch to `WalletButton.handleDisconnect()` to handle wallet provider errors gracefully.
- Updated E2E marketplace test route patterns to match any network (mainnet or testnet).

### Fixed (Backend)
- Rate limiter now fails closed on mainnet when Redis is unavailable at startup (`main.py`) — prevents unlimited requests bypassing IP-based rate limiting.
- Airdrop registration (`POST /api/airdrop/register`) added to public POST patterns in auth middleware — end users no longer need an API key to register wallets for the genesis airdrop.

### User Action
- Recompile Treasury TEAL artifact after CEI fix: `poetry run python -m smart_contracts build`
- Remaining launch blockers: fund disposable wallet, provision DEPLOYER_MNEMONIC, run live testnet smoke.
- Populate wallet addresses in `deployment.mainnet.json` (all currently empty).
- Set `tradingEnabled: true` and `launchEnabled: true` in deployment manifest when ready.

## 0.8.2 - 2026-03-25

### Fixed
- Hardened `contracts/smart_contracts/agent_factory/contract.py` by enforcing a non-zero protocol fee floor (`MIN_FEE_BPS=1`) and added regression coverage to prevent rounding-driven zero-fee buy/sell edge exploitation.
- Hardened `contracts/smart_contracts/sovereign_treasury/contract.py` by binding referenced payment/asset-transfer transactions to the caller and enforcing strict adjacent group-index semantics in `process_revenue` and `execute_burn`.
- Hardened `contracts/smart_contracts/staking/contract.py` by adding creator-gated reward distribution (`distribute_reward`), exposing reward pool reads (`get_reward_pool`), and expiring `ve_power` once locks are past unlock round.

### Updated
- Recompiled smart contracts and regenerated canonical artifact outputs (`TEAL`, `ARC56`, typed clients) via `poetry run python -m smart_contracts build`.
- Refreshed launch security documentation to include this follow-up pass and current contract evidence:
  - `SECURITY_AUDIT.md`
  - `SECURITY_AUDIT_REPORT.md`
  - `docs/MAINNET_GO_NO_GO_PACKET_2026-03-25.md`
- Verified current contract evidence after rebuild:
  - `PYTHONPATH=. poetry run pytest tests/ -v` -> `51 passed`
  - `PYTHONPATH=. poetry run pytest tests/test_agent_factory.py tests/test_sovereign_treasury.py tests/test_staking_contract.py -q` -> `31 passed`

### Root Cause
- Follow-up triage from external-audit control mapping identified unresolved contract-level integrity controls (fee-floor precision symmetry, treasury replay/caller binding, staking reward operability, ve-power expiry) that needed implementation plus artifact/doc re-baselining.

### User Action
- Redeploy contract-dependent environments using the refreshed artifacts and rerun environment smoke checks before final mainnet go/no-go sign-off.

## 0.8.1 - 2026-03-25

### Updated
- Updated launch documentation status to mark the Playwright runtime blocker as resolved in this environment across:
  - `docs/MAINNET_GO_NO_GO_PACKET_2026-03-25.md`
  - `SECURITY_AUDIT.md`
  - `SECURITY_AUDIT_REPORT.md`
- Recorded current frontend E2E evidence in those docs:
  - `npm run test:e2e:admin:smoke` -> `4 passed`
  - `npx playwright test` -> `8 passed, 1 skipped`

### Root Cause
- Launch status documentation still reflected an earlier runtime/browser mismatch even after Playwright configuration hardening and E2E stabilization.

### User Action
- No action required for this docs-only update; continue with remaining launch blockers (`live_testnet_verify.py smoke` prerequisites).

## 0.8.0 - 2026-03-25

### Fixed
- Hardened `contracts/smart_contracts/agent_factory/contract.py` sell-fee handling to prevent underflow when gross sell value is extremely small by clamping fee application (`fee <= gross`) and only applying minimum fee when gross value is non-zero.
- Reworked graduation valuation arithmetic in `contracts/smart_contracts/agent_factory/contract.py` to an overflow-safe split-scaling path, eliminating square/multiply overflow risk at high supply values.

### Updated
- Added benchmark and traceability audit artifacts:
  - `docs/ALGOLAND_AUDIT_BENCHMARK_MATRIX.md`
  - `docs/PURECORTEX_CONTROL_TRACEABILITY.md`
  - `docs/MAINNET_GO_NO_GO_PACKET_2026-03-25.md`
- Added contract security regression coverage in:
  - `contracts/tests/test_agent_factory.py`
  - `contracts/tests/test_governance_contract.py`
  - `contracts/tests/test_creator_vesting.py`
- Added backend security regression coverage in:
  - `backend/tests/test_orchestrator_security.py`
  - `backend/tests/test_auth_middleware_security.py`
  - `backend/tests/test_websocket_auth_security.py`
- Added Merkle proof generation/verification tests in `scripts/test_airdrop_snapshot.py`.
- Updated `SECURITY_AUDIT.md` and `SECURITY_AUDIT_REPORT.md` with 2026-03-25 internal audit sprint addendum and current validation status.

### Root Cause
- Internal-audit benchmark mapping surfaced missing adversarial test coverage for consensus/auth/ws and uncovered two edge-case arithmetic defects in AgentFactory that were not exercised by existing regression tests.

### User Action
- Use `PYTHONPATH=. poetry run pytest tests/ -v` in `contracts`, `venv/bin/python -m pytest tests/ -v` in `backend`, and `venv/bin/python -m pytest scripts/test_airdrop_snapshot.py -v` from repo root to reproduce this audit sprint’s passing suites.
- Complete environment prerequisites for final launch gating: resolve Playwright runtime browser path mismatch and run `contracts/tests/live_testnet_verify.py smoke` after funding disposable wallets and exporting `DEPLOYER_MNEMONIC`.

## 0.7.9 - 2026-03-17

### Fixed
- Patched `backend/src/api/agents_api.py` so the Senator and Curator governance proxy endpoints forward FastAPI `Request` context into `create_proposal(...)` and `review_proposal(...)`, resolving the runtime `TypeError` that returned `500 Internal server error` on `/api/agents/senator/propose`.
- Updated `contracts/tests/live_testnet_verify.py` governance smoke to handle both valid curator review outcomes: it now submits a vote only when proposal status transitions to `voting`, and records a deterministic skip when review rejects the proposal.

### Root Cause
- Governance service methods were hardened to require request context for auth/IP policy evaluation, but the agent-facing wrapper endpoints still called them with the previous argument shape; the live smoke harness also assumed every review would approve and move to voting.

### User Action
- Redeploy backend services so the updated governance proxy wiring is active in production.
- Use the updated smoke harness when validating governance against live tri-brain review paths, since rejection is now treated as an expected branch instead of a false-negative failure.

## 0.7.8 - 2026-03-17

### Updated
- Redeployed the active testnet Agent Factory to app `757288371` using the currently available deployer key and bootstrapped a fresh CORTEX asset `757288754`.
- Updated `deployment.testnet.json` and regenerated backend/frontend protocol config outputs so runtime clients resolve the new active factory and token IDs.
- Marked the prior canonical factory deployment (`757172168`) as deprecated legacy metadata in the manifest.

### Root Cause
- The previously configured deployer seed no longer matched the historical factory creator account, which blocked creator-only smoke flows and required rotating to a fresh deployment owned by the available operational key.

### User Action
- Keep marketplace trading disabled until the factory create flow is patched for runtime box references, then redeploy and re-run `contracts/tests/live_testnet_verify.py smoke` against the updated manifest.

## 0.7.7 - 2026-03-16

### Fixed
- Added `greenlet==3.3.2` to the backend runtime requirements so the new PostgreSQL-backed developer access and admin control-plane flows work locally and in fresh environments instead of crashing on first SQLAlchemy async session usage.
- Restored legacy `owner` and `tier` compatibility fields for PostgreSQL-backed API keys so chat session bootstrap, CLI, SDK, and admin-protected backend routes stop downgrading validated database keys to `unknown` / `free`.

### Updated
- Upgraded the backend runtime to `fastapi[all]==0.135.1`, `mcp==1.26.0`, and `pydantic==2.12.5`, which pulls in the patched Starlette/MCP dependency chain and clears the prior Python vulnerability findings.
- Added frontend dependency overrides for `ws@7.5.10` and `bn.js@4.12.3`, eliminating the remaining production `npm audit` findings from the WalletConnect dependency tree without changing the wallet UX.
- Added `OPENAI_ORG_ID` runtime support so the backend can explicitly bind OpenAI requests to the verified organization when `gpt-5` is re-enabled in production.
- Centralized the backend app version at `0.7.7` so the FastAPI metadata and `/health` response stay in sync instead of drifting independently.
- Changed the Compose `OPENAI_API_KEY` interpolation to an empty-default form so VM deploys stop logging a misleading missing-variable warning when the backend is intentionally reading that secret directly from Secret Manager at runtime.
- Added a dev-only local admin session bridge on the frontend so `/admin` can be exercised in a browser during local development without manually injecting the trusted owner email header.
- Added a gated live Playwright admin spec that seeds a real developer-access request, drives the browser approval/rotation/revocation flow, and verifies the revoked replacement key is rejected by the backend for repeatable local or staging smoke coverage.
- Added a one-command admin smoke wrapper plus frontend npm aliases so mocked admin E2E coverage always runs and the gated live admin Playwright flow can be folded in with the same command when the live flag is enabled.
- Added split GitHub Actions workflows at `.github/workflows/admin-e2e-mocked.yml` and `.github/workflows/admin-e2e-live.yml` so mocked admin browser coverage runs automatically while the live admin local-stack smoke remains separately dispatchable.
- Added separate Admin E2E Mocked and Admin E2E Live status badges to the README and expanded the live workflow-dispatch controls so CI runs can explicitly choose `dev-session` or `header` auth mode for stricter admin-surface validation.
- Added a dedicated README `CI` section so contributors can quickly see which admin workflow runs automatically on PRs and when to manually launch the live admin workflow.
- Documented the new fail-closed admin and proxy trust defaults in `DEPLOYMENT.md` and `.env.example`, including the production-only conditions for enabling `PURECORTEX_TRUST_PROXY_HEADERS=1` and `PURECORTEX_TRUST_ADMIN_EMAIL_HEADER=1`.
- Added a top-level `LICENSE` and enabled GitHub vulnerability alerts plus automated security fixes so the repository is ready for a controlled move toward public visibility.
- Added optional Google Cloud reCAPTCHA Enterprise, a hidden honeypot field, and Redis-backed per-email/per-IP submission cooldowns to the public developer-access request flow so the owner review queue is less exposed to bot spam and repeated form abuse.

### Root Cause
- The async SQLAlchemy/Postgres path depends on `greenlet`, but the backend dependency manifest only included SQLAlchemy, drivers, and Alembic, so fresh local environments could migrate successfully yet still fail once the app opened an async session.
- The new PostgreSQL-backed key records exposed richer `owner_name`, `owner_email`, and `runtime_tier` fields, but older auth and chat code still expected the legacy `owner` / `tier` shape used by the Redis-only key path.
- The previous dependency set pinned vulnerable FastAPI/MCP transitive versions, and the wallet connector ecosystem had not yet republished secure transitive patch levels even though compatible patched `ws` and `bn.js` releases were available.
- Production model selection already supported `gpt-5`, but the backend did not expose an explicit organization binding for OpenAI accounts that span multiple organizations.
- The admin and trusted-proxy hardening changed runtime defaults, but the deployment runbook and sample environment file still implied the older trust-on configuration and header-driven admin assumptions.
- The repository was operationally ready to ship, but it still lacked an explicit public-use license and had GitHub security features disabled, leaving unnecessary blockers before opening visibility.
- The public developer-access endpoint was intentionally open and rate-limited, but it still lacked dedicated bot verification and repeat-submission friction for abusive or automated request traffic.

### User Action
- Reinstall backend Python dependencies or rebuild the backend image so the runtime picks up `greenlet` before exercising the PostgreSQL-backed admin control plane.
- For local browser admin testing, visit `/admin/login` first to establish the dev-only admin session, then continue to `/admin`.
- To run the live browser admin smoke test, set `PURECORTEX_RUN_LIVE_ADMIN_E2E=1` and point `PURECORTEX_E2E_BACKEND_URL` plus `PURECORTEX_ADMIN_E2E_AUTH_MODE` at the target environment before invoking `npx playwright test tests/e2e/admin.live.spec.ts`.
- For the combined admin smoke path, run `cd frontend && npm run test:e2e:admin:smoke`; add the same live-test environment variables when you want the command to include the real browser flow.
- In GitHub Actions, the mocked admin workflow runs automatically on pushes and pull requests touching the relevant files, while the live local-stack admin workflow is launched manually through `Admin E2E Live` workflow dispatch and now lets you choose `dev-session` or `header` auth mode.
- Redeploy the VM stack so the backend picks up the new Python dependency set, the frontend serves the patched wallet dependency graph, and the OpenAI org-aware runtime configuration is applied.
- Set `OPENAI_ORG_ID` in the VM environment or Secret Manager if the OpenAI key is attached to a multi-organization OpenAI account and explicit org binding is required.
- For production, enable `PURECORTEX_TRUST_PROXY_HEADERS=1` and `PURECORTEX_TRUST_ADMIN_EMAIL_HEADER=1` only behind the documented `nginx` plus `oauth2-proxy` boundary; leave both disabled for local or direct-service access paths.
- Before flipping the repository public, keep the full-history secret scan report, confirm `LICENSE` is present on `main`, and enable branch protection on `main` immediately after visibility changes if your GitHub plan does not support it while private.
- To activate the developer-access anti-bot controls, set `PURECORTEX_RECAPTCHA_SITE_KEY` and confirm the runtime has GCP credentials that can call reCAPTCHA Enterprise assessments, then redeploy the VM stack so the backend exposes the site key to the public form.

## 0.7.6 - 2026-03-16

### Fixed
- Hardened reverse-proxy client IP handling by sanitizing `X-Forwarded-For` at Nginx and updating backend IP resolution to select the rightmost untrusted hop, preventing spoofed client IPs from bypassing rate limiting or contaminating future IP allowlist enforcement.
- Made the isolated signer fail closed when `PURECORTEX_SIGNER_SHARED_TOKEN` is missing and switched signer request token checks to constant-time comparison so the daemon cannot run unauthenticated.
- Updated the VM deploy flow to force-recreate the backend and Cloud SQL proxy together when Cloud SQL mode is active, preventing shared-network proxy drift during backend redeploys.

### Root Cause
- The initial production hardening pass trusted the leftmost forwarded IP value from a trusted proxy chain and allowed the signer daemon to continue operating when its shared token was empty, leaving avoidable gaps in two core security boundaries.

### User Action
- Redeploy the VM stack so Nginx, backend, and signer all pick up the new proxy and signer-token enforcement behavior.

## 0.7.5 - 2026-03-16

### Updated
- Added production Cloud SQL rollout support with Alembic migrations, Cloud SQL Auth Proxy wiring, VM runtime env syncing from Secret Manager, and the first public developer access request flow backed by PostgreSQL instead of the prior placeholder foundation only.
- Added the initial owner admin surface at `/admin`, protected `/admin-api/*` routes, and Nginx plus `oauth2-proxy` edge-auth scaffolding so owner workflows can move behind Google SSO while preserving app-level allowlist checks.
- Hardened the frontend shared UX by fixing chat reconnect state handling and route-driven mobile menu state updates uncovered during validation of the new developer access surfaces.

### Root Cause
- The first foundation pass defined the enterprise control plane shape, but production still lacked a managed database target, VM deploy-time secret hydration, and a real edge-auth path for the owner admin console.

### User Action
- Store Google OAuth, Cloud SQL, and oauth2-proxy cookie secrets in GCP Secret Manager before using the owner admin surface in production.
- Set `PURECORTEX_CLOUD_SQL_CONNECTION_NAME` on the VM once the managed Postgres instance is provisioned so deployments cut over from the local fallback database to Cloud SQL.

## 0.7.4 - 2026-03-15

### Updated
- Added an enterprise developer-access implementation spec covering the public API key request UX, owner-only Google SSO admin console, managed PostgreSQL source of truth, internal admin APIs, audit logging, and per-key IP allowlist enforcement for API, CLI, SDK, and future hosted MCP access.
- Linked the new control-plane design into the main repository specification, roadmap, and README so the rollout path is grounded in the tracked architecture docs.
- Added non-breaking phase 1 foundation code for centralized enterprise-access settings, trusted reverse-proxy client IP resolution, an internal admin API boundary, and environment placeholders for Cloud SQL, Google OAuth, and server-only admin secrets.

### Root Cause
- The existing Redis-only API key model and lightweight admin bootstrap flow were sufficient for current testnet auth, but not for a proper developer access program with owner review, auditability, and enterprise-grade security controls.

### User Action
- No end-user action yet. This change defines the approved implementation path for the upcoming developer access control plane.

## 0.7.3 - 2026-03-15

### Updated
- Added first-party in-repo SDK packages for Python (`sdk/python`) and TypeScript/JavaScript (`sdk/typescript`) covering health, transparency, governance, agent chat, chat-session bootstrap, and admin key workflows.
- Expanded the MCP server from a single consensus tool into a practical local read-only tool surface for protocol health, agent registry/activity, governance overview/proposals, and transparency snapshots.
- Extended the CLI with `activity`, `session`, `overview`, and `proposal` commands, added package metadata documentation, and refreshed in-app, docs-site, and repo markdown docs around the new SDK/API/CLI/MCP surfaces.

### Root Cause
- The repository still documented dedicated SDK packages as future work, the MCP surface underrepresented the live public data already available, and the CLI/documentation surface lagged behind the backend's current capabilities.

### User Action
- Install the Python SDK from `./sdk/python` and the TypeScript SDK from `./sdk/typescript` until registry publication is enabled.
- Use `pcx activity`, `pcx session`, `pcx overview`, and `pcx proposal <id>` for the new operator workflows.
- For local MCP integrations, prefer the new read-only tools for protocol inspection and reserve `get_tri_brain_consensus` for reasoning-oriented prompts.

## 0.7.2 - 2026-03-15

### Updated
- Brought the embedded frontend CLI documentation page in line with the current `pcx` command set, `ctx_` API key examples, and live testnet API behavior.

### Root Cause
- The public `/docs/cli` page is sourced from `frontend/src/content/docs/cli.md`, which still reflected an older CLI surface after the broader repository docs refresh.

### User Action
- Use `pcx status`, `pcx info`, `pcx supply`, `pcx treasury`, `pcx burns`, `pcx agents`, `pcx proposals`, `pcx constitution`, and `pcx chat senator` as the current documented command surface.

## 0.7.1 - 2026-03-15

### Updated
- Refreshed GitHub-facing docs, in-app docs, and docs-site pages to match the current PURECORTEX testnet deployment, repository URL, tri-brain model stack, and authenticated chat flow.
- Updated CLI and helper scripts to use canonical testnet IDs, current health response fields, `ctx_` API key examples, and the real PURECORTEX status surface.
- Corrected MCP documentation to match the currently implemented stdio server and removed references to undocumented public SSE transport and non-existent tools/endpoints.

### Root Cause
- Multiple repository docs and helper scripts had drifted from the live testnet implementation after deployment hardening, auth changes, and docs-site expansion.

### User Action
- Use `PURECORTEX_API_KEY=ctx_...` for authenticated CLI or REST examples.
- For MCP local integration, point clients at `backend/mcp_server.py` and do not assume a public `/mcp/sse` endpoint unless the active deployment docs explicitly add one.
