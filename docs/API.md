# PURECORTEX API Documentation

The PURECORTEX API provides high-performance, asynchronous endpoints for interacting with sovereign AI agents and the Algorand blockchain.

## Base URL
`https://purecortex.ai`

## Endpoints

### 1. Health Check
`GET /health`
- **Description:** Returns the operational status of the API and Tri-Brain orchestrator.
- **Response:** `{"status": "ok", "orchestrator_active": true}`

### 2. Neural Link (WebSocket)
`WS /ws/chat`
- **Description:** Establish a real-time bi-directional link with the PURECORTEX Tri-Brain.
- **Protocol:** Message-based string exchange.
- **Security:** Requires a short-lived chat session created via `POST /api/chat/session` with a valid `X-API-Key`.

### 3. Agent Metadata (Upcoming)
`GET /agents/{asset_id}`
- **Description:** Retrieve on-chain and off-chain metadata for a specific agent token.

## Authentication
Protected endpoints require a valid `X-API-Key`. WebSocket chat uses a short-lived session token minted by `POST /api/chat/session`.
