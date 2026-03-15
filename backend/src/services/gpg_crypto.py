"""
GPG encryption/decryption service for PURECORTEX agents.

Every agent and the VM have their own GPG keypair. Secrets (mnemonics,
API keys, inter-agent messages) are encrypted to the recipient's public
key and can only be decrypted by the holder of the corresponding private
key + passphrase.

Key hierarchy:
  - deployer@purecortex.ai  — local deploy machine (no passphrase)
  - vm@purecortex.ai        — VM runtime (passphrase in Secret Manager)
  - agent@purecortex.ai     — shared agent key (passphrase in Secret Manager)
  - senator@purecortex.ai   — Senator agent (passphrase in Secret Manager)
  - curator@purecortex.ai   — Curator agent (passphrase in Secret Manager)
  - social@purecortex.ai    — Social agent (passphrase in Secret Manager)

Secrets in GCP Secret Manager:
  PURECORTEX_AGENT_GPG_SECRET_KEY    — agent private key (armored)
  PURECORTEX_AGENT_GPG_PASSPHRASE   — agent private key passphrase
  PURECORTEX_GPG_PUBLIC_KEYS        — all public keys (armored)
  PURECORTEX_DEPLOYER_MNEMONIC_GPG  — encrypted mnemonic (armored)
"""

import asyncio
import logging
import os
import subprocess
import tempfile
import shutil
from typing import Optional

logger = logging.getLogger("purecortex.gpg")


