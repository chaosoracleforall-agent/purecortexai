# PURECORTEX TypeScript SDK

Official JavaScript/TypeScript client for the PURECORTEX API and chat-session workflow.

## Current coverage

- Public health, transparency, governance, and agent-registry endpoints
- Authenticated agent chat
- Chat session bootstrap for WebSocket usage
- Browser/runtime WebSocket helpers
- Admin key bootstrap/create/revoke helpers

## Install from the repository

```bash
npm install ./sdk/typescript
```

## Quick start

```ts
import { PureCortexClient } from "@purecortex/sdk";

const client = new PureCortexClient({ apiKey: "ctx_your_key" });

const health = await client.health();
console.log(health.status);

const registry = await client.listAgents();
console.log(registry.total_agents);

const reply = await client.chat("senator", "Summarize the governance system.");
console.log(reply.response);
```

## WebSocket flow

```ts
import { PureCortexClient } from "@purecortex/sdk";

const client = new PureCortexClient({ apiKey: "ctx_your_key" });
const socket = await client.connectChat();

socket.addEventListener("open", () => {
  socket.send("What is PURECORTEX?");
});

socket.addEventListener("message", (event) => {
  console.log(event.data);
});
```
