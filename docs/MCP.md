# Model Context Protocol (MCP) Documentation

PURECORTEX includes a FastMCP server for local agent-to-agent tool integration, decision-node workflows, and public protocol reads.

## Server Specification
- **Implementation:** FastMCP (`backend/mcp_server.py`)
- **Current transport:** Standard I/O
- **Remote transport:** Do not assume a public SSE endpoint unless it is explicitly documented for the active deployment

## Available Tools

### `get_tri_brain_consensus`
- **Arguments:** `prompt: string`
- **Description:** Sends a prompt through the PURECORTEX tri-brain stack.
- **Models:** Claude Opus 4.6, Gemini 2.5 Pro, and GPT-5
- **Consensus Logic:** High-risk decisions use 2-of-3 majority. Lower-risk flows can degrade to soft consensus when one valid response is sufficient.
- **Security:** Requests are still subject to the orchestration and permission-sandbox layers before any action is executed.

### Public read-only tools
- `get_protocol_health`
- `get_agent_registry`
- `get_agent_activity`
- `get_governance_overview`
- `list_governance_proposals`
- `get_governance_proposal`
- `get_transparency_snapshot`

## Integration Note
Use the MCP server as a decision surface and local read-only observer, not as a bypass around protocol auth or sandboxing. For public web integrations, follow the main API and WebSocket documentation first.
