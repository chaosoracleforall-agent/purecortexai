"""
PURECORTEX Isolated Signing Vault.

Local signing implementation used by the isolated signer service and
development-only fallbacks.
The signing process is separated from the broadcast process:

  1. Agent constructs an unsigned transaction (in the main environment)
  2. Unsigned transaction is serialized and passed to the signing vault
  3. Vault decrypts the GPG-encrypted mnemonic in an isolated subprocess
  4. Vault signs the transaction in memory (never writes key to disk)
  5. Vault returns ONLY the signed transaction bytes (key is zeroed)
  6. Agent broadcasts the signed transaction from the main environment

Security properties:
  - Private keys NEVER exist in the main process memory
  - Signing happens in an isolated subprocess with a minimal environment
  - Mnemonic is decrypted only for the duration of signing (<100ms)
  - Signing materials can be fetched per-operation instead of being retained in memory
  - All key material is zeroed after use
  - GPG passphrase is fetched from Secret Manager per-operation (not cached)

Notes:
  - The subprocess uses resource limits and a stripped environment, but it is
    not a full HSM or kernel-enforced network sandbox.
  - For stronger isolation, run the signer in a dedicated container or VM with
    network egress disabled externally.

Architecture:
  ┌─────────────────┐     unsigned_txn      ┌──────────────────────┐
  │   Main Process   │ ──────────────────► │   Signing Vault       │
  │   (Agent/API)    │                      │   (Isolated Subprocess)│
  │                  │ ◄────────────────── │   - Minimal env        │
  │   Has network    │     signed_txn       │   - GPG decrypt        │
  │   Can broadcast  │                      │   - Sign in memory     │
  └─────────────────┘                      │   - Zero key material  │
                                           └──────────────────────┘
"""

import asyncio
import base64
import json
import logging
import os
import resource
import signal
import subprocess
import sys
import tempfile
import time
from typing import Optional

from .gpg_crypto import (
    LEGACY_SHARED_MNEMONIC_SECRET_NAME,
    get_expected_algorand_address_env_name,
    get_gpg_passphrase_secret_name,
    get_gpg_secret_key_secret_name,
    get_mnemonic_secret_candidates,
    load_first_available_secret,
    load_secret_value,
)

logger = logging.getLogger("purecortex.signing_vault")


def _wipe_secret(secret: Optional[str]) -> str:
    if not secret:
        return ""
    return "0" * len(secret)


def _apply_posix_sandbox() -> None:
    """Best-effort resource limits for the signer subprocess."""
    try:
        os.umask(0o077)
    except Exception:
        pass

    limits = [
        ("RLIMIT_CORE", (0, 0)),
        ("RLIMIT_CPU", (5, 5)),
        ("RLIMIT_FSIZE", (1024 * 1024, 1024 * 1024)),
        ("RLIMIT_NOFILE", (32, 32)),
        ("RLIMIT_NPROC", (8, 8)),
    ]

    for name, value in limits:
        limit = getattr(resource, name, None)
        if limit is None:
            continue
        try:
            resource.setrlimit(limit, value)
        except Exception:
            continue

