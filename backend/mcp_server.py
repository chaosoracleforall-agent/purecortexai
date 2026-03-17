import asyncio
import os
from typing import Any

import httpx
from mcp.server.fastmcp import FastMCP

from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier


API_URL = os.getenv("PURECORTEX_API_URL", "https://purecortex.ai").rstrip("/")
ALLOWED_AGENT_NAMES = {"senator", "curator", "social"}

# Create an MCP server
mcp = FastMCP("PURECORTEX", instructions="PURECORTEX Tri-Brain Orchestrator MCP Server")

# Security Proxy Initialization
proxy = PermissionProxy(PermissionTier.READ_ONLY)

# Global orchestrator instance
try:
    orchestrator = ConsensusOrchestrator()
except Exception:
    orchestrator = None


def _error(message: str) -> dict[str, Any]:
    return {"ok": False, "error": message}


async def _fetch_public_json(path: str) -> dict[str, Any]:
    try:
        async with httpx.AsyncClient(base_url=API_URL, timeout=10.0) as client:
            response = await client.get(path, headers={"Accept": "application/json"})
            response.raise_for_status()
            return {
                "ok": True,
                "source": f"{API_URL}{path}",
                "data": response.json(),
            }
    except Exception as exc:
        return _error(str(exc))


@mcp.tool()
async def get_tri_brain_consensus(prompt: str) -> dict[str, Any]:
    """Run a prompt through PURECORTEX tri-brain consensus."""
    if not orchestrator:
        return _error("Orchestrator not initialized.")

    system_prompt = (
        "You are participating in an MCP network. Formulate a consensus response. "
        "Respond ONLY in valid JSON with 'action' (RESPOND) and 'message'."
    )

    decision = await orchestrator.decide_action(system_prompt, prompt)
    if not decision:
        return _error("Consensus could not be reached.")

    if not proxy.validate_action(decision):
        return _error("Action blocked by PURECORTEX Security Proxy.")

    return {
        "ok": True,
        "action": decision.get("action", "RESPOND"),
        "message": decision.get("message", ""),
        "decision": decision,
    }


@mcp.tool()
async def get_protocol_health() -> dict[str, Any]:
    """Fetch the public API health status."""
    return await _fetch_public_json("/health")


@mcp.tool()
async def get_agent_registry() -> dict[str, Any]:
    """Fetch the public registry of protocol agents."""
    return await _fetch_public_json("/api/agents/registry")


@mcp.tool()
async def get_marketplace_config() -> dict[str, Any]:
    """Fetch current marketplace rollout and trading status."""
    return await _fetch_public_json("/api/marketplace/config")


@mcp.tool()
async def get_marketplace_agent_state(asset_id: int) -> dict[str, Any]:
    """Fetch live supply and curve config for one agent asset."""
    return await _fetch_public_json(f"/api/marketplace/agents/{asset_id}/state")


@mcp.tool()
async def preview_marketplace_buy_quote(asset_id: int, amount: int) -> dict[str, Any]:
    """Preview a buy quote from the public marketplace API."""
    return await _fetch_public_json(f"/api/marketplace/quote/buy?asset_id={asset_id}&amount={amount}")


@mcp.tool()
async def preview_marketplace_sell_quote(asset_id: int, amount: int) -> dict[str, Any]:
    """Preview a sell quote from the public marketplace API."""
    return await _fetch_public_json(f"/api/marketplace/quote/sell?asset_id={asset_id}&amount={amount}")


@mcp.tool()
async def get_agent_activity(agent_name: str) -> dict[str, Any]:
    """Fetch recent activity for one protocol agent."""
    normalized = agent_name.strip().lower()
    if normalized not in ALLOWED_AGENT_NAMES:
        return _error("agent_name must be one of: senator, curator, social")
    return await _fetch_public_json(f"/api/agents/{normalized}/activity")


@mcp.tool()
async def get_governance_overview() -> dict[str, Any]:
    """Fetch high-level governance counters from the public API."""
    return await _fetch_public_json("/api/governance/overview")


@mcp.tool()
async def list_governance_proposals(limit: int = 10) -> dict[str, Any]:
    """Fetch governance proposals and return the newest N results."""
    result = await _fetch_public_json("/api/governance/proposals")
    if not result.get("ok"):
        return result

    data = result["data"]
    proposals = data.get("proposals", [])
    return {
        "ok": True,
        "source": result["source"],
        "data": {
            **data,
            "returned": max(0, limit),
            "proposals": proposals[: max(0, limit)],
        },
    }


@mcp.tool()
async def get_governance_proposal(proposal_id: int) -> dict[str, Any]:
    """Fetch one governance proposal by numeric identifier."""
    return await _fetch_public_json(f"/api/governance/proposals/{proposal_id}")


@mcp.tool()
async def get_transparency_snapshot() -> dict[str, Any]:
    """Fetch a compact transparency snapshot from the public API."""
    supply, treasury, burns, governance = await asyncio.gather(
        _fetch_public_json("/api/transparency/supply"),
        _fetch_public_json("/api/transparency/treasury"),
        _fetch_public_json("/api/transparency/burns"),
        _fetch_public_json("/api/transparency/governance"),
    )
    return {
        "ok": all(item.get("ok") for item in (supply, treasury, burns, governance)),
        "source": API_URL,
        "data": {
            "supply": supply.get("data") if supply.get("ok") else supply,
            "treasury": treasury.get("data") if treasury.get("ok") else treasury,
            "burns": burns.get("data") if burns.get("ok") else burns,
            "governance": governance.get("data") if governance.get("ok") else governance,
        },
    }


if __name__ == "__main__":
    mcp.run()
