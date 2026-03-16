"""
Algorand Service Layer for PURECORTEX.

Uses AlgoNode indexer and algod APIs to query on-chain state
for agent tokens, asset info, account balances, staking state,
delegation boxes, and transactions.
"""

import asyncio
import base64
import logging
import os
from typing import Any, Optional

import httpx
from algosdk.encoding import decode_address, encode_address, is_valid_address

from src.services.protocol_config import (
    CORTEX_ASSET_ID,
    FACTORY_APP_ID,
    GOVERNANCE_APP_ID,
    NETWORK as DEFAULT_NETWORK,
    STAKING_APP_ID,
    TREASURY_APP_ID,
)

logger = logging.getLogger("purecortex.algorand")

# AlgoNode base URLs
MAINNET_INDEXER = "https://mainnet-idx.4160.nodely.dev/v2"
TESTNET_INDEXER = "https://testnet-idx.4160.nodely.dev/v2"
MAINNET_ALGOD = "https://mainnet-api.algonode.cloud/v2"
TESTNET_ALGOD = "https://testnet-api.algonode.cloud/v2"


class AlgorandService:
    """Async client for querying the Algorand indexer."""

    def __init__(self, network: Optional[str] = None):
        net = (network or os.getenv("ALGORAND_NETWORK", DEFAULT_NETWORK)).strip().lower()
        if net == "testnet":
            self.indexer_base_url = TESTNET_INDEXER
            self.algod_base_url = TESTNET_ALGOD
        else:
            self.indexer_base_url = MAINNET_INDEXER
            self.algod_base_url = MAINNET_ALGOD
        self._indexer_client: Optional[httpx.AsyncClient] = None
        self._algod_client: Optional[httpx.AsyncClient] = None

    async def _get_indexer_client(self) -> httpx.AsyncClient:
        if self._indexer_client is None or self._indexer_client.is_closed:
            self._indexer_client = httpx.AsyncClient(
                base_url=self.indexer_base_url,
                timeout=15.0,
                headers={"Accept": "application/json"},
            )
        return self._indexer_client

    async def _get_algod_client(self) -> httpx.AsyncClient:
        if self._algod_client is None or self._algod_client.is_closed:
            self._algod_client = httpx.AsyncClient(
                base_url=self.algod_base_url,
                timeout=15.0,
                headers={"Accept": "application/json"},
            )
        return self._algod_client

    async def close(self):
        if self._indexer_client and not self._indexer_client.is_closed:
            await self._indexer_client.aclose()
        if self._algod_client and not self._algod_client.is_closed:
            await self._algod_client.aclose()

    async def get_application_info(self, app_id: int) -> dict[str, Any]:
        """Get application state from algod."""
        client = await self._get_algod_client()
        resp = await client.get(f"/applications/{app_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_node_status(self) -> dict[str, Any]:
        """Get current algod node status."""
        client = await self._get_algod_client()
        resp = await client.get("/status")
        resp.raise_for_status()
        return resp.json()

    async def get_asset_info(self, asset_id: int) -> dict[str, Any]:
        """Get asset details (name, unit name, total supply, decimals, etc.)."""
        client = await self._get_indexer_client()
        resp = await client.get(f"/assets/{asset_id}")
        resp.raise_for_status()
        return resp.json()

    async def get_account_info(self, address: str) -> dict[str, Any]:
        """Get account balances (ALGO + ASA holdings)."""
        client = await self._get_indexer_client()
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

        client = await self._get_indexer_client()
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
        client = await self._get_indexer_client()
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

    async def get_application_global_state(self, app_id: int) -> dict[str, Any]:
        """Return decoded global-state keys for an application."""
        info = await self.get_application_info(app_id)
        decoded: dict[str, Any] = {}
        for item in info.get("params", {}).get("global-state", []):
            key = base64.b64decode(item["key"]).decode(errors="ignore")
            value = item.get("value", {})
            if value.get("type") == 1:
                decoded[key] = base64.b64decode(value.get("bytes", ""))
            else:
                decoded[key] = value.get("uint", 0)
        return decoded

    async def list_application_boxes(
        self,
        app_id: int,
        *,
        max_boxes: int = 1000,
    ) -> list[bytes]:
        """List raw box names for an application."""
        client = await self._get_algod_client()
        next_token: Optional[str] = None
        raw_names: list[bytes] = []

        while len(raw_names) < max_boxes:
            params: dict[str, Any] = {
                "max": min(1000, max_boxes - len(raw_names)),
            }
            if next_token:
                params["next"] = next_token
            resp = await client.get(f"/applications/{app_id}/boxes", params=params)
            if resp.status_code == 404:
                return []
            resp.raise_for_status()
            payload = resp.json()
            for box in payload.get("boxes", []):
                name = box.get("name") if isinstance(box, dict) else None
                if not name:
                    continue
                try:
                    raw_names.append(base64.b64decode(name))
                except Exception:
                    logger.warning("Unable to decode box name for app %s: %r", app_id, name)
            next_token = payload.get("next-token")
            if not next_token:
                break

        return raw_names

    async def get_application_box(self, app_id: int, key: bytes) -> bytes | None:
        """Read raw box value by raw box key bytes."""
        client = await self._get_algod_client()
        encoded_name = base64.b64encode(key).decode()
        resp = await client.get(
            f"/applications/{app_id}/box",
            params={"name": f"b64:{encoded_name}"},
        )
        if resp.status_code == 404:
            return None
        resp.raise_for_status()
        payload = resp.json()
        value = payload.get("value")
        if not value:
            return None
        return base64.b64decode(value)

    async def get_staking_overview(
        self,
        staking_app_id: int = STAKING_APP_ID,
    ) -> dict[str, Any]:
        """Read the live staking contract configuration and totals."""
        global_state, node_status = await asyncio.gather(
            self.get_application_global_state(staking_app_id),
            self.get_node_status(),
        )
        return {
            "app_id": staking_app_id,
            "cortex_asset_id": int(global_state.get("cortex_token", CORTEX_ASSET_ID)),
            "total_staked": int(global_state.get("total_staked", 0)),
            "reward_pool": int(global_state.get("reward_pool", 0)),
            "min_lock_days": int(global_state.get("MIN_LOCK_DAYS", 7)),
            "max_lock_days": int(global_state.get("MAX_LOCK_DAYS", 1460)),
            "max_boost_bps": int(global_state.get("MAX_BOOST", 2500)),
            "current_round": int(node_status.get("last-round", 0)),
        }

    async def get_stake_snapshot(
        self,
        address: str,
        staking_app_id: int = STAKING_APP_ID,
    ) -> dict[str, Any] | None:
        """Read a user's live stake and delegation snapshot from box storage."""
        if not is_valid_address(address):
            raise ValueError(f"Invalid Algorand address: {address}")

        raw_address = decode_address(address)
        stake_key = b"s" + raw_address
        delegation_key = b"d" + raw_address

        stake_data, delegation_data = await asyncio.gather(
            self.get_application_box(staking_app_id, stake_key),
            self.get_application_box(staking_app_id, delegation_key),
        )
        if not stake_data or len(stake_data) != 32:
            return None

        amount = int.from_bytes(stake_data[0:8], "big")
        unlock_round = int.from_bytes(stake_data[8:16], "big")
        ve_power = int.from_bytes(stake_data[16:24], "big")
        boost_bps = int.from_bytes(stake_data[24:32], "big")

        delegate = None
        if delegation_data and len(delegation_data) == 32:
            delegate = encode_address(delegation_data)

        return {
            "address": address,
            "amount": amount,
            "unlock_round": unlock_round,
            "ve_power": ve_power,
            "boost_bps": boost_bps,
            "delegate": delegate,
        }

    async def list_stake_snapshots(
        self,
        staking_app_id: int = STAKING_APP_ID,
        *,
        max_boxes: int = 1000,
    ) -> list[dict[str, Any]]:
        """List all live stake snapshots from the staking contract."""
        box_names = await self.list_application_boxes(staking_app_id, max_boxes=max_boxes)
        stake_names = [name for name in box_names if len(name) == 33 and name.startswith(b"s")]
        delegation_names = [name for name in box_names if len(name) == 33 and name.startswith(b"d")]

        if not stake_names:
            return []

        stake_values = await asyncio.gather(
            *(self.get_application_box(staking_app_id, name) for name in stake_names)
        )
        delegation_values = await asyncio.gather(
            *(self.get_application_box(staking_app_id, name) for name in delegation_names)
        )

        delegations: dict[bytes, str] = {}
        for name, value in zip(delegation_names, delegation_values):
            if value and len(value) == 32:
                delegations[name[1:]] = encode_address(value)

        snapshots: list[dict[str, Any]] = []
        for name, value in zip(stake_names, stake_values):
            if not value or len(value) != 32:
                continue
            raw_address = name[1:]
            snapshots.append(
                {
                    "address": encode_address(raw_address),
                    "amount": int.from_bytes(value[0:8], "big"),
                    "unlock_round": int.from_bytes(value[8:16], "big"),
                    "ve_power": int.from_bytes(value[16:24], "big"),
                    "boost_bps": int.from_bytes(value[24:32], "big"),
                    "delegate": delegations.get(raw_address),
                }
            )

        return snapshots

    async def get_delegate_summary(
        self,
        delegate_address: str,
        staking_app_id: int = STAKING_APP_ID,
    ) -> dict[str, Any]:
        """Return delegated power and delegators for a representative address."""
        if not is_valid_address(delegate_address):
            raise ValueError(f"Invalid Algorand address: {delegate_address}")

        snapshots = await self.list_stake_snapshots(staking_app_id)
        delegated = [snapshot for snapshot in snapshots if snapshot.get("delegate") == delegate_address]
        total_power = sum(int(snapshot.get("ve_power", 0)) for snapshot in delegated)
        total_amount = sum(int(snapshot.get("amount", 0)) for snapshot in delegated)

        own_snapshot = next(
            (snapshot for snapshot in snapshots if snapshot["address"] == delegate_address),
            None,
        )

        return {
            "delegate": delegate_address,
            "delegator_count": len(delegated),
            "delegated_power": total_power,
            "delegated_amount": total_amount,
            "delegators": [snapshot["address"] for snapshot in delegated],
            "self_stake": own_snapshot,
        }


# Module-level singleton
_service: Optional[AlgorandService] = None


def get_algorand_service() -> AlgorandService:
    """Get or create the singleton AlgorandService instance."""
    global _service
    if _service is None:
        _service = AlgorandService()
    return _service
