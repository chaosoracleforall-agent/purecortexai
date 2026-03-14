# PureCortex API Documentation 🦞

The PureCortex API provides high-performance, asynchronous endpoints for interacting with sovereign AI agents and the Algorand blockchain.

## Base URL
`http://34.122.128.229:8000`

## Endpoints

### 1. Health Check
`GET /health`
- **Description:** Returns the operational status of the API and Dual-Brain orchestrator.
- **Response:** `{"status": "ok", "orchestrator_active": true}`

### 2. Neural Link (WebSocket)
`WS /ws/chat`
- **Description:** Establish a real-time bi-directional link with the PureCortex Dual-Brain.
- **Protocol:** Message-based string exchange.
- **Security:** Guarded by XML structural guardrails and the `PermissionProxy`.

### 3. Agent Metadata (Upcoming)
`GET /agents/{asset_id}`
- **Description:** Retrieve on-chain and off-chain metadata for a specific agent token.

## Authentication
Authentication is currently handled via the `PermissionProxy`. High-tier actions require a valid `Authorization Token`.
