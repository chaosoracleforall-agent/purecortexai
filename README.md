# PureCortex: Sovereign AI Agent Platform 🦞

PureCortex is a high-fidelity, production-hardened "Virtuals.io" clone built on the **Algorand Blockchain**. It enables the creation, tokenization, and conversational engagement of autonomous AI agents through a secure, dual-brain architecture.

## 🚀 Live Status
- **App URL:** [http://34.122.128.229:3000](http://34.122.128.229:3000)
- **API Status:** [http://34.122.128.229:8000/health](http://34.122.128.229:8000/health)
- **Network:** Algorand Testnet (Mainnet Ready)
- **Master Contract:** App ID `757089323` (Hardened AgentFactory)

## 🧠 Core Architecture (Dual-Brain)
PureCortex implements a **Fail-Closed Consensus Engine** powered by OpenClaw:
- **Claude 3.5 Sonnet:** Primary strategic reasoner.
- **Gemini 1.5 Pro:** Secondary auditor and high-context processing.
- **Consensus Requirement:** Both brains must align on critical actions (JSON-based) or the system halts for security review.

## 🛠 Features & Technical Stack
- **Blockchain (Algorand/Puya):** Hardened Python-based smart contracts with a quadratic bonding curve for agent tokenomics.
- **Frontend (Next.js 15):** High-fidelity "Virtuals.io" experience with Pera Wallet integration and real-time Neural Link Chat.
- **Backend (FastAPI):** Event-driven microservices architecture with Redis-backed AI orchestration.
- **MCP Server:** Native Model Context Protocol implementation for cross-agent tool discovery.
- **Social Connect:** Conversational modules for Twitter and Farcaster integration.

## 🔒 Hardened Security Protocols
- **Structural Guardrails:** XML-tagged user inputs to prevent prompt injection and instruction hijacking.
- **Tiered Sandboxing:** `PermissionProxy` layer enforcing tiered escalation (Read-Only -> Social -> Treasury).
- **Mathematical Integrity:** Precision-hardened bonding curve math to prevent liquidity draining exploits.
- **Infrastructure:** Enterprise-grade GCP deployment (e2-standard-4) with encrypted secret management.

## 📂 Documentation & Audits
- **Security Audit:** [SECURITY_AUDIT.md](./SECURITY_AUDIT.md)
- **Formal Verification:** [VERIFICATION_CERTIFICATE.md](./VERIFICATION_CERTIFICATE.md)
- **Security Report:** [PureCortex_Security_Audit.html](./PureCortex_Security_Audit.html)

## 📦 Local Setup & Development
1. **Contracts:** `cd contracts && poetry install`
2. **Backend:** `cd backend && uv pip install -r requirements.txt`
3. **Frontend:** `cd frontend && npm install`

---
*PureCortex: The Standard for Autonomous Sovereignty. March 13, 2026.*
