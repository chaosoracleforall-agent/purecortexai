"""PURECORTEX Python SDK client."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any, Literal
from urllib.parse import urlencode, urlparse, urlunparse

import httpx


DEFAULT_BASE_URL = "https://purecortex.ai"
AgentName = Literal["senator", "curator", "social"]
VoteChoice = Literal["for", "against"]


class PureCortexAPIError(RuntimeError):
    """Raised when the PURECORTEX API returns a non-success response."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        payload: Any | None = None,
    ) -> None:
        self.status_code = status_code
        self.detail = detail
        self.payload = payload
        super().__init__(f"PURECORTEX API error {status_code}: {detail}")

    @classmethod
    def from_response(cls, response: httpx.Response) -> "PureCortexAPIError":
        payload: Any | None = None
        detail = response.text
        content_type = response.headers.get("content-type", "")
        if "application/json" in content_type:
            try:
                payload = response.json()
            except Exception:
                payload = None
            if isinstance(payload, Mapping):
                detail = str(payload.get("detail") or payload.get("error") or detail)
        return cls(status_code=response.status_code, detail=detail, payload=payload)


class PureCortexClient:
    """Synchronous PURECORTEX SDK client with WebSocket bootstrap helpers."""

    def __init__(
        self,
        *,
        base_url: str = DEFAULT_BASE_URL,
        api_key: str | None = None,
        timeout: float = 10.0,
        client: httpx.Client | None = None,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self._owns_client = client is None
        self._client = client or httpx.Client(base_url=self.base_url, timeout=timeout)

    def __enter__(self) -> "PureCortexClient":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @property
    def ws_base_url(self) -> str:
        parsed = urlparse(self.base_url)
        scheme = "wss" if parsed.scheme == "https" else "ws"
        return urlunparse((scheme, parsed.netloc, "", "", "", "")).rstrip("/")

    def websocket_url(self, session_token: str) -> str:
        query = urlencode({"session": session_token})
        return f"{self.ws_base_url}/ws/chat?{query}"

    def health(self) -> dict[str, Any]:
        return self._request("GET", "/health")

    def supply(self) -> dict[str, Any]:
        return self._request("GET", "/api/transparency/supply")

    def treasury(self) -> dict[str, Any]:
        return self._request("GET", "/api/transparency/treasury")

    def burns(self) -> dict[str, Any]:
        return self._request("GET", "/api/transparency/burns")

    def governance_transparency(self) -> dict[str, Any]:
        return self._request("GET", "/api/transparency/governance")

    def transparency_agents(self) -> dict[str, Any]:
        return self._request("GET", "/api/transparency/agents")

    def list_agents(self) -> dict[str, Any]:
        return self._request("GET", "/api/agents/registry")

    def marketplace_config(self) -> dict[str, Any]:
        return self._request("GET", "/api/marketplace/config")

    def marketplace_agent_state(self, asset_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/marketplace/agents/{asset_id}/state")

    def preview_buy_quote(self, *, asset_id: int, amount: int) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/marketplace/quote/buy",
            params={"asset_id": asset_id, "amount": amount},
        )

    def preview_sell_quote(self, *, asset_id: int, amount: int) -> dict[str, Any]:
        return self._request(
            "GET",
            "/api/marketplace/quote/sell",
            params={"asset_id": asset_id, "amount": amount},
        )

    def agent_activity(self, agent_name: AgentName) -> dict[str, Any]:
        return self._request("GET", f"/api/agents/{agent_name}/activity")

    def chat(self, agent_name: AgentName, message: str) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/agents/{agent_name}/chat",
            json_body={"message": message},
            require_api_key=True,
        )

    def create_chat_session(self, *, api_key: str | None = None) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/chat/session",
            require_api_key=True,
            api_key=api_key,
        )

    async def websocket_chat(
        self,
        messages: Iterable[str],
        *,
        session_token: str | None = None,
        api_key: str | None = None,
    ) -> list[str]:
        import websockets

        token = session_token or self.create_chat_session(api_key=api_key)["session_token"]
        uri = self.websocket_url(token)
        responses: list[str] = []
        async with websockets.connect(uri) as websocket:
            for message in messages:
                await websocket.send(message)
                responses.append(await websocket.recv())
        return responses

    def constitution(self) -> dict[str, Any]:
        return self._request("GET", "/api/governance/constitution")

    def governance_overview(self) -> dict[str, Any]:
        return self._request("GET", "/api/governance/overview")

    def list_proposals(self) -> dict[str, Any]:
        return self._request("GET", "/api/governance/proposals")

    def proposal(self, proposal_id: int) -> dict[str, Any]:
        return self._request("GET", f"/api/governance/proposals/{proposal_id}")

    def onchain_proposals(self) -> dict[str, Any]:
        return self._request("GET", "/api/governance/onchain")

    def create_proposal(
        self,
        *,
        title: str,
        description: str,
        proposer: str,
        proposal_type: str = "general",
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/governance/proposals",
            json_body={
                "title": title,
                "description": description,
                "type": proposal_type,
                "proposer": proposer,
            },
        )

    def review_proposal(
        self,
        proposal_id: int,
        *,
        compliant: bool,
        analysis: str,
        recommendation: str,
        curator_name: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/governance/proposals/{proposal_id}/review",
            json_body={
                "compliant": compliant,
                "analysis": analysis,
                "recommendation": recommendation,
                "curator_name": curator_name,
            },
        )

    def vote(
        self,
        proposal_id: int,
        *,
        voter: str,
        vote: VoteChoice,
        weight: int = 1,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            f"/api/governance/proposals/{proposal_id}/vote",
            json_body={
                "voter": voter,
                "vote": vote,
                "weight": weight,
            },
        )

    def bootstrap_admin_key(
        self,
        *,
        owner: str = "bootstrap-admin",
        bootstrap_token: str,
    ) -> dict[str, Any]:
        return self._request(
            "POST",
            "/api/admin/bootstrap",
            headers={"X-Bootstrap-Token": bootstrap_token},
            json_body={"owner": owner},
        )

    def create_api_key(
        self,
        *,
        owner: str,
        tier: str = "free",
        admin_secret: str | None = None,
        admin_api_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if admin_secret:
            headers["X-Admin-Secret"] = admin_secret
        return self._request(
            "POST",
            "/api/admin/keys",
            headers=headers,
            api_key=admin_api_key,
            json_body={"owner": owner, "tier": tier},
        )

    def revoke_api_key(
        self,
        *,
        api_key_to_revoke: str,
        admin_secret: str | None = None,
        admin_api_key: str | None = None,
    ) -> dict[str, Any]:
        headers: dict[str, str] = {}
        if admin_secret:
            headers["X-Admin-Secret"] = admin_secret
        return self._request(
            "POST",
            "/api/admin/keys/revoke",
            headers=headers,
            api_key=admin_api_key,
            json_body={"api_key": api_key_to_revoke},
        )

    def _request(
        self,
        method: str,
        path: str,
        *,
        require_api_key: bool = False,
        api_key: str | None = None,
        headers: Mapping[str, str] | None = None,
        json_body: Any | None = None,
        params: Mapping[str, Any] | None = None,
    ) -> dict[str, Any]:
        request_headers = self._headers(
            require_api_key=require_api_key,
            api_key=api_key,
            headers=headers,
        )
        response = self._client.request(
            method,
            path,
            headers=request_headers,
            json=json_body,
            params=params,
        )
        if not response.is_success:
            raise PureCortexAPIError.from_response(response)
        return response.json()

    def _headers(
        self,
        *,
        require_api_key: bool = False,
        api_key: str | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> dict[str, str]:
        merged: dict[str, str] = {"Accept": "application/json"}
        if headers:
            merged.update(headers)

        token = api_key or self.api_key
        if require_api_key and not token:
            raise ValueError("PURECORTEX API key is required for this operation")
        if token:
            merged["X-API-Key"] = token

        if "Content-Type" not in merged:
            merged["Content-Type"] = "application/json"
        return merged
