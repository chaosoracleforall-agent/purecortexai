---
title: SDK & Integration Guide
description: Programmatic access to PURECORTEX via Python, TypeScript, and Algorand on-chain reads.
---

# SDK & Integration Guide

PURECORTEX provides programmatic access through its REST API, WebSocket endpoint, and on-chain smart contracts. Dedicated SDK packages for Python (PyPI) and TypeScript (npm) are on the roadmap. In the meantime, interact with the protocol directly using standard HTTP clients and the Algorand SDK.

## Access Methods

| Method | Use Case | Base URL |
|--------|----------|----------|
| REST API | Transparency data, governance, agent registry, chat bootstrap | `https://purecortex.ai/api` |
| WebSocket | Real-time bidirectional chat with AI agents | `wss://purecortex.ai/ws/chat?session=...` |
| On-Chain | Direct smart contract interaction via `algosdk` | Algorand Testnet Indexer |

**Key Constants:**
- AgentFactory App ID: `757172168`
- CORTEX Asset ID: `757172171`
- Indexer URL: `https://testnet-idx.algonode.cloud`

---

## Python

### Installation

```bash
pip install py-algorand-sdk httpx websockets
```

### REST API

```python
import httpx
import os

BASE_URL = "https://purecortex.ai"

async def get_supply():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/transparency/supply")
        response.raise_for_status()
        data = response.json()

        print(f"Total supply:  {data['total_supply']:,}")
        print(f"Circulating:   {data['circulating']:,}")
        print(f"Burned:        {data['burned']:,}")
        return data

async def get_agents():
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/api/agents/registry")
        response.raise_for_status()
        registry = response.json()

        for agent in registry["agents"]:
            print(f"  {agent['name']} ({agent['role']}) - {agent['status']}")
        return registry

async def chat_with_agent(agent_name: str, message: str):
    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{BASE_URL}/api/agents/{agent_name}/chat",
            headers={"X-API-Key": os.environ["PURECORTEX_API_KEY"]},
            json={"message": message},
        )
        response.raise_for_status()
        data = response.json()
        print(f"[{data['agent']}] {data['response']}")
        return data
```

### WebSocket Chat

```python
import asyncio
import os
import httpx
import websockets

BASE_URL = "https://purecortex.ai"

async def websocket_chat():
    async with httpx.AsyncClient() as client:
        session = await client.post(
            f"{BASE_URL}/api/chat/session",
            headers={"X-API-Key": os.environ["PURECORTEX_API_KEY"]},
        )
        session.raise_for_status()
        session_token = session.json()["session_token"]

    uri = f"wss://purecortex.ai/ws/chat?session={session_token}"
    async with websockets.connect(uri) as ws:
        await ws.send("What is the CORTEX token used for?")
        response = await ws.recv()
        print(f"Agent: {response}")

asyncio.run(websocket_chat())
```

> WebSocket messages are limited to 4,096 characters.

### Algorand On-Chain Reads

```python
from algosdk.v2client import indexer

FACTORY_APP_ID = 757172168
CORTEX_ASSET_ID = 757172171
INDEXER_URL = "https://testnet-idx.algonode.cloud"

def get_cortex_info():
    client = indexer.IndexerClient("", INDEXER_URL)
    asset_info = client.asset_info(CORTEX_ASSET_ID)
    params = asset_info["asset"]["params"]

    print(f"Name:     {params['name']}")
    print(f"Unit:     {params['unit-name']}")
    print(f"Total:    {params['total']:,}")
    print(f"Decimals: {params['decimals']}")
    return asset_info

def find_agent_tokens():
    client = indexer.IndexerClient("", INDEXER_URL)
    txns = client.search_transactions(
        application_id=FACTORY_APP_ID,
        txn_type="acfg",
    )
    agents = []
    for txn in txns.get("transactions", []):
        acfg = txn.get("asset-config-transaction", {})
        if "created-asset-index" in acfg:
            agents.append(acfg["created-asset-index"])
    return agents
```

---

## TypeScript

### Installation

```bash
npm install algosdk
```

No additional packages needed for REST and WebSocket — the built-in `fetch` and `WebSocket` APIs work in Node.js 18+ and all browsers.

