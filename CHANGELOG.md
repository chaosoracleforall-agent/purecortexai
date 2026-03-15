# Changelog

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
