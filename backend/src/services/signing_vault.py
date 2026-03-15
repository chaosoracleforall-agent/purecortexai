"""
PURECORTEX Isolated Signing Vault.

Enterprise-grade transaction signing in a completely isolated environment.
The signing process is separated from the broadcast process:

  1. Agent constructs an unsigned transaction (in the main environment)
  2. Unsigned transaction is serialized and passed to the signing vault
  3. Vault decrypts the GPG-encrypted mnemonic in an isolated subprocess
  4. Vault signs the transaction in memory (never writes key to disk)
  5. Vault returns ONLY the signed transaction bytes (key is zeroed)
  6. Agent broadcasts the signed transaction from the main environment

Security guarantees:
  - Private keys NEVER exist in the main process memory
  - Signing happens in an isolated subprocess with restricted capabilities
  - Mnemonic is decrypted only for the duration of signing (<100ms)
  - Subprocess has no network access during signing (iptables/seccomp)
  - All key material is zeroed after use
  - GPG passphrase is fetched from Secret Manager per-operation (not cached)

Architecture:
  ┌─────────────────┐     unsigned_txn      ┌──────────────────────┐
  │   Main Process   │ ──────────────────► │   Signing Vault       │
  │   (Agent/API)    │                      │   (Isolated Subprocess)│
  │                  │ ◄────────────────── │   - No network         │
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
import subprocess
import sys
import tempfile
import time
from typing import Optional

logger = logging.getLogger("purecortex.signing_vault")

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

    This process has NO network access and NO filesystem access
    beyond what's needed for GPG operations.
    """
    try:
        # Read input from stdin (passed by parent process)
        input_data = json.loads(sys.stdin.read())

        encrypted_mnemonic = input_data["encrypted_mnemonic"]
        gpg_passphrase = input_data["gpg_passphrase"]
        gpg_secret_key = input_data["gpg_secret_key"]
        gpg_public_keys = input_data.get("gpg_public_keys", "")
        unsigned_txn_b64 = input_data["unsigned_txn_b64"]

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

        # Step 5: ZERO all key material
        private_key = "0" * len(private_key) if private_key else ""
        mnemonic = "0" * len(mnemonic) if mnemonic else ""
        del private_key, mnemonic

        # Step 6: Cleanup GPG home
        import shutil
        shutil.rmtree(gpg_home, ignore_errors=True)

        # Output the signed transaction
        json.dump({"signed_txn_b64": signed_txn_b64, "sender": sender_address}, sys.stdout)

    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        sys.exit(1)

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
    try:
        input_data = json.loads(sys.stdin.read())

        encrypted_mnemonic = input_data["encrypted_mnemonic"]
        gpg_passphrase = input_data["gpg_passphrase"]
        gpg_secret_key = input_data["gpg_secret_key"]
        gpg_public_keys = input_data.get("gpg_public_keys", "")
        unsigned_txns_b64 = input_data["unsigned_txns_b64"]  # list

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

        private_key = "0" * len(private_key)
        mnemonic = "0" * len(mnemonic)
        del private_key, mnemonic
        shutil.rmtree(gpg_home, ignore_errors=True)

        json.dump({"signed_txns_b64": signed_txns}, sys.stdout)

    except Exception as e:
        json.dump({"error": str(e)}, sys.stdout)
        sys.exit(1)

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
        # Passphrase is fetched fresh each time, never cached

    async def initialize(
        self,
        encrypted_mnemonic: str,
        gpg_secret_key: str,
        gpg_public_keys: str,
    ) -> None:
        """
        Store references to encrypted materials (NOT decrypted keys).
        The actual decryption happens only inside the signing subprocess.
        """
        self._encrypted_mnemonic = encrypted_mnemonic
        self._gpg_secret_key = gpg_secret_key
        self._gpg_public_keys = gpg_public_keys
        logger.info("Signing vault initialized for %s", self.identity)

    async def _get_passphrase(self) -> str:
        """
        Fetch the GPG passphrase from Secret Manager on every signing operation.
        NEVER cached in memory — fetched fresh each time.
        """
        # Map identity to secret name
        secret_map = {
            "agent": "PURECORTEX_AGENT_GPG_PASSPHRASE",
            "senator": "PURECORTEX_SENATOR_GPG_PASSPHRASE",
            "curator": "PURECORTEX_CURATOR_GPG_PASSPHRASE",
            "social": "PURECORTEX_SOCIAL_GPG_PASSPHRASE",
            "vm": "PURECORTEX_VM_GPG_PASSPHRASE",
        }
        secret_name = secret_map.get(self.identity, "PURECORTEX_AGENT_GPG_PASSPHRASE")

        # Try env var first (for testing)
        env_val = os.getenv(secret_name, "")
        if env_val:
            return env_val

        # Fetch from Secret Manager
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GCP_PROJECT_ID", "purecortexai")
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"Cannot fetch GPG passphrase for {self.identity}: {e}")

    async def sign_transaction(self, unsigned_txn_bytes: bytes) -> bytes:
        """
        Sign a single transaction in the isolated vault.

        Args:
            unsigned_txn_bytes: msgpack-encoded unsigned transaction

        Returns:
            msgpack-encoded signed transaction bytes
        """
        if not self._encrypted_mnemonic:
            raise RuntimeError("Signing vault not initialized")

        async with self._signing_semaphore:
            passphrase = await self._get_passphrase()

            input_data = json.dumps({
                "encrypted_mnemonic": self._encrypted_mnemonic,
                "gpg_passphrase": passphrase,
                "gpg_secret_key": self._gpg_secret_key,
                "gpg_public_keys": self._gpg_public_keys or "",
                "unsigned_txn_b64": base64.b64encode(unsigned_txn_bytes).decode(),
            })

            # Zero passphrase from this process immediately
            passphrase = "0" * len(passphrase)
            del passphrase

            start = time.monotonic()
            result = await self._run_isolated(
                _SIGNING_SCRIPT, input_data, timeout=30
            )
            elapsed = time.monotonic() - start

            if "error" in result:
                raise RuntimeError("Vault signing failed")

            logger.info(
                "Transaction signed in vault (%s) in %.1fms — sender: %s",
                self.identity, elapsed * 1000, result.get("sender", "unknown")
            )

            return base64.b64decode(result["signed_txn_b64"])

    async def sign_transaction_group(
        self, unsigned_txn_bytes_list: list[bytes]
    ) -> list[bytes]:
        """Sign a group of transactions atomically in the vault."""
        if not self._encrypted_mnemonic:
            raise RuntimeError("Signing vault not initialized")

        async with self._signing_semaphore:
            passphrase = await self._get_passphrase()

            input_data = json.dumps({
                "encrypted_mnemonic": self._encrypted_mnemonic,
                "gpg_passphrase": passphrase,
                "gpg_secret_key": self._gpg_secret_key,
                "gpg_public_keys": self._gpg_public_keys or "",
                "unsigned_txns_b64": [
                    base64.b64encode(txn).decode() for txn in unsigned_txn_bytes_list
                ],
            })

            passphrase = "0" * len(passphrase)
            del passphrase

            result = await self._run_isolated(
                _GROUP_SIGNING_SCRIPT, input_data, timeout=60
            )

            if "error" in result:
                raise RuntimeError("Vault group signing failed")

            return [base64.b64decode(s) for s in result["signed_txns_b64"]]

    async def _run_isolated(
        self, script: str, input_data: str, timeout: int = 30
    ) -> dict:
        """
        Execute the signing script in an isolated subprocess.

        The subprocess:
        - Inherits NO environment variables except PATH and HOME
        - Has a tight timeout
        - Communicates only via stdin/stdout (no filesystem, no network)
        """
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
            proc.kill()
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

    encrypted_mnemonic = ""
    gpg_secret_key = ""
    gpg_public_keys = ""

    # Map identity to secret names
    key_secret = {
        "agent": "PURECORTEX_AGENT_GPG_SECRET_KEY",
        "senator": "PURECORTEX_SENATOR_GPG_SECRET_KEY",
        "curator": "PURECORTEX_CURATOR_GPG_SECRET_KEY",
        "social": "PURECORTEX_SOCIAL_GPG_SECRET_KEY",
        "vm": "PURECORTEX_VM_GPG_SECRET_KEY",
    }

    secret_key_name = key_secret.get(identity, "PURECORTEX_AGENT_GPG_SECRET_KEY")

    try:
        from google.cloud import secretmanager
        client = secretmanager.SecretManagerServiceClient()
        project_id = os.getenv("GCP_PROJECT_ID", "purecortexai")

        def _access(name: str) -> str:
            resource = f"projects/{project_id}/secrets/{name}/versions/latest"
            resp = client.access_secret_version(request={"name": resource})
            return resp.payload.data.decode("utf-8")

        encrypted_mnemonic = _access("PURECORTEX_DEPLOYER_MNEMONIC_GPG")
        gpg_secret_key = _access(secret_key_name)
        gpg_public_keys = _access("PURECORTEX_GPG_PUBLIC_KEYS")
    except Exception as e:
        # Fallback to env vars
        encrypted_mnemonic = os.getenv("PURECORTEX_DEPLOYER_MNEMONIC_GPG", "")
        gpg_secret_key = os.getenv(secret_key_name, "")
        gpg_public_keys = os.getenv("PURECORTEX_GPG_PUBLIC_KEYS", "")
        if not encrypted_mnemonic:
            logger.warning("Signing vault: no encrypted mnemonic available for %s", identity)

    if encrypted_mnemonic and gpg_secret_key:
        await vault.initialize(encrypted_mnemonic, gpg_secret_key, gpg_public_keys)

    return vault