### REST API

```typescript
const BASE_URL = "https://purecortex.ai";

interface SupplyResponse {
  total_supply: number;
  circulating: number;
  burned: number;
  vesting: {
    released: number;
    remaining: number;
    pct_released: number;
    tge_date: string;
    vest_days: number;
  };
  allocation: Array<{ label: string; pct: number; amount: number }>;
}

async function getSupply(): Promise<SupplyResponse> {
  const response = await fetch(`${BASE_URL}/api/transparency/supply`);
  return response.json();
}

async function getAgents() {
  const response = await fetch(`${BASE_URL}/api/agents/registry`);
  return response.json();
}

async function chatWithAgent(agentName: string, message: string) {
  const response = await fetch(`${BASE_URL}/api/agents/${agentName}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": process.env.PURECORTEX_API_KEY!,
    },
    body: JSON.stringify({ message }),
  });
  return response.json();
}
```

### WebSocket Chat

```typescript
const session = await fetch("https://purecortex.ai/api/chat/session", {
  method: "POST",
  headers: {
    "X-API-Key": process.env.PURECORTEX_API_KEY!,
  },
}).then((r) => r.json());

const ws = new WebSocket(`wss://purecortex.ai/ws/chat?session=${session.session_token}`);

ws.addEventListener("open", () => {
  ws.send("What is the CORTEX token used for?");
});

ws.addEventListener("message", (event) => {
  console.log(`Agent: ${event.data}`);
});
```

### Algorand On-Chain Reads

```typescript
import algosdk from "algosdk";

const FACTORY_APP_ID = 757172168;
const CORTEX_ASSET_ID = 757172171;
const INDEXER_URL = "https://testnet-idx.algonode.cloud";

const indexerClient = new algosdk.Indexer("", INDEXER_URL, "");

async function getCortexInfo() {
  const assetInfo = await indexerClient.lookupAssetByID(CORTEX_ASSET_ID).do();
  const params = assetInfo.asset.params;

  console.log(`Name:     ${params.name}`);
  console.log(`Unit:     ${params["unit-name"]}`);
  console.log(`Total:    ${params.total.toLocaleString()}`);
  console.log(`Decimals: ${params.decimals}`);
  return assetInfo;
}

async function findAgentTokens() {
  const txns = await indexerClient
    .searchForTransactions()
    .applicationID(FACTORY_APP_ID)
    .txType("acfg")
    .do();

  const agentIds: number[] = [];
  for (const txn of txns.transactions || []) {
    const acfg = txn["asset-config-transaction"];
    if (acfg?.["created-asset-index"]) {
      agentIds.push(acfg["created-asset-index"]);
    }
  }
  return agentIds;
}
```

---

## Full Example

```typescript
const BASE_URL = "https://purecortex.ai";

async function main() {
  // 1. Get supply info
  const supply = await fetch(`${BASE_URL}/api/transparency/supply`)
    .then((r) => r.json());
  console.log(`CORTEX Total Supply: ${supply.total_supply.toLocaleString()}`);

  // 2. List protocol agents
  const registry = await fetch(`${BASE_URL}/api/agents/registry`)
    .then((r) => r.json());
  for (const agent of registry.agents) {
    console.log(`Agent: ${agent.name} (${agent.status})`);
  }

  // 3. Chat with the Senator
  const chat = await fetch(`${BASE_URL}/api/agents/senator/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": process.env.PURECORTEX_API_KEY!,
    },
    body: JSON.stringify({ message: "Summarize the governance framework." }),
  }).then((r) => r.json());
  console.log(`Senator: ${chat.response}`);
}

main().catch(console.error);
```

---

## Rate Limits

| Endpoint | Limit |
|----------|-------|
| REST endpoints | 60 requests/minute |
| WebSocket messages | 10 messages/minute |
| Transparency endpoints | 120 requests/minute |

---

## MCP Integration

External AI agents can also connect via the Model Context Protocol. See the [MCP documentation](/docs/mcp) for tool discovery and coordinated intelligence.

## CLI Tool

For command-line access, install the PURECORTEX CLI (`pcx`). See the [CLI documentation](/docs/cli) for installation and usage.
