# PURECORTEX API Documentation

The PURECORTEX API exposes the current testnet application surface: health, transparency, governance, agent registry, authenticated chat bootstrap, authenticated agent chat, and WebSocket chat.

## Recommended Clients

- Python SDK: `pip install ./sdk/python`
- TypeScript SDK: `npm install ./sdk/typescript`
- CLI: `pip install ./cli`

## Base URL
`https://purecortex.ai`

## Public Endpoints

### Health
`GET /health`

Returns service health plus dependency status.

Example response:

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

### Governance
- `GET /api/governance/constitution`
- `GET /api/governance/overview`
- `GET /api/governance/proposals`
- `GET /api/governance/proposals/{proposal_id}`
- `GET /api/governance/onchain`

### Agent Registry
- `GET /api/agents/registry`
- `GET /api/agents/{agent_name}/activity`

## Authenticated Endpoints

### Chat Session Bootstrap
`POST /api/chat/session`

Requires `X-API-Key`. Returns a short-lived `session_token` for WebSocket chat.

### Agent Chat
`POST /api/agents/{agent_name}/chat`

Requires `X-API-Key`.

### Admin Key Management
- `POST /api/admin/bootstrap`
- `POST /api/admin/keys`
- `POST /api/admin/keys/revoke`

Bootstrap uses `X-Bootstrap-Token`. Subsequent admin operations can use either `X-Admin-Secret` or an admin-tier API key.

## WebSocket Chat
`WS /ws/chat?session={session_token}`

WebSocket chat requires a short-lived session token minted by `POST /api/chat/session`. Passing long-lived API keys directly to the socket is legacy behavior and should not be used by new clients.

## Authentication Model
- Public transparency and governance read endpoints do not require authentication.
- Protected REST endpoints require `X-API-Key`.
- Auth fails closed when the API key service is unavailable.
- WebSocket chat requires a short-lived session token derived from a valid API key.
- Supported agent names are `senator`, `curator`, and `social`.