class GPGCrypto:
    """Manages a per-instance GPG keyring for encrypt/decrypt operations."""

    def __init__(self, identity: str = "agent"):
        """
        Args:
            identity: The agent identity (e.g., "agent", "senator", "curator").
                      Used to look up the correct key and passphrase.
        """
        self.identity = identity
        self._gnupg_home: Optional[str] = None
        self._initialized = False

    async def initialize(
        self,
        secret_key_pem: str,
        passphrase: str,
        public_keys_pem: str,
    ) -> None:
        """
        Set up an isolated GPG keyring with the agent's private key
        and all public keys.

        Args:
            secret_key_pem: Armored GPG secret key for this agent.
            passphrase: Passphrase for the secret key.
            public_keys_pem: Armored GPG public keys for all parties.
        """
        # Create isolated GNUPG home
        self._gnupg_home = tempfile.mkdtemp(prefix=f"pcx_gpg_{self.identity}_")
        os.chmod(self._gnupg_home, 0o700)

        # Import public keys
        await self._run_gpg(
            ["--import"],
            input_data=public_keys_pem,
        )

        # Import secret key (passphrase via fd, not CLI arg — PEN-001)
        await self._run_gpg(
            ["--batch", "--pinentry-mode", "loopback",
             "--passphrase-fd", "0", "--import"],
            input_data=passphrase + "\n" + secret_key_pem,
        )

        # Trust all imported keys
        keys_output = await self._run_gpg(
            ["--list-keys", "--with-colons", "--keyid-format", "long"],
        )
        for line in keys_output.split("\n"):
            if line.startswith("fpr:"):
                fpr = line.split(":")[9]
                await self._run_gpg(
                    ["--batch", "--command-fd", "0", "--edit-key", fpr, "trust"],
                    input_data="5\ny\n",
                )

        # Passphrase NOT cached — fetched per-operation from Secret Manager
        self._initialized = True
        logger.info("GPG keyring initialized for %s", self.identity)

    async def encrypt(self, plaintext: str, recipients: list[str]) -> str:
        """
        Encrypt a message to one or more recipients.

        Args:
            plaintext: The secret data to encrypt.
            recipients: List of recipient emails (e.g., ["senator@purecortex.ai"]).

        Returns:
            Armored GPG encrypted message.
        """
        self._check_initialized()
        args = ["--encrypt", "--armor", "--trust-model", "always"]
        for r in recipients:
            args.extend(["--recipient", r])
        return await self._run_gpg(args, input_data=plaintext)

    async def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt a GPG-encrypted message using this agent's private key.

        Args:
            ciphertext: Armored GPG encrypted message.

        Returns:
            Decrypted plaintext.
        """
        self._check_initialized()
        passphrase = await self._get_passphrase()
        result = await self._run_gpg(
            ["--batch", "--pinentry-mode", "loopback",
             "--passphrase-fd", "0",
             "--decrypt"],
            input_data=passphrase + "\n" + ciphertext,
        )
        passphrase = "0" * len(passphrase)
        del passphrase
        return result

    async def sign(self, message: str) -> str:
        """Sign a message with this agent's key (clearsign)."""
        self._check_initialized()
        passphrase = await self._get_passphrase()
        result = await self._run_gpg(
            ["--batch", "--pinentry-mode", "loopback",
             "--passphrase-fd", "0",
             "--clearsign"],
            input_data=passphrase + "\n" + message,
        )
        passphrase = "0" * len(passphrase)
        del passphrase
        return result

    async def verify(self, signed_message: str) -> tuple[bool, str]:
        """
        Verify a clearsigned message.

        Returns:
            (valid, signer_email) tuple.
        """
        self._check_initialized()
        try:
            output = await self._run_gpg(
                ["--verify", "--status-fd", "1"],
                input_data=signed_message,
            )
            # Parse GOODSIG from status output
            for line in output.split("\n"):
                if "GOODSIG" in line:
                    parts = line.split()
                    signer = parts[-1] if parts else "unknown"
                    return True, signer
            return False, ""
        except RuntimeError:
            return False, ""

    async def encrypt_for_all_agents(self, plaintext: str) -> str:
        """Encrypt to all PURECORTEX agents + deployer + VM."""
        recipients = [
            "deployer@purecortex.ai",
            "vm@purecortex.ai",
            "agent@purecortex.ai",
            "senator@purecortex.ai",
            "curator@purecortex.ai",
            "social@purecortex.ai",
        ]
        return await self.encrypt(plaintext, recipients)

    async def cleanup(self) -> None:
        """Remove the temporary GPG keyring."""
        if self._gnupg_home and os.path.exists(self._gnupg_home):
            shutil.rmtree(self._gnupg_home, ignore_errors=True)
            self._gnupg_home = None
            self._initialized = False
            logger.info("GPG keyring cleaned up for %s", self.identity)

    async def _get_passphrase(self) -> str:
        """Fetch GPG passphrase per-operation from Secret Manager. Never cached."""
        secret_map = {
            "agent": "PURECORTEX_AGENT_GPG_PASSPHRASE",
            "senator": "PURECORTEX_SENATOR_GPG_PASSPHRASE",
            "curator": "PURECORTEX_CURATOR_GPG_PASSPHRASE",
            "social": "PURECORTEX_SOCIAL_GPG_PASSPHRASE",
            "vm": "PURECORTEX_VM_GPG_PASSPHRASE",
        }
        secret_name = secret_map.get(self.identity, "PURECORTEX_AGENT_GPG_PASSPHRASE")
        env_val = os.getenv(secret_name, "")
        if env_val:
            return env_val
        try:
            from google.cloud import secretmanager
            client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GCP_PROJECT_ID", "purecortexai")
            name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
            response = client.access_secret_version(request={"name": name})
            return response.payload.data.decode("utf-8")
        except Exception as e:
            raise RuntimeError(f"Cannot fetch GPG passphrase for {self.identity}: {e}")

    def _check_initialized(self) -> None:
        if not self._initialized:
            raise RuntimeError(
                f"GPG keyring not initialized for {self.identity}. "
                "Call initialize() first."
            )

    async def _run_gpg(
        self,
        args: list[str],
        input_data: Optional[str] = None,
    ) -> str:
        """Run a gpg command in the isolated keyring."""
        cmd = [
            "gpg", "--batch", "--no-tty",
            "--homedir", self._gnupg_home,
        ] + args

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=subprocess.PIPE if input_data else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        stdout, stderr = await proc.communicate(
            input=input_data.encode() if input_data else None
        )
        if proc.returncode != 0:
            err_msg = stderr.decode().strip()
            # Some gpg warnings are not errors
            if "WARNING" not in err_msg and "gpg: key" not in err_msg:
                raise RuntimeError(f"GPG error: {err_msg}")
        return stdout.decode()


# ------------------------------------------------------------------ #
#  Helper: load from GCP Secret Manager and initialize
# ------------------------------------------------------------------ #

