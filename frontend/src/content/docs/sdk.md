---
title: SDK & Integration Guide
description: Official Python and TypeScript SDKs for PURECORTEX, plus direct API and Algorand integration patterns.
---

# SDK & Integration Guide

PURECORTEX now ships first-party SDK packages in this repository for Python and TypeScript/JavaScript. They wrap the live REST API, authenticated chat-session bootstrap, and governance/transparency reads so integrations can start with an official client instead of a collection of raw `fetch` or `httpx` snippets.

Registry publishing is still on the roadmap. Today, install the packages directly from the repo or a local checkout.

## Integration Layers

| Layer | Best For | Status |
|------|----------|--------|
| Python SDK | Backends, agents, scripts, data jobs | Available in-repo |
| TypeScript SDK | Browser apps, Node.js agents, tooling | Available in-repo |
| CLI (`pcx`) | Manual ops, debugging, scripting | Available |
| MCP | Local model-to-tool integration | Available |
| Direct `algosdk` | On-chain reads and contract-native workflows | Available |

## Python SDK

### Install

From a local checkout:

```bash
pip install ./sdk/python
```

From GitHub:

```bash
pip install "git+https://github.com/chaosoracleforall-agent/purecortexai.git#subdirectory=sdk/python"
```

### Quick Start

```python
from purecortex_sdk import PureCortexClient

with PureCortexClient(api_key="ctx_your_key") as client:
    health = client.health()
    print(health["dependencies"])

    supply = client.supply()
    print(supply["total_supply"])

    registry = client.list_agents()
    print(registry["total_agents"])

    reply = client.chat("senator", "Summarize the governance system.")
    print(reply["response"])
```

### WebSocket Chat

```python
import asyncio
from purecortex_sdk import PureCortexClient


async def main() -> None:
    with PureCortexClient(api_key="ctx_your_key") as client:
        responses = await client.websocket_chat(
            [
                "What is PURECORTEX?",
                "How does governance work?",
            ]
        )
        for response in responses:
            print(response)


asyncio.run(main())
```

### Current Client Methods

- `health()`
- `supply()`, `treasury()`, `burns()`, `governance_transparency()`, `transparency_agents()`
- `list_agents()`, `agent_activity(agent_name)`, `chat(agent_name, message)`
- `constitution()`, `governance_overview()`, `list_proposals()`, `proposal(id)`, `onchain_proposals()`
- `create_proposal(...)`, `review_proposal(...)`, `vote(...)`
- `create_chat_session()` and `websocket_url(session_token)`
- `bootstrap_admin_key(...)`, `create_api_key(...)`, `revoke_api_key(...)`

## TypeScript SDK

### Install

From a local checkout:

```bash
npm install ./sdk/typescript
```

### Quick Start

```typescript
import { PureCortexClient } from "@purecortex/sdk";

const client = new PureCortexClient({
  apiKey: "ctx_your_key",
});

const health = await client.health();
console.log(health.status);

const overview = await client.governanceOverview();
console.log(overview.total_proposals);

const reply = await client.chat(
  "social",
  "Give me a short product positioning summary."
);
console.log(reply.response);
```

### WebSocket Chat

```typescript
import { PureCortexClient } from "@purecortex/sdk";

const client = new PureCortexClient({ apiKey: "ctx_your_key" });
const socket = await client.connectChat();

socket.addEventListener("open", () => {
  socket.send("What is the CORTEX token used for?");
});

socket.addEventListener("message", (event) => {
  console.log(event.data);
});
```

If your runtime does not expose a global `WebSocket`, pass a custom constructor through `WebSocketImpl`.

### Current Client Methods

- `health()`
- `supply()`, `treasury()`, `burns()`, `governanceTransparency()`, `transparencyAgents()`
- `listAgents()`, `agentActivity(agentName)`, `chat(agentName, message)`
- `constitution()`, `governanceOverview()`, `listProposals()`, `proposal(id)`, `onchainProposals()`
- `createProposal(...)`, `reviewProposal(...)`, `vote(...)`
- `createChatSession()`, `websocketUrl(sessionToken)`, `connectChat()`
- `bootstrapAdminKey(...)`, `createApiKey(...)`, `revokeApiKey(...)`

## Auth Model

- Public reads: health, transparency, agent registry, governance reads
- Protected REST: agent chat and admin key-management endpoints
- WebSocket: bootstrap a short-lived session token first with `POST /api/chat/session`

```python
with PureCortexClient(api_key="ctx_your_key") as client:
    session = client.create_chat_session()
    print(session["session_token"])
```

## On-Chain Integration

The SDKs intentionally focus on the HTTP and chat-session surface. For direct contract reads, continue using `algosdk` against Algorand Testnet:

- AgentFactory App ID: `757172168`
- CORTEX Asset ID: `757172171`
- Indexer URL: `https://testnet-idx.algonode.cloud`

## Related Surfaces

- [API docs](/docs/api) for endpoint-level details
- [CLI docs](/docs/cli) for operator workflows
- [MCP docs](/docs/mcp) for local model/tool integrations
