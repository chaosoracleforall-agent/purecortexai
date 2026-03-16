# Enterprise Developer Access & Admin Control Plane Specification

Status: approved for phased implementation
Owner: `chaosoracleforall@gmail.com`
Last updated: 2026-03-15

Related docs:
- `SPECIFICATION.md`
- `TECHNICAL_ROADMAP.md`
- `DEPLOYMENT.md`
- `docs/API.md`
- `docs/CLI.md`
- `docs/MCP.md`

## 1. Executive Summary

PURECORTEX needs a unified developer access system that covers the API, CLI, official SDKs, and future hosted MCP access. The current Redis-backed API key model is intentionally lightweight and does not provide:

- request and approval workflows
- Google SSO-protected admin operations
- per-key scopes beyond broad tiers
- IP allowlists
- one-time key reveal
- audit logs suitable for enterprise operations
- a durable source of truth outside Redis

This specification defines an enterprise-grade control plane built on the current PURECORTEX VM deployment model while introducing managed persistence, stronger admin isolation, and a clear phased rollout path.

## 2. Locked Decisions

These decisions are approved and should be treated as implementation constraints:

1. Public read endpoints remain public in v1.
2. A single API key model powers the API, CLI, and official SDKs.
3. MCP is included as a requested access surface, but hosted MCP transport is a later phase because the current MCP server is local stdio.
4. The admin dashboard is accessible only to `chaosoracleforall@gmail.com` via Google SSO.
5. Production source of truth moves to managed PostgreSQL, not Redis.
6. Redis remains in place for hot-path rate limiting, chat sessions, and optional key metadata caching.
7. Write-enabled keys should require at least one IP allowlist entry unless the owner explicitly overrides that policy and records a justification.
8. The browser must never hold an admin API key or long-lived backend admin secret.
9. Internal admin operations should not be exposed as public FastAPI routes when they can be kept container-internal.

## 3. Goals

- Give developers a clear UX to request access for the API, CLI, Python SDK, TypeScript SDK, and future hosted MCP.
- Give the owner a secure admin dashboard to review requests, issue keys, revoke keys, rotate keys, and manage allowlists.
- Support `read` and `write` access levels with internal scopes.
- Support one or many IP or CIDR allowlist entries per key.
- Provide enterprise-grade auditability for issuance, revocation, IP denials, and admin actions.
- Preserve the existing VM deployment while upgrading the data, auth, and operations model.
- Keep the eventual hosted MCP authorization model aligned with the same key and scope system.

## 4. Non-Goals

- Requiring keys for all public read endpoints in v1
- Building a multi-admin RBAC system in v1
- Shipping public self-serve automatic key issuance in v1
- Treating local stdio MCP as a network-authenticated service
- Replacing Redis-based chat-session bootstrap in this feature
- Replatforming the entire app away from the current VM deployment during phase 1

## 5. Current State

Current implementation in the repository:

- FastAPI app at `backend/main.py`
- Redis-backed API keys in `backend/src/services/api_keys.py`
- Basic admin bootstrap, create, and revoke endpoints in `backend/src/api/admin.py`
- API-key middleware in `backend/src/api/auth.py`
- No Google SSO library or admin dashboard in the frontend
- Nginx reverse proxy in `nginx.conf`
- Docker Compose deployment in `docker-compose.yml`

Current gaps:

- Redis is the only storage layer for API key metadata.
- The current key model only stores `owner`, `tier`, `active`, and `created_at`.
- No durable request records exist.
- No IP allowlist support exists.
- Admin operations are public API routes gated only by an admin secret or admin API key.
- There is no owner-only dashboard.

## 6. Target Architecture

### 6.1 Production Topology

The production architecture remains VM-based, but adds a managed database and a dedicated SSO boundary:

```text
Developers ───────► Nginx ───────────────► Frontend (Next.js)
                          │                     │
                          │                     ├── Public access-request UX
                          │                     └── Admin UI under /admin
                          │
                          ├───────────────────► Backend (FastAPI)
                          │                        │
Admin Owner ─► Google SSO │                        ├── Public developer-access APIs
         via oauth2-proxy │                        ├── Internal admin APIs
                          │                        ├── Redis (rate limits, chat sessions, hot cache)
                          │                        └── Cloud SQL Postgres via Cloud SQL Auth Proxy
                          │
                          └───────────────────► oauth2-proxy
```

### 6.2 Primary Components

#### Nginx

- Remains the public reverse proxy
- Terminates TLS
- Routes `/admin` through `auth_request` to `oauth2-proxy`
- Continues routing public app traffic to Next.js and public API traffic to FastAPI
- Must forward normalized client IP headers to the backend

#### oauth2-proxy

- Handles Google OAuth
- Restricts access to the exact owner email
- Issues secure session cookies for the admin UI
- Exposes authenticated identity to Nginx and the Next.js app via trusted headers

#### Next.js frontend

- Hosts the public developer access request flow
- Hosts the owner-only admin console
- Uses server-side route handlers for admin operations
- Calls backend internal admin endpoints over the container network using a server-only token

#### FastAPI backend

- Continues serving the public API surface
- Adds a new developer-access request surface
- Adds internal admin endpoints not routed publicly by Nginx
- Enforces scopes, status, expiry, and IP allowlists on API key validation
- Writes audit events and key metadata to PostgreSQL
- Optionally caches active key metadata in Redis

#### PostgreSQL

- Production source of truth for requests, key metadata, allowlists, and audit logs
- Managed by Cloud SQL for durability, backups, and operational safety

#### Redis

- Remains in place for:
  - request rate limiting
  - chat session tokens
  - optional key metadata hot cache
  - short-lived issuance claim tokens if introduced later

## 7. Infrastructure Decisions

### 7.1 Database Strategy

Production:

- Use Cloud SQL for PostgreSQL
- Access from the VM stack through a Cloud SQL Auth Proxy sidecar container
- Do not expose PostgreSQL publicly
- Use a least-privilege application database user
- Enable automated backups and point-in-time recovery

Local development:

- Use a local Postgres container or a local Postgres instance
- Keep the same schema and migration flow

Rationale:

- Durable auditability does not belong in Redis
- Cloud SQL is materially safer than introducing a self-managed Postgres container into the single VM production stack

### 7.2 Admin SSO Strategy

Phase 1 production choice:

- Add `oauth2-proxy` to the Docker Compose stack
- Configure Google OAuth with an exact email allowlist containing only `chaosoracleforall@gmail.com`
- Protect `/admin` and any admin-specific frontend data endpoints at Nginx using `auth_request`

Secondary defense:

- The Next.js admin layout and route handlers must still verify the trusted authenticated email and reject anything else

Rationale:

- This is the strongest improvement that fits the current VM architecture without redesigning the entire public entry path around a cloud load balancer and IAP

### 7.3 Internal Admin API Strategy

Admin operations should not be browser-to-FastAPI direct calls.

Instead:

1. The browser talks only to Next.js `/admin` pages and admin route handlers.
2. Next.js route handlers call FastAPI internal admin endpoints over the Docker network.
3. FastAPI internal admin endpoints require a server-only shared token.
4. Nginx does not expose those internal admin endpoints to the public internet.

Rationale:

- This prevents browser exposure of admin credentials
- This keeps the backend admin surface off the public edge

### 7.4 Key Storage Strategy

New raw key format:

```text
ctx_live_<key_id>_<secret>
```

Where:

- `key_id` is a short stable public identifier used for lookup and display
- `secret` is a high-entropy random value shown once at creation time

Store:

- `key_id`
- `key_prefix`
- `secret_hash`
- metadata and status fields

Recommended hashing:

- `HMAC-SHA256(secret, PURECORTEX_KEY_HMAC_SECRET)` for request-time verification

Rationale:

- API keys are machine-generated, high-entropy secrets
- A keyed HMAC is performant enough for online validation and appropriate for this use case
- The system should not store recoverable plaintext keys

## 8. Data Model

### 8.1 `developer_access_requests`

