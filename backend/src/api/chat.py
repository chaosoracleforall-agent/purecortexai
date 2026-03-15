"""Chat session bootstrap API for PURECORTEX."""

from __future__ import annotations

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel


router = APIRouter(prefix="/api/chat", tags=["chat"])


class ChatSessionResponse(BaseModel):
    session_token: str
    expires_at: str
    ttl_seconds: int
    owner: str
    tier: str


@router.post("/session", response_model=ChatSessionResponse)
async def create_chat_session(request: Request):
    """Create a short-lived websocket session from an authenticated API key."""
    chat_session_manager = getattr(request.app.state, "chat_session_manager", None)
    api_key_data = getattr(request.state, "api_key_data", None)
    api_key = request.headers.get("X-API-Key")

    if chat_session_manager is None:
        raise HTTPException(status_code=503, detail="Chat sessions unavailable")
    if not api_key_data or not api_key:
        raise HTTPException(status_code=401, detail="API key required")

    session = await chat_session_manager.create_session(
        owner=api_key_data.get("owner", "unknown"),
        tier=api_key_data.get("tier", "free"),
        api_key=api_key,
    )
    return ChatSessionResponse(**session)
