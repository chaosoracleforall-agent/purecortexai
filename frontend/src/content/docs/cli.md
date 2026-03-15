---
title: CLI Documentation
description: PURECORTEX command-line interface for querying the live testnet protocol.
---

# PURECORTEX CLI

The PURECORTEX CLI (`pcx`) provides a lightweight command-line interface for querying protocol health, transparency, governance, and authenticated agent chat.

## Installation

**Requires Python 3.10+**

### Option A: pipx

```bash
brew install pipx
pipx ensurepath
pipx install git+https://github.com/chaosoracleforall-agent/purecortexai.git#subdirectory=cli
```

### Option B: From source

```bash
git clone https://github.com/chaosoracleforall-agent/purecortexai.git
cd purecortexai/cli
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

Verify the installation:

```bash
pcx info
```

> macOS 15+ uses an externally-managed Python. Prefer `pipx` or a virtual environment instead of system `pip install`.

---

## Configuration

Optional environment variables:

```bash
export PURECORTEX_API_URL=https://purecortex.ai
export PURECORTEX_API_KEY=ctx_your_key
```

### `status`

Check backend health plus Redis, orchestrator, and agent loop status.

```bash
pcx status
```

Example output:

```
╭──────────────────── PURECORTEX Status ────────────────────╮
│ Backend Online                                            │
│ Version: 0.7.0                                            │
│ Overall status: ok                                        │
│ Redis: connected                                          │
│ Orchestrator: initialized                                 │
│ Agent loop: running                                       │
╰───────────────────────────────────────────────────────────╯
```

---

### `info`

Print the canonical testnet protocol identifiers and public URLs.

```bash
pcx info
```

### `supply`

Show the current CORTEX supply breakdown.

```bash
pcx supply
```

### `treasury`

Print treasury balances and revenue split data.

```bash
pcx treasury
```

### `burns`

Show buyback-burn history.

```bash
pcx burns
```

---

### `agents`

List the registered protocol agents and their current status.

```bash
pcx agents
```

---

### `chat`

Chat with a protocol agent over the authenticated REST API.

```bash
export PURECORTEX_API_KEY=ctx_your_key
pcx chat senator
```

---

### `proposals`

List governance proposals from the backend governance API.

```bash
pcx proposals
```

---

### `constitution`

Display the current constitution preamble.

```bash
pcx constitution
```

---

## Notes

- Read-only commands use public endpoints.
- `pcx chat` requires `PURECORTEX_API_KEY` because `POST /api/agents/{agent_name}/chat` is authenticated.
- The CLI reads canonical testnet identifiers from `deployment.testnet.json` when available.
