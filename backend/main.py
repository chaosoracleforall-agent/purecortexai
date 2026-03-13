import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

app = FastAPI(title="PureCortex API Gateway & Chat", version="1.0.0")

# Security Proxy Initialization
proxy = PermissionProxy(PermissionTier.READ_ONLY)

# Initialize Orchestrator
try:
    orchestrator = ConsensusOrchestrator()
except Exception as e:
    print(f"Warning: Failed to initialize orchestrator: {e}")
    orchestrator = None

# ... (ConnectionManager code) ...

@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            
            if orchestrator:
                system_prompt = (
                    "You are a PureCortex Autonomous Agent. "
                    "Engage the user. Respond ONLY in valid JSON with 'action' (REPLY) and 'message'."
                )
                
                decision = await orchestrator.decide_action(system_prompt, data)
                
                # HARDENED: Verify permission before executing
                if decision and proxy.validate_action(decision):
                    response_text = decision.get("message", "Cognition complete.")
                else:
                    response_text = "Action blocked by PureCortex Security Sandbox."
            else:
                response_text = f"Mock Agent Reply to: {data}"
                
            await manager.send_personal_message(response_text, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