# The signing subprocess script (executed in isolation)
_SIGNING_SCRIPT = '''
import base64
import json
import os
import sys

def main():
    """
    Isolated signing process.

    Reads from stdin: JSON with {encrypted_mnemonic, gpg_passphrase,
                                  gpg_secret_key, unsigned_txn_b64}
    Writes to stdout: JSON with {signed_txn_b64} or {error}

    This process inherits a stripped environment and relies on the parent
    process for timeout + resource enforcement.
    """
    gpg_home = None
    mnemonic = ""
    private_key = ""
    gpg_passphrase = ""
    gpg_secret_key = ""
    encrypted_mnemonic = ""

    try:
        # Read input from stdin (passed by parent process)
        input_data = json.loads(sys.stdin.read())

        encrypted_mnemonic = input_data["encrypted_mnemonic"]
        gpg_passphrase = input_data["gpg_passphrase"]
        gpg_secret_key = input_data["gpg_secret_key"]
        gpg_public_keys = input_data.get("gpg_public_keys", "")
        unsigned_txn_b64 = input_data["unsigned_txn_b64"]
        expected_sender = input_data.get("expected_sender")

        # Step 1: Create temporary GPG home
        import tempfile
        gpg_home = tempfile.mkdtemp(prefix="pcx_vault_")
        os.chmod(gpg_home, 0o700)

        # Step 2: Import keys into isolated keyring
        import subprocess

        # Import public keys
        if gpg_public_keys:
            p = subprocess.run(
                ["gpg", "--batch", "--no-tty", "--homedir", gpg_home, "--import"],
                input=gpg_public_keys.encode(), capture_output=True
            )

        # Import secret key (passphrase via stdin fd, not CLI arg)
        import_input = gpg_passphrase + "\\n"
        p = subprocess.run(
            ["gpg", "--batch", "--no-tty", "--homedir", gpg_home,
             "--pinentry-mode", "loopback", "--passphrase-fd", "0",
             "--import"],
            input=(import_input + gpg_secret_key).encode(), capture_output=True
        )
        if p.returncode != 0:
            raise RuntimeError("GPG key import failed")

        # Step 3: Decrypt the mnemonic (passphrase via stdin fd)
        decrypt_input = gpg_passphrase + "\\n" + encrypted_mnemonic
        p = subprocess.run(
            ["gpg", "--batch", "--no-tty", "--homedir", gpg_home,
             "--pinentry-mode", "loopback", "--passphrase-fd", "0",
             "--decrypt"],
            input=decrypt_input.encode(),
            capture_output=True
        )
        if p.returncode != 0:
            raise RuntimeError("Mnemonic decryption failed")

        mnemonic = p.stdout.decode().strip()

        # Step 4: Derive private key and sign
        from algosdk import mnemonic as mn_module, account, transaction, encoding

        private_key = mn_module.to_private_key(mnemonic)
        sender_address = account.address_from_private_key(private_key)

        if expected_sender and sender_address != expected_sender:
            raise RuntimeError(
                f"Signer address {sender_address} does not match expected sender {expected_sender}"
            )

        # Decode the unsigned transaction
        unsigned_txn_bytes = base64.b64decode(unsigned_txn_b64)
        txn = encoding.msgpack_decode(unsigned_txn_bytes)

        # Verify the transaction sender matches the key
        if hasattr(txn, 'sender') and txn.sender != sender_address:
            raise RuntimeError(
                f"Transaction sender {txn.sender} does not match "
                f"signing key {sender_address}"
            )

        # Sign the transaction
        signed_txn = txn.sign(private_key)
        signed_txn_bytes = encoding.msgpack_encode(signed_txn)
        signed_txn_b64 = base64.b64encode(signed_txn_bytes.encode()
                                           if isinstance(signed_txn_bytes, str)
                                           else signed_txn_bytes).decode()

        # Output the signed transaction
        json.dump({"signed_txn_b64": signed_txn_b64, "sender": sender_address}, sys.stdout)

    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        sys.exit(1)
    finally:
        private_key = "0" * len(private_key) if private_key else ""
        mnemonic = "0" * len(mnemonic) if mnemonic else ""
        gpg_passphrase = "0" * len(gpg_passphrase) if gpg_passphrase else ""
        gpg_secret_key = "0" * len(gpg_secret_key) if gpg_secret_key else ""
        encrypted_mnemonic = "0" * len(encrypted_mnemonic) if encrypted_mnemonic else ""
        try:
            del private_key, mnemonic, gpg_passphrase, gpg_secret_key, encrypted_mnemonic
        except Exception:
            pass

        if gpg_home:
            import shutil
            shutil.rmtree(gpg_home, ignore_errors=True)

if __name__ == "__main__":
    main()
'''

