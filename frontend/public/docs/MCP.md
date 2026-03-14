# Model Context Protocol (MCP) Documentation 🦞

PureCortex implements the Model Context Protocol to enable cross-agent tool discovery and coordinated intelligence.

## Server Specification
- **Implementation:** FastMCP (Python)
- **Transport:** Standard I/O (local) / SSE (Upcoming remote)

## Available Tools

### `get_dual_brain_consensus`
- **Arguments:** `prompt: string`
- **Description:** Submits a prompt to the PureCortex Dual-Brain (Claude + Gemini).
- **Consensus Logic:** 100% agreement required between both brains for the returned action.
- **Security:** Action validated by `PermissionProxy` (Tier 0 required).

## Coordinated Actions
Agents can discover PureCortex as a "Decision Node" within their own context windows by connecting to this MCP server.
