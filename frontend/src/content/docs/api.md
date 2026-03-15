---
title: API Documentation
description: PURECORTEX REST and WebSocket API reference for interacting with sovereign AI agents on Algorand.
---

# PURECORTEX API Documentation

The PURECORTEX API provides high-performance, asynchronous endpoints for interacting with sovereign AI agents and the Algorand blockchain.

## Base URL

**Testnet:** `https://purecortex.ai/api`

## Authentication

Read-only transparency and governance endpoints are publicly accessible. Protected REST endpoints require `X-API-Key`, and WebSocket chat requires a short-lived session token created through `POST /api/chat/session`.

---

## Endpoints

### Health Check

```
GET /health
```

Returns the operational status of the API and Tri-Brain orchestrator.

**Response:**
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

---

### Neural Link (WebSocket)

```
WS /ws/chat
```

Establish a real-time bi-directional link with the PURECORTEX Tri-Brain consensus engine.

- **Protocol:** Message-based string exchange
- **Security:** Guarded by XML structural guardrails and an authenticated chat session
- **Consensus:** Both Claude and Gemini must agree on an action before execution

**Usage:**
```javascript
const session = await fetch('https://purecortex.ai/api/chat/session', {
  method: 'POST',
  headers: { 'X-API-Key': process.env.PURECORTEX_API_KEY! },
}).then((r) => r.json());

const ws = new WebSocket(`wss://purecortex.ai/ws/chat?session=${session.session_token}`);
```

---

### Transparency — Supply Data

```
GET /api/transparency/supply
```

Returns the current token supply breakdown, including circulating supply, burned tokens, and vesting progress.

**Response:**
```json
{
  "total_supply": 10000000000000000,
  "circulating_supply": 3100000000000000,
  "burned": 0,
  "vesting": {
    "creator_total": 1000000000000000,
    "creator_released": 100000000000000,
    "creator_remaining": 900000000000000,
    "tge_date": "2026-03-31",
    "vesting_end_date": "2026-09-27"
  }
}
```

---

### Transparency — Treasury

```
GET /api/transparency/treasury
```

Returns Assistance Fund and Operations Account balances with recent transactions.

---

### Transparency — Burn History

```
GET /api/transparency/burns
```

Returns a paginated list of buyback-burn transactions.

**Query Parameters:**
- `limit` (default: 50) — Number of results
- `offset` (default: 0) — Pagination offset

---

### Transparency — Agents

```
GET /api/transparency/agents
```

Returns the registry of all agents deployed through the AgentFactory, including on-chain metrics.

---

### Agent Metadata

```
GET /api/agents/{asset_id}
```

Retrieve on-chain and off-chain metadata for a specific agent token.

**Response:**
```json
{
  "asset_id": 757172171,
  "name": "Cortex-Omega-1",
  "symbol": "CORTX",
  "total_supply": 1000000000,
  "holders": 1240,
  "curve_progress": 65,
  "current_price_algo": 0.42
}
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| REST endpoints | 60 requests/minute |
| WebSocket messages | 10 messages/minute |
| Transparency endpoints | 120 requests/minute |

---

## Error Codes

| Code | Description |
|------|-------------|
| 200 | Success |
| 400 | Bad request — invalid parameters |
| 401 | Unauthorized — missing or invalid API key or chat session |
| 404 | Resource not found |
| 429 | Rate limit exceeded |
| 500 | Internal server error |
| 503 | Orchestrator unavailable |

---

## SDKs

Official SDKs are under development. In the meantime, use `algosdk` (JavaScript/Python) for direct contract interaction and standard HTTP/WebSocket clients for API access.

```bash
npm install algosdk
```

```python
pip install py-algorand-sdk
```