# Multi-transaction signing script (for atomic groups)
_GROUP_SIGNING_SCRIPT = '''
import base64
import json
import os
import sys

def main():
    gpg_home = None
    mnemonic = ""
    private_key = ""
    gpg_passphrase = ""
    gpg_secret_key = ""
    encrypted_mnemonic = ""

    try:
        input_data = json.loads(sys.stdin.read())

        encrypted_mnemonic = input_data["encrypted_mnemonic"]
        gpg_passphrase = input_data["gpg_passphrase"]
        gpg_secret_key = input_data["gpg_secret_key"]
        gpg_public_keys = input_data.get("gpg_public_keys", "")
        unsigned_txns_b64 = input_data["unsigned_txns_b64"]  # list
        expected_sender = input_data.get("expected_sender")

        import tempfile, subprocess, shutil
        gpg_home = tempfile.mkdtemp(prefix="pcx_vault_grp_")
        os.chmod(gpg_home, 0o700)

        if gpg_public_keys:
            subprocess.run(
                ["gpg", "--batch", "--no-tty", "--homedir", gpg_home, "--import"],
                input=gpg_public_keys.encode(), capture_output=True
            )
        import_input = gpg_passphrase + "\\n"
        subprocess.run(
            ["gpg", "--batch", "--no-tty", "--homedir", gpg_home,
             "--pinentry-mode", "loopback", "--passphrase-fd", "0",
             "--import"],
            input=(import_input + gpg_secret_key).encode(), capture_output=True
        )

        decrypt_input = gpg_passphrase + "\\n" + encrypted_mnemonic
        p = subprocess.run(
            ["gpg", "--batch", "--no-tty", "--homedir", gpg_home,
             "--pinentry-mode", "loopback", "--passphrase-fd", "0",
             "--decrypt"],
            input=decrypt_input.encode(), capture_output=True
        )
        mnemonic = p.stdout.decode().strip()

        from algosdk import mnemonic as mn_module, account, transaction, encoding
        private_key = mn_module.to_private_key(mnemonic)
        sender_address = account.address_from_private_key(private_key)

        if expected_sender and sender_address != expected_sender:
            raise RuntimeError(
                f"Signer address {sender_address} does not match expected sender {expected_sender}"
            )

        signed_txns = []
        for utxn_b64 in unsigned_txns_b64:
            unsigned_bytes = base64.b64decode(utxn_b64)
            txn = encoding.msgpack_decode(unsigned_bytes)
            # Verify sender matches signing key
            if hasattr(txn, 'sender') and txn.sender != sender_address:
                raise RuntimeError(
                    f"Group txn sender {txn.sender} does not match "
                    f"signing key {sender_address}"
                )
            signed = txn.sign(private_key)
            signed_bytes = encoding.msgpack_encode(signed)
            signed_txns.append(
                base64.b64encode(signed_bytes.encode()
                                 if isinstance(signed_bytes, str)
                                 else signed_bytes).decode()
            )

        json.dump({"signed_txns_b64": signed_txns}, sys.stdout)

    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        sys.exit(1)
    finally:
        private_key = "0" * len(private_key) if private_key else ""
        mnemonic = "0" * len(mnemonic) if mnemonic else ""
        gpg_passphrase = "0" * len(gpg_passphrase) if gpg_passphrase else ""
        gpg_secret_key = "0" * len(gpg_secret_key) if gpg_secret_key else ""
        encrypted_mnemonic = "0" * len(encrypted_mnemonic) if encrypted_mnemonic else ""
        try:
            del private_key, mnemonic, gpg_passphrase, gpg_secret_key, encrypted_mnemonic
        except Exception:
            pass
        if gpg_home:
            shutil.rmtree(gpg_home, ignore_errors=True)

if __name__ == "__main__":
    main()
'''


