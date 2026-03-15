# Model Context Protocol (MCP) Documentation 🦞

PURECORTEX implements the Model Context Protocol to enable cross-agent tool discovery and coordinated intelligence.

## Server Specification
- **Implementation:** FastMCP (Python)
- **Transport:** Standard I/O (local) / SSE (Upcoming remote)

## Available Tools

### `get_tri_brain_consensus`
- **Arguments:** `prompt: string`
- **Description:** Submits a prompt to the PURECORTEX Tri-Brain (Claude + Gemini + GPT-5).
- **Consensus Logic:** 2-of-3 majority required between Claude, Gemini, and GPT-5 for the returned action.
- **Security:** Action validated by `PermissionProxy` (Tier 0 required).

## Coordinated Actions
Agents can discover PURECORTEX as a "Decision Node" within their own context windows by connecting to this MCP server.
