---
title: API Documentation
description: PURECORTEX REST and WebSocket API reference, including auth flows, endpoint families, and official SDK usage.
---

# PURECORTEX API Documentation

The PURECORTEX API exposes four main surfaces:

- protocol health
- public transparency and governance reads
- authenticated agent chat
- short-lived WebSocket chat sessions

The official Python and TypeScript SDKs in this repository wrap these endpoints directly, but every route can also be called over raw HTTPS.

## Base URL

**Testnet:** `https://purecortex.ai`

## Authentication

| Surface | Auth |
|--------|------|
| `GET /health` | Public |
| Transparency reads | Public |
| Governance reads | Public |
| Agent registry and activity | Public |
| Agent chat | `X-API-Key` required |
| WebSocket chat | `POST /api/chat/session` first, then `?session=...` |
| Admin key management | bootstrap token or admin credentials |

---

## Recommended Clients

- Python: `pip install ./sdk/python`
- TypeScript: `npm install ./sdk/typescript`
- CLI: `pip install ./cli`

If you prefer raw HTTP, the examples below map directly to the live endpoints.

## Endpoint Families

### Health

- `GET /health`

Returns:

```json
{
  "status": "ok",
  "version": "0.7.0",
  "dependencies": {
    "redis": "connected",
    "orchestrator": "initialized",
    "agent_loop": "running"
  }
}
```

### Transparency

- `GET /api/transparency/supply`
- `GET /api/transparency/treasury`
- `GET /api/transparency/burns`
- `GET /api/transparency/governance`
- `GET /api/transparency/agents`

Typical use cases:

- supply dashboards
- treasury reporting
- burn-history displays
- governance stats
- live agent ASA discovery from the Algorand indexer

### Agents

- `GET /api/agents/registry`
- `GET /api/agents/{agent_name}/activity`
- `POST /api/agents/{agent_name}/chat`

Supported `agent_name` values:

- `senator`
- `curator`
- `social`

### Governance

- `GET /api/governance/constitution`
- `GET /api/governance/overview`
- `GET /api/governance/proposals`
- `GET /api/governance/proposals/{proposal_id}`
- `GET /api/governance/onchain`
- `POST /api/governance/proposals`
- `POST /api/governance/proposals/{proposal_id}/review`
- `POST /api/governance/proposals/{proposal_id}/vote`

### Chat Session Bootstrap

- `POST /api/chat/session`

Response:

```json
{
  "session_token": "cxs_...",
  "expires_at": "2026-03-15T20:30:00+00:00",
  "ttl_seconds": 900,
  "owner": "example-user",
  "tier": "free"
}
```

### WebSocket Chat

- `WS /ws/chat?session=<token>`

The socket accepts plain text messages and returns plain text responses. Messages longer than `4096` characters are rejected, and the connection is rate limited server-side.

## Typical Chat Flow

```text
1. Create or load an API key
2. POST /api/chat/session with X-API-Key
3. Connect to wss://purecortex.ai/ws/chat?session=...
4. Send text messages
5. Read text responses
```

## Examples

### Python SDK

```python
from purecortex_sdk import PureCortexClient

with PureCortexClient(api_key="ctx_your_key") as client:
    session = client.create_chat_session()
    print(session["session_token"])

    reply = client.chat("senator", "Summarize the governance system.")
    print(reply["response"])
```

### TypeScript SDK

```typescript
import { PureCortexClient } from "@purecortex/sdk";

const client = new PureCortexClient({ apiKey: "ctx_your_key" });
const supply = await client.supply();
console.log(supply.total_supply);

const session = await client.createChatSession();
const socket = await client.connectChat({ sessionToken: session.session_token });
```

### Raw HTTP

```bash
curl https://purecortex.ai/health

curl https://purecortex.ai/api/agents/registry

curl -X POST https://purecortex.ai/api/chat/session \
  -H "X-API-Key: ctx_your_key"
```

## Rate Limits

| Channel | Limit |
|--------|-------|
| REST endpoints | `60` requests/minute |
| WebSocket messages | `10` messages/minute |
| Transparency endpoints | `120` requests/minute |

---

## Error Codes

| Code | Meaning |
|------|---------|
| `200` | Success |
| `400` | Invalid payload or unsupported state transition |
| `401` | Missing or invalid API key or chat session |
| `403` | Invalid bootstrap token or admin credentials |
| `404` | Resource not found |
| `409` | Duplicate vote or conflicting bootstrap action |
| `429` | Rate limit exceeded |
| `500` | Internal server error |
| `503` | Dependent service unavailable |

---

## On-Chain Boundary

The HTTP API is not the same thing as direct Algorand contract integration. Use `algosdk` when you need on-chain state, ARC artifacts, or indexer-native workflows:

- AgentFactory App ID: `757172168`
- CORTEX Asset ID: `757172171`
- Indexer URL: `https://testnet-idx.algonode.cloud`
