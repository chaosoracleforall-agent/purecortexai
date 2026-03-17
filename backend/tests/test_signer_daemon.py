from __future__ import annotations

import asyncio
import sys
import tempfile
import uuid
from pathlib import Path
import socket

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.services.signer_client import RemoteSigningClient, create_signing_backend
from src.services.signer_daemon import SignerDaemon


class FakeVault:
    async def sign_transaction(self, unsigned_txn: bytes) -> bytes:
        return b"signed:" + unsigned_txn

    async def sign_transaction_group(self, unsigned_group: list[bytes]) -> list[bytes]:
        return [b"signed:" + item for item in unsigned_group]


def _require_unix_socket_support() -> None:
    """Skip tests in runtimes that disallow binding unix sockets (sandbox CI)."""
    socket_dir = Path(tempfile.mkdtemp(prefix="pcxsock_probe_", dir="/tmp"))
    socket_path = socket_dir / f"{uuid.uuid4().hex[:12]}.sock"
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    try:
        try:
            sock.bind(str(socket_path))
        except PermissionError:
            pytest.skip("Unix socket bind is not permitted in this runtime")
    finally:
        sock.close()
        if socket_path.exists():
            socket_path.unlink()
        socket_dir.rmdir()


def test_remote_signer_round_trip(monkeypatch, tmp_path):
    _require_unix_socket_support()

    async def _run() -> None:
        socket_dir = Path(tempfile.mkdtemp(prefix="pcxsock_", dir="/tmp"))
        socket_path = socket_dir / f"{uuid.uuid4().hex[:12]}.sock"

        async def fake_create_signing_vault(identity: str = "agent"):
            assert identity == "social"
            vault = FakeVault()
            vault.mode = "local"
            return vault

        monkeypatch.setattr(
            "src.services.signer_daemon.create_signing_vault",
            fake_create_signing_vault,
        )
        monkeypatch.setenv("PURECORTEX_SIGNER_SOCKET_PATH", str(socket_path))
        monkeypatch.setenv("PURECORTEX_SIGNER_SHARED_TOKEN", "shared-token")
        monkeypatch.delenv("PURECORTEX_FORCE_LOCAL_SIGNING_VAULT", raising=False)

        daemon = SignerDaemon(
            socket_path=str(socket_path),
            socket_mode=0o666,
            shared_token="shared-token",
            allowed_identities={"social"},
            request_timeout_seconds=5,
            max_request_bytes=8192,
            max_group_size=4,
        )
        await daemon.start()
        try:
            backend = await create_signing_backend("social")
            assert getattr(backend, "mode") == "remote"
            assert await backend.sign_transaction(b"txn") == b"signed:txn"
            assert await backend.sign_transaction_group([b"a", b"b"]) == [
                b"signed:a",
                b"signed:b",
            ]
            await backend.cleanup()
        finally:
            await daemon.stop()
            socket_dir.rmdir()

    asyncio.run(_run())


def test_remote_signer_rejects_invalid_token(monkeypatch, tmp_path):
    _require_unix_socket_support()

    async def _run() -> None:
        socket_dir = Path(tempfile.mkdtemp(prefix="pcxsock_", dir="/tmp"))
        socket_path = socket_dir / f"{uuid.uuid4().hex[:12]}.sock"

        async def fake_create_signing_vault(identity: str = "agent"):
            assert identity == "social"
            return FakeVault()

        monkeypatch.setattr(
            "src.services.signer_daemon.create_signing_vault",
            fake_create_signing_vault,
        )

        daemon = SignerDaemon(
            socket_path=str(socket_path),
            socket_mode=0o666,
            shared_token="expected-token",
            allowed_identities={"social"},
            request_timeout_seconds=5,
            max_request_bytes=8192,
            max_group_size=4,
        )
        await daemon.start()
        try:
            client = RemoteSigningClient(
                "social",
                socket_path=str(socket_path),
                token="wrong-token",
                timeout_seconds=5,
            )
            with pytest.raises(RuntimeError, match="Unauthorized signer request"):
                await client.ping()
        finally:
            await daemon.stop()
            socket_dir.rmdir()

    asyncio.run(_run())


def test_signer_daemon_requires_shared_token():
    async def _run() -> None:
        socket_dir = Path(tempfile.mkdtemp(prefix="pcxsock_", dir="/tmp"))
        socket_path = socket_dir / f"{uuid.uuid4().hex[:12]}.sock"

        daemon = SignerDaemon(
            socket_path=str(socket_path),
            socket_mode=0o666,
            shared_token="",
            allowed_identities={"social"},
            request_timeout_seconds=5,
            max_request_bytes=8192,
            max_group_size=4,
        )
        try:
            with pytest.raises(RuntimeError, match="Signer shared token not configured"):
                await daemon.start()
        finally:
            if socket_path.exists():
                socket_path.unlink()
            socket_dir.rmdir()

    asyncio.run(_run())
