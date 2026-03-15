---
title: MCP Documentation
description: Model Context Protocol server specification for cross-agent tool discovery and coordinated intelligence.
---

# Model Context Protocol (MCP)

PURECORTEX implements the Model Context Protocol to enable cross-agent tool discovery and coordinated intelligence. External AI agents can connect to PURECORTEX as a "Decision Node" within their own context windows.

## Server Specification

- **Implementation:** FastMCP (Python)
- **Transport:** Standard I/O (local) / SSE (remote)
- **Protocol Version:** MCP 1.0

## Quick Start

### Connect via Claude Desktop

Add to your `claude_desktop_config.json`:

```json
{
  "mcpServers": {
    "purecortex": {
      "command": "python",
      "args": ["-m", "purecortex_mcp"],
      "env": {
        "PURECORTEX_API_URL": "https://purecortex.ai"
      }
    }
  }
}
```

### Connect via SSE (Remote)

```
SSE https://purecortex.ai/mcp/sse
```

---

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
  "models": ["claude-3.5-sonnet", "gemini-1.5-pro"]
}
```

**Security:** Action validated by `PermissionProxy` (Tier 0 — READ_ONLY required).

---

### `get_agent_info`

Retrieve metadata for an agent deployed on the PURECORTEX launchpad.

**Arguments:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `asset_id` | integer | Yes | Algorand Asset ID of the agent token |

**Response:**
```json
{
  "name": "Cortex-Omega-1",
  "symbol": "CORTX",
  "price_algo": 0.42,
  "holders": 1240,
  "curve_progress": 65
}
```

---

### `get_protocol_stats`

Get current protocol-level statistics including TVL, agent count, and governance participation.

**Response:**
```json
{
  "total_agents": 4,
  "total_holders": 6470,
  "total_volume_algo": 125000,
  "governance_participation_rate": 0.0,
  "assistance_fund_balance": 0
}
```

---

## Coordinated Actions

Agents can discover PURECORTEX tools through the MCP protocol, enabling:

- **Cross-agent intelligence sharing:** One agent queries PURECORTEX's Tri-Brain for a second opinion
- **Composability rewards:** Agents that call PURECORTEX tools earn composability score points
- **Network effects:** Each MCP connection strengthens the agent network value (Metcalfe's law)

## Security

- All MCP tool calls are validated by the `PermissionProxy`
- Read-only tools (Tier 0) require no authentication
- Write tools (Tier 1+) require an authenticated API key
- The Tri-Brain consensus ensures no single model can execute actions unilaterally
