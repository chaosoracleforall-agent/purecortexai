import asyncio
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

app = FastAPI(title="PureCortex API Gateway", version="0.6.0")

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "https://purecortex.ai",
        "http://localhost:3000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Security Proxy Initialization
proxy = PermissionProxy(PermissionTier.READ_ONLY)

# Initialize Orchestrator
try:
    orchestrator = ConsensusOrchestrator()
except Exception as e:
    print(f"Warning: Failed to initialize orchestrator: {e}")
    orchestrator = None


class ConnectionManager:
    """Manages active WebSocket connections."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.get("/health")
async def health():
    return {
        "status": "ok",
        "orchestrator_active": orchestrator is not None,
        "version": "0.6.0",
    }


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()

            # Enforce max message length
            if len(data) > 4096:
                await manager.send_personal_message(
                    "Message too long. Maximum 4096 characters.", websocket
                )
                continue

            if orchestrator:
                system_prompt = (
                    "You are a PureCortex Autonomous Agent. "
                    "Engage the user. Respond ONLY in valid JSON with 'action' (REPLY) and 'message'."
                )

                decision = await orchestrator.decide_action(system_prompt, data)

                if decision and proxy.validate_action(decision):
                    response_text = decision.get("message", "Cognition complete.")
                else:
                    response_text = "Action blocked by PureCortex Security Sandbox."
            else:
                response_text = f"Mock Agent Reply to: {data}"

            await manager.send_personal_message(response_text, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
