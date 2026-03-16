import asyncio
import logging
import os
import time
from contextlib import asynccontextmanager

import redis.asyncio as aioredis

# Configure logging for all PURECORTEX modules
logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
logging.getLogger("purecortex").setLevel(logging.INFO)

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from orchestrator import ConsensusOrchestrator
from sandboxing import PermissionProxy, PermissionTier

# API Routers
from src.api.health import router as health_router
from src.api.transparency import router as transparency_router
from src.api.governance import router as governance_router
from src.api.agents_api import router as agents_router
from src.api.chat import router as chat_router
from src.api.admin import router as admin_router, set_api_key_manager
from src.api.developer_access import router as developer_access_router
from src.api.internal_admin import router as internal_admin_router

# Auth
from src.api.auth import APIKeyMiddleware
from src.core.settings import get_settings
from src.services.api_keys import APIKeyManager
from src.services.chat_sessions import ChatSessionManager
from src.services.request_ip import resolve_client_ip

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
    logger.info("Redis cache: %s", "connected" if cache.available else "unavailable (running without cache)")

    # ── Initialize API Key Auth ──
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
    try:
        _redis_rl = aioredis.from_url(redis_url, decode_responses=True, socket_connect_timeout=5)
        await _redis_rl.ping()
        api_key_mgr = APIKeyManager(_redis_rl)
        chat_session_mgr = ChatSessionManager(_redis_rl)
        set_api_key_manager(api_key_mgr)
        app.state.api_key_manager = api_key_mgr
        app.state.chat_session_manager = chat_session_mgr
        app.state.redis_rate_limit = _redis_rl
        logger.info("API key authentication initialized.")
    except Exception as e:
        logger.warning("Redis for API keys unavailable: %s — protected routes will fail closed", e)
        set_api_key_manager(None)
        app.state.api_key_manager = None
        app.state.chat_session_manager = None
        _redis_rl = None
        app.state.redis_rate_limit = None

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
    if getattr(app.state, "redis_rate_limit", None):
        await app.state.redis_rate_limit.aclose()
    algo = get_algorand_service()
    await algo.close()
    logger.info("Services shut down cleanly.")


app = FastAPI(
    title="PURECORTEX API Gateway",
    version="0.7.0",
    lifespan=lifespan,
)

app.state.api_key_manager = None
app.state.chat_session_manager = None
app.state.redis_rate_limit = None

app.add_middleware(APIKeyMiddleware)

# CORS configuration — environment-aware
_cors_origins_env = os.getenv("CORS_ALLOWED_ORIGINS", "")
if _cors_origins_env:
    _cors_origins = [o.strip() for o in _cors_origins_env.split(",") if o.strip()]
elif os.getenv("ENVIRONMENT", "development") == "production":
    _cors_origins = ["https://purecortex.ai"]
else:
    _cors_origins = ["https://purecortex.ai", "http://localhost:3000"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization", "X-API-Key"],
)

# ── Rate Limiting (Redis-backed) ──
RATE_LIMIT_WINDOW = 60    # seconds
RATE_LIMIT_MAX = 60       # requests per window


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    settings = get_settings()
    client_ip = resolve_client_ip(
        request.headers,
        request.client.host if request.client else None,
        trust_proxy_headers=settings.trust_proxy_headers,
        trusted_proxy_cidrs=settings.trusted_proxy_cidrs,
    )
    request.state.client_ip = client_ip
    redis_rl = getattr(request.app.state, "redis_rate_limit", None)
    if redis_rl:
        try:
            rl_key = f"ip_ratelimit:{client_ip}"
            count = await redis_rl.incr(rl_key)
            if count == 1:
                await redis_rl.expire(rl_key, RATE_LIMIT_WINDOW)
            if count > RATE_LIMIT_MAX:
                return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded. Try again later."})
        except Exception:
            # If Redis is down, allow the request through rather than blocking
            pass
    response = await call_next(request)
    return response


# ── Global Exception Handler ──
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled exception on %s: %s", request.url.path, exc)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# ── Register Routers ──
app.include_router(health_router)
app.include_router(transparency_router)
app.include_router(governance_router)
app.include_router(agents_router)
app.include_router(chat_router)
app.include_router(admin_router)
app.include_router(developer_access_router)
app.include_router(internal_admin_router)

# ── Security Proxy ──
proxy = PermissionProxy(PermissionTier.READ_ONLY)

# ── Initialize Orchestrator ──
try:
    orchestrator = ConsensusOrchestrator()
except Exception as e:
    logger.warning("Failed to initialize orchestrator: %s", e)
    orchestrator = None


# ── WebSocket Connection Manager ──
MAX_WS_CONNECTIONS = 100
WS_RATE_LIMIT_PER_SEC = 2  # max messages per second per connection


class ConnectionManager:
    """Manages active WebSocket connections with limits."""

    def __init__(self, max_connections: int = MAX_WS_CONNECTIONS):
        self.active_connections: list[WebSocket] = []
        self.max_connections = max_connections

    async def connect(self, websocket: WebSocket) -> bool:
        if len(self.active_connections) >= self.max_connections:
            await websocket.close(code=1013, reason="Server at capacity")
            return False
        await websocket.accept()
        self.active_connections.append(websocket)
        return True

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)

    async def broadcast(self, message: str):
        for connection in self.active_connections:
            await connection.send_text(message)


manager = ConnectionManager()


@app.websocket("/ws/chat")
async def websocket_chat(websocket: WebSocket):
    session_token = websocket.query_params.get("session")
    legacy_token = websocket.query_params.get("token")
    api_key_mgr = getattr(websocket.app.state, "api_key_manager", None)
    chat_session_mgr = getattr(websocket.app.state, "chat_session_manager", None)

    if chat_session_mgr and session_token:
        key_data = await chat_session_mgr.validate_session(session_token)
        if not key_data:
            await websocket.close(code=4001, reason="Invalid or expired chat session")
            return
    elif api_key_mgr and legacy_token:
        key_data = await api_key_mgr.validate_key(legacy_token)
        if not key_data:
            await websocket.close(code=4001, reason="Invalid API key")
            return
    elif api_key_mgr:
        await websocket.close(code=4001, reason="Chat session required. Bootstrap via POST /api/chat/session first.")
        return

    connected = await manager.connect(websocket)
    if not connected:
        return

    last_message_time = 0.0
    try:
        while True:
            data = await websocket.receive_text()

            # Per-connection rate limit
            now = time.time()
            if now - last_message_time < (1.0 / WS_RATE_LIMIT_PER_SEC):
                await manager.send_personal_message(
                    "Rate limited. Please slow down.", websocket
                )
                continue
            last_message_time = now

            # Enforce max message length
            if len(data) > 4096:
                await manager.send_personal_message(
                    "Message too long. Maximum 4096 characters.", websocket
                )
                continue

            if orchestrator:
                system_prompt = (
                    "You are a PURECORTEX Autonomous Agent. "
                    "Engage the user. Respond ONLY in valid JSON with 'action' (REPLY) and 'message'."
                )

                decision = await orchestrator.decide_action(system_prompt, data)

                if decision and proxy.validate_action(decision):
                    response_text = decision.get("message", "Cognition complete.")
                else:
                    response_text = "Action blocked by PURECORTEX Security Sandbox."
            else:
                response_text = "PURECORTEX agent is currently offline."

            await manager.send_personal_message(response_text, websocket)
    except WebSocketDisconnect:
        manager.disconnect(websocket)