- `id`
- `requester_name`
- `requester_email`
- `organization`
- `use_case`
- `requested_surfaces` JSON
- `requested_access_level`
- `requested_ips` JSON
- `expected_rpm`
- `status`
- `review_notes`
- `created_at`
- `reviewed_at`
- `reviewed_by`
- `issued_key_id`

### 8.2 `api_keys`

- `id`
- `key_id`
- `key_prefix`
- `secret_hash`
- `label`
- `owner_name`
- `owner_email`
- `status`
- `access_level`
- `scopes` JSON
- `intended_surfaces` JSON
- `rate_limit_profile`
- `expires_at`
- `created_at`
- `created_by`
- `revoked_at`
- `revoked_by`
- `revocation_reason`
- `last_used_at`
- `last_used_ip`
- `override_no_ip_allowlist`
- `override_reason`
- `request_id`
- `notes`

### 8.3 `api_key_ip_allowlists`

- `id`
- `api_key_id`
- `cidr`
- `label`
- `created_at`
- `created_by`

### 8.4 `audit_events`

- `id`
- `actor_type`
- `actor_email`
- `event_type`
- `target_type`
- `target_id`
- `request_ip`
- `metadata` JSON
- `created_at`

### 8.5 Optional `api_key_usage_rollups`

Not required for phase 1, but recommended later for dashboard performance:

- `api_key_id`
- `date_hour`
- `request_count`
- `error_count`
- `denied_ip_count`

## 9. Access Model

### 9.1 User-Facing Access Levels

- `read`
- `write`

### 9.2 Internal Scopes

Recommended initial internal scopes:

- `read.public`
- `read.authenticated`
- `agent.chat`
- `governance.write`
- `admin.none`
- `mcp.read`
- `mcp.write`

Notes:

- `agent.chat` should cover authenticated chat flows like `POST /api/chat/session` and `POST /api/agents/{agent}/chat`
- `mcp.read` and `mcp.write` are future-facing and only apply once a hosted MCP transport exists

### 9.3 Surface Mapping

Same key, different clients:

- API
- CLI
- Python SDK
- TypeScript SDK
- Future hosted MCP gateway

Local stdio MCP is not network-authenticated and does not consume issued keys.

## 10. IP Allowlist Policy

### 10.1 Supported Formats

- single IPv4 address
- single IPv6 address
- IPv4 CIDR
- IPv6 CIDR

### 10.2 Policy Rules

- If a key has one or more allowlist entries, requests from any non-matching IP must fail with `403`
- If a key is `write` and has no allowlist entry, the admin UI should require an explicit override and justification
- All IP denials must create audit events
- The admin dashboard must show the last successful IP and the most recent denied IP

### 10.3 IP Trust Chain

The backend must not trust arbitrary headers from the public internet.

The backend should:

1. Trust only the proxy headers set by the local Nginx reverse proxy
2. Resolve the client IP through a dedicated helper
3. Normalize `X-Real-IP` and `X-Forwarded-For`
4. Use one canonical resolved IP for:
   - allowlist checks
   - usage logging
   - rate limiting

## 11. UX / UI Specification

### 11.1 Public Request Flow

Route:

- `frontend/src/app/developers/access/page.tsx`

Key UX requirements:

- Explain that one key works across API, CLI, and SDKs
- Show access cards for `Read`, `Write`, and `Custom`
- Let the user choose intended surfaces:
  - API
  - CLI
  - Python SDK
  - TypeScript SDK
  - MCP
- Collect:
  - name
  - email
  - organization
  - use case
  - expected traffic
  - requested IPs
- Show clear guidance on IP restrictions for fixed servers versus dynamic home IPs
- Return a request ID and a review-pending confirmation state

### 11.2 Owner Admin Console

Routes:

- `frontend/src/app/admin/layout.tsx`
- `frontend/src/app/admin/requests/page.tsx`
- `frontend/src/app/admin/api-keys/page.tsx`
- `frontend/src/app/admin/api-keys/[id]/page.tsx`
- `frontend/src/app/admin/audit/page.tsx`

