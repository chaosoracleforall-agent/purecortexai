# PURECORTEX Admin Application Manual

## Purpose

This manual is for the owner-admin operating the PURECORTEX testnet application, especially the developer access control plane at `/admin`.

It explains:

- What parts of the application are currently functional
- How to review and approve or reject developer API key requests
- How to manage issued keys for API, CLI, SDK, and MCP access
- What prerequisites must be configured before the admin console is fully operational

## Application Surfaces

The current product has five main operator-facing surfaces:

- `Frontend`: `purecortex.ai` for chat, governance, marketplace, transparency, docs, and the owner admin console
- `Backend API`: FastAPI service for health, transparency, governance, staking reads, chat bootstrap, admin bootstrap, and agent APIs
- `CLI`: `pcx` command-line client
- `SDKs`: Python and TypeScript SDK packages
- `MCP`: local stdio MCP server for read-only protocol tools plus tri-brain consensus access

## What Must Exist Before Admin Workflows Function

The admin console can render with partial configuration, but full request approval requires all of the following:

- `PURECORTEX_INTERNAL_ADMIN_TOKEN`
- `PURECORTEX_ADMIN_ALLOWED_EMAILS`
- Google SSO or trusted admin-header injection at the edge
- `PURECORTEX_DATABASE_URL` or Cloud SQL configuration for the enterprise database
- `PURECORTEX_KEY_HMAC_SECRET`

Without the database configured:

- `/admin` can load
- `/admin-api/control-plane` can report health
- Request listing and key listing return `503`
- Approval, rejection, rotation, and policy updates cannot complete

## Admin Entry Point

The owner console lives at:

- `/admin`

The page presents:

- Control-plane health cards
- Pending developer access requests
- Issued API keys
- Policy editing controls for scopes, IP allowlists, notes, rotation, and revocation

## Understanding the Health Cards

The admin console shows whether these dependencies are ready:

- `Database`
- `Google OAuth`
- `Internal admin bridge`

Interpretation:

- `Ready`: the dependency is configured and the internal bridge responded successfully
- `Pending`: the dependency is not configured yet

Do not approve external developer access requests until the database and SSO boundary both show healthy behavior.

## Reviewing API Key Requests

Requests are submitted by developers who want to use one or more of:

- REST API
- CLI
- Python SDK
- TypeScript SDK
- MCP integrations

Each request includes:

- Requester name
- Requester email
- Organization
- Requested access level
- Requested surfaces
- Requested IPs
- Use case description

## Approval Workflow

For each pending request:

1. Read the requester identity and use case carefully.
2. Confirm the requested surfaces match the stated use case.
3. Review the requested IPs. Prefer specific CIDRs, not broad networks.
4. Set a human-readable key label.
5. Set expiry days if the access should be time-limited.
6. Edit the approved IP allowlists if you want to narrow or normalize them.
7. Add review notes describing why access was approved.
8. Click `Approve & Issue Key`.

Expected result:

- The request leaves the pending queue
- A new API key record appears in the issued-key section
- A one-time secret reveal is shown immediately after issuance

Important:

- Copy the one-time secret into your secure delivery channel immediately
- The displayed secret is the only time the raw key is shown

## Rejection Workflow

Reject a request when:

- The requester identity is unclear
- The use case is too vague
- The requested surfaces exceed the stated need
- The IP allowlist is missing or too broad
- The request asks for write access without a justified reason

To reject:

1. Add review notes explaining the reason for rejection.
2. Click `Reject`.

Best practice:

- Keep rejection notes short, specific, and actionable
- Tell the requester what to change before reapplying

## Issued API Key Management

The issued-key section allows day-two administration of live keys.

For each key you can update:

- `Label`
- `Scopes`
- `IP Allowlists`
- `Notes / Rotation Reason`
- `Allow empty IP allowlist for this key`

You can also:

- `Save Policy`
- `Rotate`
- `Revoke`

## Scope Guidance

Use the narrowest possible set of scopes.

Common scopes:

- `read.public`
- `agent.chat`
- `governance.write`
- `mcp.read`
- `mcp.write`

Recommended patterns:

- API or CLI read access: `read.public`, `agent.chat`
- MCP read-only access: `read.public`, `mcp.read`
- Governance write/testing access: only for trusted operators or approved write clients

Do not grant `governance.write` unless the requester truly needs write access.

## IP Allowlists

IP allowlists are a primary defensive control.

Recommendations:

- Prefer host IPs such as `/32` for IPv4 and `/128` for IPv6
- Use office or fixed egress CIDRs only when necessary
- Avoid broad ranges unless there is a documented justification
- Record the reason in notes when allowing empty IP allowlists

## Rotation Workflow

Rotate a key when:

- The key owner changes devices or infrastructure
- A contractor engagement ends
- A secret may have been exposed
- You are doing routine hygiene

Steps:

1. Enter the rotation reason in `Notes / Rotation Reason`.
2. Click `Rotate`.
3. Deliver the new one-time secret to the owner securely.
4. Confirm the old secret is no longer being used.

## Revocation Workflow

Revoke immediately when:

- A key is suspected compromised
- A project ends
- The owner is no longer authorized
- Policy violations occur

Steps:

1. Enter the revocation reason.
2. Click `Revoke`.
3. Confirm the key disappears from active operational use.

## What the Admin Should Verify Before Public Launch

Before allowing real external developers into the platform:

- Enterprise database is configured and healthy
- Google SSO owner boundary is enabled
- Internal admin token is server-only and rotated
- API key issuance, rotation, and revocation all work in production
- MCP, CLI, SDK, and API docs reflect the live implementation
- No internal-only infrastructure runbooks remain in public-facing docs
- Social-agent posting credentials and operational controls are explicitly reviewed

## Current Known Functional Gaps

As of the latest validation pass:

- Signed governance voting requires a wallet with actual veCORTEX or delegated power; current local testnet stake snapshots were empty
- Admin request and key-list routes return `503` until the enterprise database is configured
- The social agent can post in code, but there is no repo-backed evidence that it is currently active on X
- The GitHub repository is still private and should not be announced as public yet

## Operator Checklist

- Review health cards before taking admin action
- Approve only least-privilege scopes
- Require useful IP allowlists
- Record review notes for every approval or rejection
- Rotate keys on a schedule and on suspicion
- Revoke quickly when trust changes
- Keep public docs aligned with the actual running system
