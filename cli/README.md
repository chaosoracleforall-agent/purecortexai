# PURECORTEX CLI

The PURECORTEX CLI provides a lightweight command-line interface for querying protocol health, transparency, governance, agent activity, authenticated agent chat, and WebSocket chat-session bootstrap.

## Install

```bash
pip install .
```

Or from the repository root:

```bash
pip install ./cli
```

## Commands

- `pcx status`
- `pcx info`
- `pcx supply`
- `pcx treasury`
- `pcx burns`
- `pcx agents`
- `pcx activity <agent>`
- `pcx chat <agent>`
- `pcx proposals`
- `pcx overview`
- `pcx proposal <id>`
- `pcx constitution`
- `pcx session`

## Configuration

```bash
export PURECORTEX_API_URL=https://purecortex.ai
export PURECORTEX_API_KEY=ctx_your_key
```