Required views:

- Dashboard overview
- Pending requests queue
- Request review detail
- Key inventory
- Key detail view
- Audit log

Required actions:

- approve request
- reject request
- issue key
- reveal key once
- revoke key
- rotate key
- add IP allowlists
- remove IP allowlists
- set expiry
- set scopes and rate profile

### 11.3 Key Reveal UX

- The full key must be visible only once after issuance
- The UI must require an explicit acknowledgment that the key will not be shown again
- After reveal, only the key prefix and metadata remain visible
- The page should generate onboarding snippets for:
  - `curl`
  - `pcx`
  - Python SDK
  - TypeScript SDK
  - future hosted MCP config

## 12. Backend API Design

### 12.1 Public Endpoints

- `POST /api/developer-access/requests`
- `GET /api/developer-access/requests/{id}` optional for request-status checks

### 12.2 Internal Admin Endpoints

These should be container-internal and not publicly routed by Nginx:

- `POST /internal/admin/access-requests/{id}/approve`
- `POST /internal/admin/access-requests/{id}/reject`
- `GET /internal/admin/access-requests`
- `GET /internal/admin/access-requests/{id}`
- `GET /internal/admin/api-keys`
- `GET /internal/admin/api-keys/{id}`
- `POST /internal/admin/api-keys/{id}/revoke`
- `POST /internal/admin/api-keys/{id}/rotate`
- `PUT /internal/admin/api-keys/{id}/allowlists`
- `GET /internal/admin/audit-events`

### 12.3 Frontend Route Handlers

Recommended Next.js route handlers:

- `frontend/src/app/api/admin/requests/...`
- `frontend/src/app/api/admin/api-keys/...`
- `frontend/src/app/api/admin/audit/...`

Responsibilities:

- verify owner identity from trusted SSO headers
- call FastAPI internal admin endpoints
- never expose the internal admin token to the browser

## 13. Validation Order For Protected Requests

For authenticated backend routes, the final middleware path should be:

1. Resolve trusted client IP
2. Parse key format and extract `key_id`
3. Load active key metadata from Redis cache or PostgreSQL
4. Verify secret hash
5. Check `status`
6. Check `expires_at`
7. Check IP allowlist
8. Check required scopes
9. Apply per-key rate limits
10. Attach resolved key metadata to request state
11. Log usage and failures

This replaces the current lightweight validation path in `backend/src/api/auth.py`.

## 14. Security Controls

Required controls:

- Google SSO exact-email allowlist for `/admin`
- Next.js app-side secondary admin email check
- Internal admin endpoints not exposed publicly
- server-only internal admin token
- one-time key reveal
- durable audit logging
- write-key IP allowlist policy
- least-privilege database user
- secrets in GCP Secret Manager, not committed files
- Nginx trusted proxy IP normalization

Recommended controls:

- admin session timeout and forced re-auth for key issuance actions
- separate `read` and `write` rate-limit profiles
- admin-action confirmation step for revoke and rotate
- background reconciliation between Redis hot cache and PostgreSQL source of truth

## 15. Observability And Operations

### 15.1 Metrics

Track:

- pending requests
- approved and rejected requests
- active keys
- write keys without allowlists
- IP-denied requests
- key creation, revoke, and rotate events
- internal admin API failures

### 15.2 Audit Events

Must log:

- request creation
- request approval
- request rejection
- key issuance
- key reveal
- key revoke
- key rotate
- allowlist change
- denied request due to IP mismatch
- denied request due to scope mismatch

### 15.3 Backups

- Cloud SQL automated backups enabled
- point-in-time recovery enabled
- audit retention policy documented

### 15.4 Deployment Safety

- apply database migrations before the new backend code path is enabled
- deploy internal admin APIs before the frontend admin console
- deploy oauth2-proxy and Nginx auth rules before linking to `/admin`

## 16. Phase Plan

### Phase 1: Foundation

Scope:

- PostgreSQL schema and migrations
- backend key model redesign
- IP allowlist enforcement
- audit logging
- internal admin API skeleton
- Cloud SQL Auth Proxy integration
- config and secret model

