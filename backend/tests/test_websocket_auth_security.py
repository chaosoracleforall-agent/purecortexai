from __future__ import annotations

import importlib
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from starlette.websockets import WebSocketDisconnect


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def _load_app(monkeypatch):
    monkeypatch.setenv("ENABLE_AGENTS", "0")
    monkeypatch.setenv("REDIS_URL", "redis://127.0.0.1:6399/0")
    for module_name in ["main"]:
        sys.modules.pop(module_name, None)
    main = importlib.import_module("main")
    return main.app


class _FakeApiKeyManager:
    async def validate_key(self, _token: str):
        return {"tier": "free"}


class _FakeChatSessionManager:
    def __init__(self, valid: bool):
        self._valid = valid

    async def validate_session(self, _token: str):
        return {"tier": "free"} if self._valid else None

    async def revoke_session(self, _token: str):
        return None


def test_websocket_fails_closed_when_auth_backends_unavailable(monkeypatch):
    app = _load_app(monkeypatch)
    app.state.api_key_manager = None
    app.state.chat_session_manager = None

    with TestClient(app) as client:
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/chat"):
                pass
        assert exc_info.value.code == 4003


def test_websocket_requires_chat_session_when_only_api_manager_exists(monkeypatch):
    app = _load_app(monkeypatch)

    with TestClient(app) as client:
        # Lifespan startup can reset app state, so set test doubles after startup.
        app.state.api_key_manager = _FakeApiKeyManager()
        app.state.chat_session_manager = None
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/chat"):
                pass
        assert exc_info.value.code == 4001


def test_websocket_rejects_invalid_session_token(monkeypatch):
    app = _load_app(monkeypatch)

    with TestClient(app) as client:
        app.state.api_key_manager = None
        app.state.chat_session_manager = _FakeChatSessionManager(valid=False)
        with pytest.raises(WebSocketDisconnect) as exc_info:
            with client.websocket_connect("/ws/chat?session=bad-token"):
                pass
        assert exc_info.value.code == 4001
