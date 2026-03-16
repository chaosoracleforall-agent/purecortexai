# Changelog

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

### Root Cause
- The async SQLAlchemy/Postgres path depends on `greenlet`, but the backend dependency manifest only included SQLAlchemy, drivers, and Alembic, so fresh local environments could migrate successfully yet still fail once the app opened an async session.
- The new PostgreSQL-backed key records exposed richer `owner_name`, `owner_email`, and `runtime_tier` fields, but older auth and chat code still expected the legacy `owner` / `tier` shape used by the Redis-only key path.
- The previous dependency set pinned vulnerable FastAPI/MCP transitive versions, and the wallet connector ecosystem had not yet republished secure transitive patch levels even though compatible patched `ws` and `bn.js` releases were available.
- Production model selection already supported `gpt-5`, but the backend did not expose an explicit organization binding for OpenAI accounts that span multiple organizations.
- The admin and trusted-proxy hardening changed runtime defaults, but the deployment runbook and sample environment file still implied the older trust-on configuration and header-driven admin assumptions.

### User Action
- Reinstall backend Python dependencies or rebuild the backend image so the runtime picks up `greenlet` before exercising the PostgreSQL-backed admin control plane.
- For local browser admin testing, visit `/admin/login` first to establish the dev-only admin session, then continue to `/admin`.
- To run the live browser admin smoke test, set `PURECORTEX_RUN_LIVE_ADMIN_E2E=1` and point `PURECORTEX_E2E_BACKEND_URL` plus `PURECORTEX_ADMIN_E2E_AUTH_MODE` at the target environment before invoking `npx playwright test tests/e2e/admin.live.spec.ts`.
- For the combined admin smoke path, run `cd frontend && npm run test:e2e:admin:smoke`; add the same live-test environment variables when you want the command to include the real browser flow.
- In GitHub Actions, the mocked admin workflow runs automatically on pushes and pull requests touching the relevant files, while the live local-stack admin workflow is launched manually through `Admin E2E Live` workflow dispatch and now lets you choose `dev-session` or `header` auth mode.
- Redeploy the VM stack so the backend picks up the new Python dependency set, the frontend serves the patched wallet dependency graph, and the OpenAI org-aware runtime configuration is applied.
- Set `OPENAI_ORG_ID` in the VM environment or Secret Manager if the OpenAI key is attached to a multi-organization OpenAI account and explicit org binding is required.
- For production, enable `PURECORTEX_TRUST_PROXY_HEADERS=1` and `PURECORTEX_TRUST_ADMIN_EMAIL_HEADER=1` only behind the documented `nginx` plus `oauth2-proxy` boundary; leave both disabled for local or direct-service access paths.

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
