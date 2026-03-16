# Security Policy

## Reporting a Vulnerability

Please do not open public GitHub issues for suspected vulnerabilities.

Report security issues privately to:

- `hello@purecortex.ai`

Include:

- A clear description of the issue
- Impact and affected surface
- Reproduction steps or proof of concept
- Any suggested remediation

## Scope

This repository contains:

- A Next.js frontend
- A FastAPI backend
- Algorand smart contracts
- CLI, SDK, and MCP integration surfaces

Security-sensitive areas include:

- Authentication and API key issuance
- Wallet signing and governance voting
- Social-agent posting credentials
- Deployment and secret-management paths

## Expectations

- Do not exfiltrate data, secrets, or user credentials
- Do not perform destructive tests against production systems
- Prefer minimal proof-of-concept demonstrations

## Disclosure

We prefer coordinated disclosure. After receiving a report, we will triage it, confirm impact, and coordinate remediation and public communication as appropriate.
