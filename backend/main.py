import asyncio
import logging
import os
from contextlib import asynccontextmanager

# Configure logging for all PureCortex modules
logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
logging.getLogger("purecortex").setLevel(logging.INFO)

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

# Agents
from src.agents.memory import AgentMemory
from src.agents.senator_agent import SenatorAgent
from src.agents.curator_agent import CuratorAgent
from src.agents.social_agent import SocialAgent
from src.agents.orchestrator_loop import AgentOrchestrationLoop

logger = logging.getLogger("purecortex")

# Global reference so agent APIs can access it
_agent_loop: AgentOrchestrationLoop | None = None


def get_agent_loop() -> AgentOrchestrationLoop | None:
    return _agent_loop


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup / shutdown lifecycle for the application."""
    global _agent_loop

    # ── Startup ──
    cache = get_cache_service()
    await cache.connect()
    print("Redis cache: connected" if cache.available else "Redis cache: unavailable (running without cache)")

    # ── Start Agent Orchestration Loop ──
    if orchestrator and os.getenv("ENABLE_AGENTS", "1") == "1":
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            senator_memory = AgentMemory("senator", redis_url=redis_url)
            curator_memory = AgentMemory("curator", redis_url=redis_url)
            social_memory = AgentMemory("social", redis_url=redis_url)

            senator = SenatorAgent(orchestrator=orchestrator, memory=senator_memory)
            curator = CuratorAgent(orchestrator=orchestrator, memory=curator_memory)
            social = SocialAgent(orchestrator=orchestrator, memory=social_memory)

            _agent_loop = AgentOrchestrationLoop(
                senator=senator,
                curator=curator,
                social=social,
            )
            await _agent_loop.start()
            logger.info("Agent orchestration loop started.")
        except Exception as e:
            logger.error("Failed to start agent orchestration loop: %s", e)
            _agent_loop = None
    else:
        logger.info("Agent orchestration loop disabled (no orchestrator or ENABLE_AGENTS=0).")

    yield

    # ── Shutdown ──
    if _agent_loop:
        await _agent_loop.stop()
        logger.info("Agent orchestration loop stopped.")

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
