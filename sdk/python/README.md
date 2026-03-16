# PURECORTEX Python SDK

Official Python client for the PURECORTEX REST API and authenticated chat-session workflow.

## Current coverage

- Public health, transparency, governance, and agent-registry endpoints
- Authenticated agent chat
- Chat session bootstrap for WebSocket usage
- WebSocket URL helpers and sequential chat helper
- Admin key bootstrap/create/revoke helpers

## Install from the repository

```bash
pip install ./sdk/python
```

Or directly from GitHub:

```bash
pip install "git+https://github.com/chaosoracleforall-agent/purecortexai.git#subdirectory=sdk/python"
```

## Quick start

```python
from purecortex_sdk import PureCortexClient

with PureCortexClient(api_key="ctx_your_key") as client:
    health = client.health()
    print(health["status"])

    registry = client.list_agents()
    print(registry["total_agents"])

    reply = client.chat("senator", "Summarize the governance system.")
    print(reply["response"])
```

## WebSocket flow

```python
import asyncio
from purecortex_sdk import PureCortexClient


async def main() -> None:
    with PureCortexClient(api_key="ctx_your_key") as client:
        messages = await client.websocket_chat(
            [
                "What is PURECORTEX?",
                "How does governance work?",
            ]
        )
        for message in messages:
            print(message)


asyncio.run(main())
```