async def create_agent_gpg(identity: str = "agent") -> GPGCrypto:
    """
    Factory function: creates and initializes a GPGCrypto instance
    using secrets from GCP Secret Manager or environment variables.

    Env var fallbacks:
        PURECORTEX_AGENT_GPG_SECRET_KEY
        PURECORTEX_AGENT_GPG_PASSPHRASE
        PURECORTEX_GPG_PUBLIC_KEYS
    """
    gpg = GPGCrypto(identity=identity)

    # Map identity to identity-specific secret names (PEN-013)
    key_secret_map = {
        "agent": "PURECORTEX_AGENT_GPG_SECRET_KEY",
        "senator": "PURECORTEX_SENATOR_GPG_SECRET_KEY",
        "curator": "PURECORTEX_CURATOR_GPG_SECRET_KEY",
        "social": "PURECORTEX_SOCIAL_GPG_SECRET_KEY",
        "vm": "PURECORTEX_VM_GPG_SECRET_KEY",
    }
    passphrase_map = {
        "agent": "PURECORTEX_AGENT_GPG_PASSPHRASE",
        "senator": "PURECORTEX_SENATOR_GPG_PASSPHRASE",
        "curator": "PURECORTEX_CURATOR_GPG_PASSPHRASE",
        "social": "PURECORTEX_SOCIAL_GPG_PASSPHRASE",
        "vm": "PURECORTEX_VM_GPG_PASSPHRASE",
    }
    key_secret_name = key_secret_map.get(identity, "PURECORTEX_AGENT_GPG_SECRET_KEY")
    pass_secret_name = passphrase_map.get(identity, "PURECORTEX_AGENT_GPG_PASSPHRASE")

    secret_key = os.getenv(key_secret_name, "")
    passphrase = os.getenv(pass_secret_name, "")
    public_keys = os.getenv("PURECORTEX_GPG_PUBLIC_KEYS", "")

    # Try GCP Secret Manager if env vars are empty
    if not secret_key or not passphrase or not public_keys:
        try:
            from google.cloud import secretmanager
            sm_client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GCP_PROJECT_ID", "purecortexai")

            def _access(name: str) -> str:
                resource = f"projects/{project_id}/secrets/{name}/versions/latest"
                resp = sm_client.access_secret_version(request={"name": resource})
                return resp.payload.data.decode("utf-8")

            if not secret_key:
                secret_key = _access(key_secret_name)
            if not passphrase:
                passphrase = _access(pass_secret_name)
            if not public_keys:
                public_keys = _access("PURECORTEX_GPG_PUBLIC_KEYS")

            logger.info("Loaded GPG keys from Secret Manager for %s", identity)
        except Exception as e:
            logger.warning("Could not load GPG keys from Secret Manager: %s", e)

    if secret_key and passphrase and public_keys:
        await gpg.initialize(secret_key, passphrase, public_keys)
    else:
        logger.warning(
            "GPG keys not available for %s — encrypted operations will fail",
            identity,
        )

    return gpg


async def decrypt_mnemonic(gpg: GPGCrypto) -> Optional[str]:
    """
    Decrypt the deployer mnemonic from GCP Secret Manager.

    Returns the plaintext mnemonic or None if unavailable.
    """
    encrypted = os.getenv("PURECORTEX_DEPLOYER_MNEMONIC_GPG", "")

    if not encrypted:
        try:
            from google.cloud import secretmanager
            sm_client = secretmanager.SecretManagerServiceClient()
            project_id = os.getenv("GCP_PROJECT_ID", "purecortexai")
            resource = f"projects/{project_id}/secrets/PURECORTEX_DEPLOYER_MNEMONIC_GPG/versions/latest"
            resp = sm_client.access_secret_version(request={"name": resource})
            encrypted = resp.payload.data.decode("utf-8")
        except Exception as e:
            logger.warning("Could not load encrypted mnemonic: %s", e)
            return None

    if not encrypted:
        return None

    try:
        plaintext = await gpg.decrypt(encrypted)
        return plaintext.strip()
    except Exception as e:
        logger.error("Failed to decrypt mnemonic: %s", e)
        return None
