# Contributing to PURECORTEX

## Scope
PURECORTEX spans smart contracts, backend services, and frontend applications. Contributions should prioritize safety, determinism, and reproducibility.

## Getting Started
- Fork and clone the repository.
- Create a feature branch from the active mainnet-launch branch.
- Bootstrap local dependencies for each workspace you touch (`contracts`, `backend`, `frontend`).
- Copy `.env.example` to `.env` and fill required local values.

## Development Guidelines
- Keep changes focused and scoped to one concern.
- Prefer fail-closed behavior for auth, signing, and risk checks.
- Never commit secrets, mnemonics, private keys, or `.env` values.
- Preserve existing security controls (signer isolation, HMAC validation, auth checks).
- Add or update tests for behavior changes.

## Testing Expectations
- Smart contracts: `cd contracts && PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`
- Backend: `cd backend && PYTHONPATH=. .venv/bin/python -m pytest tests/ -q`
- Frontend: run lint/build checks for modified UI paths.

## Pull Request Process
- Use descriptive PR titles and include rationale in the body.
- Link related issues and list risk areas.
- Include a test plan with exact commands executed.
- Add screenshots or recordings for user-facing changes.
- Ensure CI is green before requesting review.

## Security Reporting
Do not open public issues for sensitive vulnerabilities. Follow the private disclosure path in `docs/IMMUNEFI_BOUNTY_SPEC.md`.