class SigningVault:
    """
    Isolated transaction signing vault.

    Signs Algorand transactions in a subprocess that:
    - Decrypts GPG-encrypted mnemonics only when needed
    - Has no persistent access to key material
    - Zeros all secrets after signing
    - Returns only the signed transaction bytes
    """

    # Limit concurrent signing operations to reduce attack surface
    _signing_semaphore = asyncio.Semaphore(3)

    def __init__(self, identity: str = "agent"):
        self.identity = identity
        self._encrypted_mnemonic: Optional[str] = None
        self._gpg_secret_key: Optional[str] = None
        self._gpg_public_keys: Optional[str] = None
        self._mnemonic_secret_candidates: list[str] = []
        self._gpg_secret_key_secret_name: Optional[str] = None
        self._gpg_public_keys_secret_name: str = "PURECORTEX_GPG_PUBLIC_KEYS"
        self._expected_sender: Optional[str] = None
        self._legacy_warning_emitted = False
        # Passphrase is fetched fresh each time, never cached

    async def initialize(
        self,
        encrypted_mnemonic: str = "",
        gpg_secret_key: str = "",
        gpg_public_keys: str = "",
        *,
        mnemonic_secret_candidates: Optional[list[str]] = None,
        gpg_secret_key_secret_name: Optional[str] = None,
        gpg_public_keys_secret_name: str = "PURECORTEX_GPG_PUBLIC_KEYS",
        expected_sender: Optional[str] = None,
    ) -> None:
        """
        Configure how the vault should retrieve signing material.

        Preferred mode stores only secret names and fetches the encrypted
        mnemonic + GPG key material immediately before signing. The positional
        arguments remain for backward compatibility with older callers.
        """
        self._encrypted_mnemonic = encrypted_mnemonic or None
        self._gpg_secret_key = gpg_secret_key or None
        self._gpg_public_keys = gpg_public_keys or None
        self._mnemonic_secret_candidates = list(mnemonic_secret_candidates or [])
        self._gpg_secret_key_secret_name = gpg_secret_key_secret_name
        self._gpg_public_keys_secret_name = gpg_public_keys_secret_name
        self._expected_sender = expected_sender.strip() if expected_sender else None
        logger.info("Signing vault initialized for %s", self.identity)

    async def _get_passphrase(self) -> str:
        """
        Fetch the GPG passphrase from Secret Manager on every signing operation.
        NEVER cached in memory — fetched fresh each time.
        """
        try:
            return load_secret_value(get_gpg_passphrase_secret_name(self.identity))
        except Exception as e:
            raise RuntimeError(f"Cannot fetch GPG passphrase for {self.identity}: {e}")

    def _is_initialized(self) -> bool:
        return bool(
            self._encrypted_mnemonic
            or self._mnemonic_secret_candidates
            or self._gpg_secret_key
            or self._gpg_secret_key_secret_name
        )

    def _resolve_expected_sender(self) -> Optional[str]:
        if self._expected_sender:
            return self._expected_sender

        env_name = get_expected_algorand_address_env_name(self.identity)
        value = os.getenv(env_name, "").strip()
        return value or None

    def _load_runtime_materials(self) -> tuple[str, str, str, Optional[str]]:
        encrypted_mnemonic = self._encrypted_mnemonic or ""
        gpg_secret_key = self._gpg_secret_key or ""
        gpg_public_keys = self._gpg_public_keys or ""
        mnemonic_secret_name: Optional[str] = None

        if self._mnemonic_secret_candidates:
            mnemonic_secret_name, encrypted_mnemonic = load_first_available_secret(
                self._mnemonic_secret_candidates
            )
            if not encrypted_mnemonic:
                raise RuntimeError(
                    f"No encrypted mnemonic available for {self.identity}"
                )

        if self._gpg_secret_key_secret_name:
            gpg_secret_key = load_secret_value(self._gpg_secret_key_secret_name)

        if self._gpg_public_keys_secret_name:
            gpg_public_keys = load_secret_value(self._gpg_public_keys_secret_name)

        if not encrypted_mnemonic or not gpg_secret_key:
            raise RuntimeError(f"Signing material is incomplete for {self.identity}")

        if (
            mnemonic_secret_name == LEGACY_SHARED_MNEMONIC_SECRET_NAME
            and not self._legacy_warning_emitted
        ):
            preferred = self._mnemonic_secret_candidates[0]
            logger.warning(
                "Signing vault for %s is using legacy shared mnemonic secret %s. Configure %s to isolate signer identities.",
                self.identity,
                LEGACY_SHARED_MNEMONIC_SECRET_NAME,
                preferred,
            )
            self._legacy_warning_emitted = True

        return (
            encrypted_mnemonic,
            gpg_secret_key,
            gpg_public_keys,
            self._resolve_expected_sender(),
        )

    async def sign_transaction(self, unsigned_txn_bytes: bytes) -> bytes:
        """
        Sign a single transaction in the isolated vault.

        Args:
            unsigned_txn_bytes: msgpack-encoded unsigned transaction

        Returns:
            msgpack-encoded signed transaction bytes
        """
        if not self._is_initialized():
            raise RuntimeError("Signing vault not initialized")

        async with self._signing_semaphore:
            passphrase = await self._get_passphrase()
            encrypted_mnemonic = ""
            gpg_secret_key = ""
            gpg_public_keys = ""
            input_data = ""

            try:
                (
                    encrypted_mnemonic,
                    gpg_secret_key,
                    gpg_public_keys,
                    expected_sender,
                ) = self._load_runtime_materials()

                payload = {
                    "encrypted_mnemonic": encrypted_mnemonic,
                    "gpg_passphrase": passphrase,
                    "gpg_secret_key": gpg_secret_key,
                    "gpg_public_keys": gpg_public_keys or "",
                    "unsigned_txn_b64": base64.b64encode(unsigned_txn_bytes).decode(),
                }
                if expected_sender:
                    payload["expected_sender"] = expected_sender

                input_data = json.dumps(payload)

                start = time.monotonic()
                result = await self._run_isolated(
                    _SIGNING_SCRIPT, input_data, timeout=30
                )
                elapsed = time.monotonic() - start
            finally:
                passphrase = _wipe_secret(passphrase)
                encrypted_mnemonic = _wipe_secret(encrypted_mnemonic)
                gpg_secret_key = _wipe_secret(gpg_secret_key)
                input_data = _wipe_secret(input_data)
                del passphrase, encrypted_mnemonic, gpg_secret_key, input_data

            if "error" in result:
                raise RuntimeError(result["error"])

            logger.info(
                "Transaction signed in vault (%s) in %.1fms — sender: %s",
                self.identity, elapsed * 1000, result.get("sender", "unknown")
            )

            return base64.b64decode(result["signed_txn_b64"])

    async def sign_transaction_group(
        self, unsigned_txn_bytes_list: list[bytes]
    ) -> list[bytes]:
        """Sign a group of transactions atomically in the vault."""
        if not self._is_initialized():
            raise RuntimeError("Signing vault not initialized")

        async with self._signing_semaphore:
            passphrase = await self._get_passphrase()
            encrypted_mnemonic = ""
            gpg_secret_key = ""
            gpg_public_keys = ""
            input_data = ""

            try:
                (
                    encrypted_mnemonic,
                    gpg_secret_key,
                    gpg_public_keys,
                    expected_sender,
                ) = self._load_runtime_materials()

                payload = {
                    "encrypted_mnemonic": encrypted_mnemonic,
                    "gpg_passphrase": passphrase,
                    "gpg_secret_key": gpg_secret_key,
                    "gpg_public_keys": gpg_public_keys or "",
                    "unsigned_txns_b64": [
                        base64.b64encode(txn).decode() for txn in unsigned_txn_bytes_list
                    ],
                }
                if expected_sender:
                    payload["expected_sender"] = expected_sender

                input_data = json.dumps(payload)

                result = await self._run_isolated(
                    _GROUP_SIGNING_SCRIPT, input_data, timeout=60
                )
            finally:
                passphrase = _wipe_secret(passphrase)
                encrypted_mnemonic = _wipe_secret(encrypted_mnemonic)
                gpg_secret_key = _wipe_secret(gpg_secret_key)
                input_data = _wipe_secret(input_data)
                del passphrase, encrypted_mnemonic, gpg_secret_key, input_data

            if "error" in result:
                raise RuntimeError(result["error"])

            return [base64.b64decode(s) for s in result["signed_txns_b64"]]

    async def _run_isolated(
        self, script: str, input_data: str, timeout: int = 30
    ) -> dict:
        """
        Execute the signing script in an isolated subprocess.

        The subprocess:
        - Inherits NO environment variables except PATH and HOME
        - Has a tight timeout
        - Communicates only via stdin/stdout
        - Runs with restrictive file/process limits on POSIX systems
        """
        proc = None

        # Write script to a temp file (not the key material)
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".py", delete=False, prefix="pcx_vault_"
        ) as f:
            f.write(script)
            script_path = f.name

        try:
            # Minimal environment — no secrets leak via env
            # PYTHONPATH intentionally excluded to prevent module injection
            clean_env = {
                "PATH": os.environ.get("PATH", "/usr/bin:/usr/local/bin"),
                "HOME": tempfile.gettempdir(),
            }

            proc = await asyncio.create_subprocess_exec(
                sys.executable, script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=clean_env,
                cwd=tempfile.gettempdir(),
                close_fds=True,
                start_new_session=True,
                preexec_fn=_apply_posix_sandbox if os.name == "posix" else None,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=input_data.encode()),
                timeout=timeout,
            )

            if proc.returncode != 0:
                try:
                    return json.loads(stdout.decode())
                except Exception:
                    # Sanitize: never expose raw stderr (may contain key fragments)
                    logger.error("Vault process failed (exit %d) for %s", proc.returncode, self.identity)
                    return {"error": f"Vault process failed (exit {proc.returncode})"}

            return json.loads(stdout.decode())

        except asyncio.TimeoutError:
            if proc is not None:
                try:
                    if os.name == "posix":
                        os.killpg(proc.pid, signal.SIGKILL)
                    else:
                        proc.kill()
                except Exception:
                    proc.kill()
                await proc.wait()
            return {"error": "Vault signing timed out"}
        finally:
            os.unlink(script_path)
            # Clean up any orphaned vault temp dirs (PEN-007)
            import glob as _glob
            for d in _glob.glob(os.path.join(tempfile.gettempdir(), "pcx_vault_*")):
                if os.path.isdir(d):
                    try:
                        import shutil
                        shutil.rmtree(d, ignore_errors=True)
                    except Exception:
                        pass


# ------------------------------------------------------------------ #
#  Factory function
# ------------------------------------------------------------------ #

async def create_signing_vault(identity: str = "agent") -> SigningVault:
    """
    Create and initialize a signing vault from GCP Secret Manager.
    """
    vault = SigningVault(identity=identity)
    expected_sender = os.getenv(get_expected_algorand_address_env_name(identity), "").strip()
    await vault.initialize(
        mnemonic_secret_candidates=get_mnemonic_secret_candidates(identity),
        gpg_secret_key_secret_name=get_gpg_secret_key_secret_name(identity),
        gpg_public_keys_secret_name="PURECORTEX_GPG_PUBLIC_KEYS",
        expected_sender=expected_sender or None,
    )

    return vault
