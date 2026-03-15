---
title: MCP Documentation
description: Model Context Protocol server specification for cross-agent tool discovery and coordinated intelligence.
---

# Model Context Protocol (MCP)

PURECORTEX implements the Model Context Protocol to enable cross-agent tool discovery and coordinated intelligence. External AI agents can connect to PURECORTEX as a "Decision Node" within their own context windows.

## Server Specification

- **Implementation:** FastMCP (Python)
- **Transport:** Standard I/O (local)
- **Protocol Version:** MCP 1.0

## Quick Start

### Connect via Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "purecortex": {
      "command": "python",
      "args": ["/absolute/path/to/purecortexai/backend/mcp_server.py"],
      "env": {
        "PURECORTEX_API_URL": "https://purecortex.ai"
      }
    }
  }
}
```

## Available Tools

### `get_tri_brain_consensus`

Submit a prompt to the PURECORTEX Tri-Brain (Claude + Gemini + GPT-5) for consensus-based decision making.

**Arguments:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `prompt` | string | Yes | The query to submit for consensus |

**Response:**
```json
{
  "action": "REPLY",
  "response": "The current bonding curve price is 0.42 ALGO...",
  "consensus": true,
  "models": ["claude-opus-4-6", "gemini-2.5-pro", "gpt-5"]
}
```

**Security:** Action validated by `PermissionProxy` (Tier 0 — READ_ONLY required).

---

## Coordinated Actions

Agents can discover the current PURECORTEX decision-node tool through the MCP protocol, enabling:

- **Cross-agent intelligence sharing:** One agent queries PURECORTEX's Tri-Brain for a second opinion
- **Composability rewards:** Agents that call PURECORTEX tools earn composability score points
- **Network effects:** Each MCP connection strengthens the agent network value (Metcalfe's law)

## Security

- All MCP tool calls are validated by the `PermissionProxy`
- Read-only tools (Tier 0) require no authentication
- Write tools (Tier 1+) require an authenticated API key
- The Tri-Brain consensus ensures no single model can execute actions unilaterally

## Transport Note

The currently tracked deployment documents MCP as a local stdio server. Do not assume a public SSE endpoint unless the active deployment docs explicitly add one.
