import asyncio
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

# API Routers
from src.api.health import router as health_router
from src.api.transparency import router as transparency_router
from src.api.governance import router as governance_router
from src.api.agents_api import router as agents_router

# Services
from src.services.cache import get_cache_service
from src.services.algorand import get_algorand_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the application."""
    # ── Startup ──
    cache = get_cache_service()
    await cache.connect()
    print("Redis cache: connected" if cache.available else "Redis cache: unavailable (running without cache)")

    yield

    # ── Shutdown ──
    await cache.disconnect()
    algo = get_algorand_service()
    await algo.close()
    print("Services shut down cleanly.")


app = FastAPI(
    title="PureCortex API Gateway",
    version="0.7.0",
    lifespan=lifespan,
)

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

# ── Register Routers ──
app.include_router(health_router)
app.include_router(transparency_router)
app.include_router(governance_router)
app.include_router(agents_router)

# ── Security Proxy ──
proxy = PermissionProxy(PermissionTier.READ_ONLY)

# ── Initialize Orchestrator ──
try:
    orchestrator = ConsensusOrchestrator()
except Exception as e:
    print(f"Warning: Failed to initialize orchestrator: {e}")
    orchestrator = None


# ── WebSocket Connection Manager ──
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
