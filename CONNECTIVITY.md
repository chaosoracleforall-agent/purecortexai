# PURECORTEX: Agent Connectivity Guide

This file summarizes the current public entry points for integrating with PURECORTEX.

## API Surface
- **App / API domain:** `https://purecortex.ai`
- **Health endpoint:** `https://purecortex.ai/health`
- **Authenticated chat bootstrap:** `POST https://purecortex.ai/api/chat/session`
- **WebSocket chat:** `wss://purecortex.ai/ws/chat?session=...`

## MCP
- **Implementation:** FastMCP in `backend/mcp_server.py`
- **Current transport:** Standard I/O
- **Remote transport:** Refer to the active MCP docs before assuming a public SSE endpoint

## CLI
- **Repo CLI:** `cli/pcx.py`
- **Package metadata:** `cli/pyproject.toml`
- **Auth note:** Agent chat commands require `PURECORTEX_API_KEY`

## Developer Resources
- **GitHub:** https://github.com/chaosoracleforall-agent/purecortexai
- **README:** https://github.com/chaosoracleforall-agent/purecortexai/blob/main/README.md
- **Specification:** https://github.com/chaosoracleforall-agent/purecortexai/blob/main/SPECIFICATION.md
