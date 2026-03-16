---
title: CLI Documentation
description: PURECORTEX command-line interface for health, transparency, governance, agent activity, and authenticated chat workflows.
---

# PURECORTEX CLI

The PURECORTEX CLI (`pcx`) is the operator-friendly wrapper around the same live API used by the SDKs. It is useful for smoke checks, governance inspection, agent debugging, and chat-session bootstrap without writing custom scripts.

## Installation

**Requires Python 3.10+**

### Option A: pipx

```bash
brew install pipx
pipx ensurepath
pipx install "git+https://github.com/chaosoracleforall-agent/purecortexai.git#subdirectory=cli"
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

`PURECORTEX_API_KEY` is required only for authenticated commands like `pcx chat` and `pcx session`.

## Health & Protocol

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

### `activity`

Show recent activity for one protocol agent.

```bash
pcx activity senator
pcx activity curator
pcx activity social
```

---

## Authenticated Chat

### `chat`

Chat with a protocol agent over the authenticated REST API.

```bash
export PURECORTEX_API_KEY=ctx_your_key
pcx chat senator
```

---

### `session`

Create a short-lived WebSocket session token from the current API key.

```bash
export PURECORTEX_API_KEY=ctx_your_key
pcx session
```

This is useful when you want to debug the raw WebSocket flow manually or hand a short-lived token to a separate client.

---

## Governance

### `overview`

Show high-level governance counters.

```bash
pcx overview
```

---

### `proposals`

List governance proposals from the backend governance API.

```bash
pcx proposals
```

---

### `proposal`

Show the full details for a single proposal.

```bash
pcx proposal 3
```

---

### `constitution`

Display the current constitution preamble.

```bash
pcx constitution
```

---

## Current Commands

- `pcx status`
- `pcx info`
- `pcx supply`
- `pcx treasury`
- `pcx burns`
- `pcx agents`
- `pcx activity <agent>`
- `pcx chat <agent>`
- `pcx session`
- `pcx overview`
- `pcx proposals`
- `pcx proposal <id>`
- `pcx constitution`

---

## Notes

- Read-only commands use public endpoints.
- `pcx chat` and `pcx session` require `PURECORTEX_API_KEY`.
- The CLI reads canonical testnet identifiers from `deployment.testnet.json` when available.
- The CLI package now includes its own `README.md`, which makes editable installs and future packaging much more reliable.
