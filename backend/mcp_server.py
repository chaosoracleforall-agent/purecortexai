import asyncio
from mcp.server.fastmcp import FastMCP
from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

# Create an MCP server
mcp = FastMCP("PureCortex", description="PureCortex Dual-Brain Orchestrator MCP Server")

# Security Proxy Initialization
proxy = PermissionProxy(PermissionTier.READ_ONLY)

# Global orchestrator instance
try:
    orchestrator = ConsensusOrchestrator()
except Exception:
    orchestrator = None

@mcp.tool()
async def get_dual_brain_consensus(prompt: str) -> str:
    if not orchestrator:
        return "Error: Orchestrator not initialized."
        
    system_prompt = (
        "You are participating in an MCP network. Formulate a consensus response. "
        "Respond ONLY in valid JSON with 'action' (RESPOND) and 'message'."
    )
    
    decision = await orchestrator.decide_action(system_prompt, prompt)
    
    # HARDENED: Verify permission before responding
    if decision and proxy.validate_action(decision):
        return decision.get("message", "Consensus reached.")
    else:
        return "Action blocked by PureCortex Security Proxy."

if __name__ == "__main__":
    # Start the MCP server using standard I/O (default for MCP)
    print("Starting PureCortex MCP Server...")
    mcp.run()
