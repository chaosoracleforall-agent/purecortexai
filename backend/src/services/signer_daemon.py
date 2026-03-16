"""
Dedicated Unix-socket signer daemon for PURECORTEX.

This service is intended to run in its own container with:
  - no network access,
  - a minimal Python image,
  - signer-only secret files or env vars,
  - a shared Unix socket mounted only into the backend container.
"""

from __future__ import annotations

import asyncio
import base64
import json
import logging
import os
import signal
from typing import Optional

from .signing_vault import create_signing_vault

logger = logging.getLogger("purecortex.signer_daemon")


DEFAULT_ALLOWED_IDENTITIES = ("agent", "senator", "curator", "social", "vm")
DEFAULT_SOCKET_PATH = "/run/purecortex/signer.sock"


class SignerDaemon:
    def __init__(
        self,
        *,
        socket_path: str,
        socket_mode: int,
        shared_token: str,
        allowed_identities: set[str],
        request_timeout_seconds: int,
        max_request_bytes: int,
        max_group_size: int,
    ) -> None:
        self.socket_path = socket_path
        self.socket_mode = socket_mode
        self.shared_token = shared_token
        self.allowed_identities = allowed_identities
        self.request_timeout_seconds = request_timeout_seconds
        self.max_request_bytes = max_request_bytes
        self.max_group_size = max_group_size
        self._vaults: dict[str, object] = {}
        self._server: Optional[asyncio.AbstractServer] = None

    @classmethod
    def from_env(cls) -> "SignerDaemon":
        allowed_raw = os.getenv(
            "PURECORTEX_SIGNER_ALLOWED_IDENTITIES",
            ",".join(DEFAULT_ALLOWED_IDENTITIES),
        )
        allowed_identities = {
            identity.strip().lower()
            for identity in allowed_raw.split(",")
            if identity.strip()
        }
        return cls(
            socket_path=os.getenv("PURECORTEX_SIGNER_SOCKET_PATH", DEFAULT_SOCKET_PATH),
            socket_mode=int(os.getenv("PURECORTEX_SIGNER_SOCKET_MODE", "660"), 8),
            shared_token=os.getenv("PURECORTEX_SIGNER_SHARED_TOKEN", ""),
            allowed_identities=allowed_identities,
            request_timeout_seconds=int(
                os.getenv("PURECORTEX_SIGNER_REQUEST_TIMEOUT_SECONDS", "30")
            ),
            max_request_bytes=int(
                os.getenv("PURECORTEX_SIGNER_MAX_REQUEST_BYTES", str(1024 * 1024))
            ),
            max_group_size=int(os.getenv("PURECORTEX_SIGNER_MAX_GROUP_SIZE", "16")),
        )

    async def start(self) -> None:
        socket_dir = os.path.dirname(self.socket_path)
        if socket_dir:
            os.makedirs(socket_dir, exist_ok=True)

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self._server = await asyncio.start_unix_server(
            self.handle_client,
            path=self.socket_path,
            limit=self.max_request_bytes,
        )
        os.chmod(self.socket_path, self.socket_mode)
        logger.info(
            "Signer daemon listening on %s for identities=%s",
            self.socket_path,
            sorted(self.allowed_identities),
        )

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
            self._server = None

        if os.path.exists(self.socket_path):
            os.unlink(self.socket_path)

        self._vaults.clear()

    async def serve_forever(self) -> None:
        if self._server is None:
            raise RuntimeError("Signer daemon not started")
        async with self._server:
            await self._server.serve_forever()

    async def get_vault(self, identity: str):
        vault = self._vaults.get(identity)
        if vault is None:
            vault = await create_signing_vault(identity=identity)
            self._vaults[identity] = vault
        return vault

    async def handle_client(
        self,
        reader: asyncio.StreamReader,
        writer: asyncio.StreamWriter,
    ) -> None:
        response: dict[str, object]
        try:
            raw_request = await asyncio.wait_for(
                reader.readline(), timeout=self.request_timeout_seconds
            )
            if not raw_request:
                raise ValueError("Empty signer request")
            if len(raw_request) > self.max_request_bytes:
                raise ValueError("Signer request too large")

            request = json.loads(raw_request.decode("utf-8"))
            action = str(request.get("action", "")).strip()

            if self.shared_token and request.get("token") != self.shared_token:
                raise PermissionError("Unauthorized signer request")

            if action == "ping":
                response = {"ok": True}
            else:
                identity = str(request.get("identity", "")).strip().lower()
                if identity not in self.allowed_identities:
                    raise PermissionError("Identity not allowed by signer policy")

                vault = await self.get_vault(identity)
                if action == "sign":
                    unsigned_txn = base64.b64decode(request["unsigned_txn_b64"])
                    signed_txn = await vault.sign_transaction(unsigned_txn)
                    response = {
                        "signed_txn_b64": base64.b64encode(signed_txn).decode("utf-8")
                    }
                elif action == "sign_group":
                    encoded_group = request["unsigned_txns_b64"]
                    if len(encoded_group) > self.max_group_size:
                        raise ValueError("Signer request exceeds maximum group size")
                    unsigned_group = [
                        base64.b64decode(item) for item in encoded_group
                    ]
                    signed_group = await vault.sign_transaction_group(unsigned_group)
                    response = {
                        "signed_txns_b64": [
                            base64.b64encode(item).decode("utf-8")
                            for item in signed_group
                        ]
                    }
                else:
                    raise ValueError(f"Unsupported signer action: {action or 'unknown'}")
        except Exception as exc:
            logger.error("Signer request failed: %s", exc)
            response = {"error": str(exc)}
        finally:
            writer.write(json.dumps(response).encode("utf-8") + b"\n")
            try:
                await asyncio.wait_for(writer.drain(), timeout=5)
            except Exception:
                pass
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass


async def _main() -> None:
    daemon = SignerDaemon.from_env()
    await daemon.start()

    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    def _request_stop() -> None:
        stop_event.set()

    for sig in (signal.SIGINT, signal.SIGTERM):
        try:
            loop.add_signal_handler(sig, _request_stop)
        except NotImplementedError:
            pass

    server_task = asyncio.create_task(daemon.serve_forever())
    try:
        await stop_event.wait()
    finally:
        server_task.cancel()
        await asyncio.gather(server_task, return_exceptions=True)
        await daemon.stop()


def main() -> None:
    logging.basicConfig(
        level=os.getenv("PURECORTEX_SIGNER_LOG_LEVEL", "INFO"),
        format="%(name)s | %(message)s",
    )
    asyncio.run(_main())


if __name__ == "__main__":
    main()
