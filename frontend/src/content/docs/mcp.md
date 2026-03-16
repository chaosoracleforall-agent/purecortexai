---
title: MCP Documentation
description: PURECORTEX MCP server for local tri-brain consensus, health, governance, transparency, and agent reads.
---

# Model Context Protocol (MCP)

PURECORTEX implements the Model Context Protocol to expose two kinds of local tools:

- a tri-brain consensus tool powered by the orchestrator
- practical read-only tools backed by the public API

This makes PURECORTEX useful both as a decision node and as a local protocol-observer toolset for IDEs and autonomous agents.

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
  "ok": true,
  "action": "RESPOND",
  "message": "The current bonding curve price is 0.42 ALGO...",
  "decision": {
    "action": "RESPOND",
    "message": "..."
  }
}
```

**Security:** Action validated by `PermissionProxy` (Tier 0 — READ_ONLY required).

---

### `get_protocol_health`

Fetch the live payload from `GET /health`.

### `get_agent_registry`

Fetch the protocol agent registry from `GET /api/agents/registry`.

### `get_agent_activity`

Fetch recent activity for `senator`, `curator`, or `social`.

### `get_governance_overview`

Fetch the governance counters from `GET /api/governance/overview`.

### `list_governance_proposals`

Fetch the proposal list and optionally trim it to the newest `N` entries.

### `get_governance_proposal`

Fetch one proposal by numeric ID.

### `get_transparency_snapshot`

Fetch a bundled snapshot of supply, treasury, burn, and governance transparency data.

---

## Coordinated Actions

Agents can discover the current PURECORTEX toolset through MCP, enabling:

- **Cross-agent intelligence sharing:** One agent queries PURECORTEX's Tri-Brain for a second opinion
- **Protocol observability:** IDEs and agents can pull health, governance, and transparency data without building their own HTTP client
- **Local composability:** A single local MCP server can answer both reasoning and monitoring questions

## Security

- All MCP tool calls are validated by the `PermissionProxy`
- The server runs at the `READ_ONLY` permission tier by default
- Public-read tools proxy the live public API without needing an API key
- The tri-brain tool still uses orchestrator-side validation before returning a decision

## Transport Note

The currently tracked deployment documents MCP as a local stdio server. Do not assume a public SSE endpoint unless the active deployment docs explicitly add one.
