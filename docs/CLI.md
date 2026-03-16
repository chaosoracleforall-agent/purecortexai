# PURECORTEX CLI Documentation

The repo ships a Python CLI at `cli/pcx.py` for querying protocol status, transparency data, governance, agent activity, chat-session bootstrap, and authenticated agent chat.

## Installation

From the repo root:

```bash
cd cli
python3 -m pip install -e .
```

You can also run it directly without packaging:

```bash
python3 cli/pcx.py --help
```

## Environment Variables
- `PURECORTEX_API_URL`: Optional override for the API base URL. Defaults to `https://purecortex.ai`.
- `PURECORTEX_API_KEY`: Required for authenticated commands like `chat` and `session`.

## Available Commands

### `status`
Check backend health plus Redis, orchestrator, and agent loop status.

```bash
python3 cli/pcx.py status
```

### `supply`
Show the current CORTEX supply breakdown.

```bash
python3 cli/pcx.py supply
```

### `treasury`
Print treasury balances and revenue split data.

```bash
python3 cli/pcx.py treasury
```

### `burns`
Show buyback-burn history.

```bash
python3 cli/pcx.py burns
```

### `agents`
List registered protocol agents and their current status.

```bash
python3 cli/pcx.py agents
```

### `activity`
Show recent activity for one protocol agent.

```bash
python3 cli/pcx.py activity senator
```

### `chat`
Chat with an agent over the authenticated REST API.

```bash
export PURECORTEX_API_KEY=ctx_your_key
python3 cli/pcx.py chat senator
```

### `session`
Create a short-lived WebSocket session token from the current API key.

```bash
export PURECORTEX_API_KEY=ctx_your_key
python3 cli/pcx.py session
```

### `overview`
Display high-level governance counters.

```bash
python3 cli/pcx.py overview
```

### `proposals`
List current governance proposals from the backend API.

```bash
python3 cli/pcx.py proposals
```

### `proposal`
Display full detail for a single proposal.

```bash
python3 cli/pcx.py proposal 3
```

### `constitution`
Display the current governance constitution preamble.

```bash
python3 cli/pcx.py constitution
```

### `info`
Print the canonical testnet protocol identifiers and public URLs.

```bash
python3 cli/pcx.py info
```

## Notes
- Read-only commands use public endpoints.
- Chat and session bootstrap require a valid API key.
- The CLI reads canonical deployment IDs from `deployment.testnet.json` when available.