Deliverables:

- SQLAlchemy and Alembic foundation
- new developer access tables
- updated backend auth pipeline
- internal admin token path
- non-breaking coexistence with current auth until cutover

### Phase 2: Owner Dashboard And Public Request UX

Scope:

- public access request pages
- owner-only admin console
- oauth2-proxy setup
- Nginx `auth_request` protection
- issue, reveal, revoke, rotate, and allowlist UI

Deliverables:

- `/developers/access`
- `/admin/*`
- secure owner-only admin session flow
- request review queue
- key inventory

### Phase 3: Hosted MCP Access

Scope:

- remote MCP gateway design and deployment
- scope mapping for `mcp.read` and `mcp.write`
- docs and onboarding for hosted MCP credentials

Notes:

- This is intentionally separate because the current MCP server is local stdio

## 17. File-Level Implementation Map

### Backend

- `backend/requirements.txt`
  - add `sqlalchemy`, `alembic`, `asyncpg`, and any required migration/runtime support
- `backend/src/core/settings.py`
  - centralize new database, proxy, and admin token settings
- `backend/src/db/`
  - connection management and base metadata
- `backend/alembic/`
  - migrations
- `backend/src/models/`
  - developer access request, API key, allowlist, audit event models
- `backend/src/services/developer_access/`
  - request service
  - key service
  - allowlist service
  - audit service
  - cache adapter
- `backend/src/api/developer_access.py`
  - public request endpoints
- `backend/src/api/internal_admin.py`
  - internal admin endpoints
- `backend/src/api/auth.py`
  - updated validation, scopes, and allowlist enforcement

### Frontend

- `frontend/src/app/developers/access/`
  - public request experience
- `frontend/src/app/admin/`
  - protected admin console
- `frontend/src/lib/admin/`
  - trusted session parsing and admin fetch wrappers
- `frontend/src/app/api/admin/`
  - server-side proxy handlers to backend internal admin endpoints

### Infrastructure

- `docker-compose.yml`
  - add `oauth2-proxy`
  - add `cloud-sql-proxy`
- `nginx.conf`
  - protect `/admin` with `auth_request`
  - preserve correct IP header forwarding
- `.env.example`
  - add OAuth, Cloud SQL, internal admin token, key HMAC secret, and owner email config
- `scripts/deploy_vm.sh`
  - run migrations
  - verify new services

## 18. Test Strategy

### Backend Tests

- unit tests for key parsing and validation
- unit tests for IP allowlist matching
- unit tests for scope enforcement
- unit tests for admin-token protected internal endpoints
- migration smoke tests

### Frontend Tests

- request form happy path
- request form validation errors
- owner admin page redirect when unauthenticated
- owner admin page render when authenticated
- key issuance and one-time reveal flow

### Integration Tests

- Nginx plus oauth2-proxy auth flow for `/admin`
- backend enforcement with trusted proxy IP headers
- FastAPI internal admin route not externally reachable

## 19. Acceptance Criteria

This feature is complete when:

1. A public user can submit a developer access request and receive a request ID.
2. Only `chaosoracleforall@gmail.com` can access the admin dashboard through Google SSO.
3. The admin dashboard can approve, reject, issue, revoke, and rotate keys.
4. Each key supports `read` or `write` access level plus internal scopes.
5. Each key can have zero, one, or many IP or CIDR allowlist entries.
6. Requests from non-allowlisted IPs fail with `403` and create audit events.
7. The same issued key can be used by the API, CLI, Python SDK, and TypeScript SDK.
8. Hosted MCP support can later adopt the same model without redesigning the key system.
9. Admin actions and access denials are durably auditable.

## 20. Immediate Next Step

The next implementation step is phase 1 foundation work:

1. introduce PostgreSQL and migrations
2. refactor API key validation into a real service layer
3. add internal admin APIs
4. add IP allowlist enforcement and audit logging
5. wire Cloud SQL Auth Proxy and new secrets into the deployment model
