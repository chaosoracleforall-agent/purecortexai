"""
Algorand Service Layer for PURECORTEX.

Uses AlgoNode indexer (no auth required) to query on-chain state
for agent tokens, asset info, account balances, and transactions.
"""

import logging
import os

import httpx
from typing import Any, Optional

from src.services.protocol_config import (
    CORTEX_ASSET_ID,
    FACTORY_APP_ID,
    GOVERNANCE_APP_ID,
    NETWORK as DEFAULT_NETWORK,
    STAKING_APP_ID,
    TREASURY_APP_ID,
)

logger = logging.getLogger("purecortex.algorand")

# AlgoNode Indexer base URLs
MAINNET_INDEXER = "https://mainnet-idx.4160.nodely.dev/v2"
TESTNET_INDEXER = "https://testnet-idx.4160.nodely.dev/v2"


class AlgorandService:
    """Async client for querying the Algorand indexer."""

    def __init__(self, network: Optional[str] = None):
        net = (network or os.getenv("ALGORAND_NETWORK", DEFAULT_NETWORK)).strip().lower()
        if net == "testnet":
            self.base_url = TESTNET_INDEXER
        else:
            self.base_url = MAINNET_INDEXER
        self._client: Optional[httpx.AsyncClient] = None

    async def _get_client(self) -> httpx.AsyncClient:
        if self._client is None or self._client.is_closed:
            self._client = httpx.AsyncClient(
                base_url=self.base_url,
                timeout=15.0,
                headers={"Accept": "application/json"},
            )
        return self._client

    async def close(self):
        if self._client and not self._client.is_closed:
            await self._client.aclose()

    async def get_application_info(self, app_id: int) -> dict[str, Any]:
        """Get application state from the indexer."""
        client = await self._get_client()
        resp = await client.get(f"/applications/{app_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_asset_info(self, asset_id: int) -> dict[str, Any]:
        """Get asset details (name, unit name, total supply, decimals, etc.)."""
        client = await self._get_client()
        resp = await client.get(f"/assets/{asset_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_account_info(self, address: str) -> dict[str, Any]:
        """Get account balances (ALGO + ASA holdings)."""
        client = await self._get_client()
        resp = await client.get(f"/accounts/{address}")
        resp.raise_for_status()
        return resp.json()

    async def search_transactions(
        self,
        address: Optional[str] = None,
        asset_id: Optional[int] = None,
        min_round: Optional[int] = None,
        limit: int = 20,
        next_token: Optional[str] = None,
    ) -> dict[str, Any]:
        """Search transactions with optional filters and pagination."""
        params: dict[str, Any] = {"limit": limit}
        if address:
            params["address"] = address
        if asset_id:
            params["asset-id"] = asset_id
        if min_round:
            params["min-round"] = min_round
        if next_token:
            params["next"] = next_token

        client = await self._get_client()
        resp = await client.get("/transactions", params=params)
        resp.raise_for_status()
        return resp.json()

    async def get_agent_tokens(
        self,
        factory_app_id: int = FACTORY_APP_ID,
        max_pages: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Get all agent assets created by the factory application.
        Paginates through results using the indexer's next-token.
        """
        client = await self._get_client()
        agents = []
        next_token: Optional[str] = None

        for _ in range(max_pages):
            params: dict[str, Any] = {
                "application-id": factory_app_id,
                "tx-type": "appl",
                "limit": 100,
            }
            if next_token:
                params["next"] = next_token

            resp = await client.get("/transactions", params=params)
            resp.raise_for_status()
            data = resp.json()

            for txn in data.get("transactions", []):
                inner_txns = txn.get("inner-txns", [])
                for inner in inner_txns:
                    if inner.get("tx-type") == "acfg" and inner.get("created-asset-index"):
                        asset_id = inner["created-asset-index"]
                        asset_config = inner.get("asset-config-transaction", {})
                        params_data = asset_config.get("params", {})
                        agents.append({
                            "asset_id": asset_id,
                            "name": params_data.get("name", "Unknown"),
                            "unit_name": params_data.get("unit-name", ""),
                            "total": params_data.get("total", 0),
                            "decimals": params_data.get("decimals", 0),
                            "creator_txn": txn.get("id", ""),
                        })

            next_token = data.get("next-token")
            if not next_token:
                break

        return agents


# Module-level singleton
_service: Optional[AlgorandService] = None


def get_algorand_service() -> AlgorandService:
    """Get or create the singleton AlgorandService instance."""
    global _service
    if _service is None:
        _service = AlgorandService()
    return _service
