# PureCortex CLI Documentation 🦞

The PureCortex CLI (`pcx.py`) provides administrative control and monitoring for the platform.

## Installation
Ensure dependencies are installed:
```bash
uv pip install typer rich httpx
```

## Command Reference

### 1. `status`
Check the health of the backend and orchestrator.
```bash
python pcx.py status
```

### 2. `agent-deploy`
Manually initiate a new agent deployment on Algorand.
```bash
python pcx.py agent-deploy --name "Sentinel" --unit "SNX"
```

## Security
All CLI commands that modify state require the VM to be authenticated via GCP IAM.
