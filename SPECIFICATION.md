# Technical Specification: PURECORTEX Ecosystem

## Core Components
1. **Launchpad:** Bonding-curve-based ASA deployment with graduation logic on Algorand Testnet.
2. **Tri-Brain Orchestrator:** Claude Opus 4.6, Gemini 2.5 Pro, and GPT-5 with 2-of-3 majority for high-risk actions.
3. **API Layer:** FastAPI services for transparency, governance, registry, authenticated chat bootstrap, and agent chat.
4. **Frontend Surface:** Next.js marketplace, governance, transparency, docs, and chat experiences.
5. **Treasury / Governance / Staking Contracts:** Dedicated smart contracts alongside the core AgentFactory.
6. **MCP Integration:** FastMCP decision-node support for agent-to-agent tool use.

## Algorand Primitives Used
- **ASAs:** Agent tokenization.
- **Box Storage:** Proposal, staking, and contract state reads.
- **Atomic Transfers:** Revenue routing and contract interactions.
- **Applications:** AgentFactory, governance, staking, and treasury app flows.
