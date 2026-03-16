"""
Remote signer client for PURECORTEX.

The backend can delegate Algorand signing to a dedicated signer service over a
local Unix domain socket. This keeps mnemonic and signer GPG material out of
the main application container.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os

logger = logging.getLogger("purecortex.signer_client")


SIGNER_SOCKET_ENV = "PURECORTEX_SIGNER_SOCKET_PATH"
SIGNER_TIMEOUT_ENV = "PURECORTEX_SIGNER_REQUEST_TIMEOUT_SECONDS"
SIGNER_SHARED_TOKEN_ENV = "PURECORTEX_SIGNER_SHARED_TOKEN"
FORCE_LOCAL_SIGNER_ENV = "PURECORTEX_FORCE_LOCAL_SIGNING_VAULT"


class RemoteSigningClient:
    """Unix-socket client for the isolated signer service."""

    def __init__(
        self,
        identity: str,
        *,
        socket_path: str,
        token: str | None = None,
        timeout_seconds: int = 30,
    ) -> None:
        self.identity = identity
        self.socket_path = socket_path
        self.token = token or ""
        self.timeout_seconds = timeout_seconds
        self.mode = "remote"

    async def ping(self) -> None:
        await self._request({"action": "ping"})

    async def sign_transaction(self, unsigned_txn_bytes: bytes) -> bytes:
        response = await self._request(
            {
                "action": "sign",
                "unsigned_txn_b64": base64.b64encode(unsigned_txn_bytes).decode(),
            }
        )
        return base64.b64decode(response["signed_txn_b64"])

    async def sign_transaction_group(self, unsigned_txns: list[bytes]) -> list[bytes]:
        response = await self._request(
            {
                "action": "sign_group",
                "unsigned_txns_b64": [
                    base64.b64encode(txn).decode() for txn in unsigned_txns
                ],
            }
        )
        return [base64.b64decode(item) for item in response["signed_txns_b64"]]

    async def cleanup(self) -> None:
        """No-op for interface parity with the local vault."""

    async def _request(self, payload: dict) -> dict:
        request_payload = {
            "identity": self.identity,
            "token": self.token,
            **payload,
        }

        reader = None
        writer = None
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_unix_connection(self.socket_path),
                timeout=self.timeout_seconds,
            )
            writer.write(json.dumps(request_payload).encode("utf-8") + b"\n")
            await asyncio.wait_for(writer.drain(), timeout=self.timeout_seconds)

            raw_response = await asyncio.wait_for(
                reader.readline(), timeout=self.timeout_seconds
            )
            if not raw_response:
                raise RuntimeError("Signer closed the connection without a response")

            response = json.loads(raw_response.decode("utf-8"))
            if "error" in response:
                raise RuntimeError(response["error"])

            return response
        finally:
            if writer is not None:
                writer.close()
                try:
                    await writer.wait_closed()
                except Exception:
                    pass


async def create_signing_backend(identity: str = "agent"):
    """
    Create the most secure available signing backend.

    If PURECORTEX_SIGNER_SOCKET_PATH is configured and local fallback is not
    forced, the backend uses the isolated signer service over a Unix socket.
    Otherwise it falls back to the in-process local signing vault for
    development-only workflows.
    """
    force_local = os.getenv(FORCE_LOCAL_SIGNER_ENV, "0") == "1"
    socket_path = os.getenv(SIGNER_SOCKET_ENV, "").strip()

    if socket_path and not force_local:
        timeout_seconds = int(os.getenv(SIGNER_TIMEOUT_ENV, "30"))
        client = RemoteSigningClient(
            identity=identity,
            socket_path=socket_path,
            token=os.getenv(SIGNER_SHARED_TOKEN_ENV, ""),
            timeout_seconds=timeout_seconds,
        )
        await client.ping()
        logger.info("Using remote signer service for %s via %s", identity, socket_path)
        return client

    from .signing_vault import create_signing_vault

    logger.warning(
        "Using local signing vault for %s. Configure %s to route signing through the isolated signer service.",
        identity,
        SIGNER_SOCKET_ENV,
    )
    vault = await create_signing_vault(identity=identity)
    setattr(vault, "mode", "local")
    return vault
