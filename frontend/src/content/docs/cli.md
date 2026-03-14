---
title: CLI Documentation
description: PureCortex command-line interface for administrative control and monitoring.
---

# PureCortex CLI

The PureCortex CLI (`pcx`) provides administrative control and monitoring for the platform.

## Installation

```bash
pip install purecortex-cli
```

Or install from source:

```bash
git clone https://github.com/chaosoracleforall-agent/purecortexai
cd purecortexai/cli
pip install -e .
```

### Dependencies

```bash
pip install typer rich httpx algosdk
```

---

## Configuration

Set the API endpoint:

```bash
export PURECORTEX_API_URL=https://purecortex.ai
```

Or pass it per-command:

```bash
pcx --api-url https://purecortex.ai status
```

---

## Command Reference

### `status`

Check the health of the backend and orchestrator.

```bash
pcx status
```

**Output:**
```
PureCortex Status
├── API: ✓ Operational
├── Orchestrator: ✓ Active
├── Algod: ✓ Syncing (testnet)
└── Version: 0.6.0
```

---

### `agents list`

List all agents deployed through the AgentFactory.

```bash
pcx agents list
```

**Output:**
```
┌──────────────────┬────────┬───────────┬──────────┬───────────┐
│ Name             │ Symbol │ Price     │ Holders  │ Curve     │
├──────────────────┼────────┼───────────┼──────────┼───────────┤
│ Cortex-Omega-1   │ CORTX  │ 0.42 ALGO │ 1,240    │ 65%       │
│ Neural-Sentinel  │ SENT   │ 0.15 ALGO │ 820      │ 22%       │
│ Chaos-Oracle     │ ORCL   │ 2.10 ALGO │ 4,100    │ 98%       │
└──────────────────┴────────┴───────────┴──────────┴───────────┘
```

---

### `agents deploy`

Deploy a new agent on the Algorand blockchain via the AgentFactory.

```bash
pcx agents deploy --name "Sentinel" --symbol "SNX"
```

**Flags:**
| Flag | Description | Required |
|------|-------------|----------|
| `--name` | Agent display name | Yes |
| `--symbol` | Token unit name (max 8 chars) | Yes |
| `--wallet` | Path to wallet mnemonic file | No (uses default) |

**Requirements:**
- Connected Algorand wallet with 100+ CORTEX tokens (creation fee)
- Sufficient ALGO for transaction fees and minimum balance

---

### `transparency`

Display current protocol transparency data.

```bash
pcx transparency
```

**Output:**
```
PureCortex Transparency Report
├── Total Supply: 10,000,000,000,000,000 CORTEX
├── Circulating: 3,100,000,000,000,000 CORTEX
├── Burned: 0 CORTEX
├── Assistance Fund: 0 ALGO
└── Creator Vesting: 0% released (TGE: 2026-03-31)
```

---

### `governance proposals`

List active and recent governance proposals.

```bash
pcx governance proposals
```

---

### `governance vote`

Cast a vote on an active proposal (requires veCORTEX stake).

```bash
pcx governance vote --proposal-id 1 --vote approve
```

---

## Security

All CLI commands that modify state require:
- Authenticated Algorand wallet
- Sufficient CORTEX/ALGO balances
- GCP IAM authentication (for admin commands on the VM)

Read-only commands (`status`, `agents list`, `transparency`) are publicly accessible.
