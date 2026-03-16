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
  PURECORTEX_<IDENTITY>_MNEMONIC_GPG — identity-scoped encrypted mnemonic
  PURECORTEX_DEPLOYER_MNEMONIC_GPG   — legacy shared mnemonic fallback
"""

import asyncio
import logging
import os
import shutil
import subprocess
import tempfile
from typing import Iterable, Optional

logger = logging.getLogger("purecortex.gpg")


GPG_SECRET_KEY_SECRET_NAMES = {
    "agent": "PURECORTEX_AGENT_GPG_SECRET_KEY",
    "senator": "PURECORTEX_SENATOR_GPG_SECRET_KEY",
    "curator": "PURECORTEX_CURATOR_GPG_SECRET_KEY",
    "social": "PURECORTEX_SOCIAL_GPG_SECRET_KEY",
    "vm": "PURECORTEX_VM_GPG_SECRET_KEY",
}

GPG_PASSPHRASE_SECRET_NAMES = {
    "agent": "PURECORTEX_AGENT_GPG_PASSPHRASE",
    "senator": "PURECORTEX_SENATOR_GPG_PASSPHRASE",
    "curator": "PURECORTEX_CURATOR_GPG_PASSPHRASE",
    "social": "PURECORTEX_SOCIAL_GPG_PASSPHRASE",
    "vm": "PURECORTEX_VM_GPG_PASSPHRASE",
}

MNEMONIC_SECRET_NAMES = {
    "agent": "PURECORTEX_AGENT_MNEMONIC_GPG",
    "senator": "PURECORTEX_SENATOR_MNEMONIC_GPG",
    "curator": "PURECORTEX_CURATOR_MNEMONIC_GPG",
    "social": "PURECORTEX_SOCIAL_MNEMONIC_GPG",
    "vm": "PURECORTEX_VM_MNEMONIC_GPG",
}

ALGORAND_ADDRESS_ENV_NAMES = {
    "agent": "PURECORTEX_AGENT_ALGORAND_ADDRESS",
    "senator": "PURECORTEX_SENATOR_ALGORAND_ADDRESS",
    "curator": "PURECORTEX_CURATOR_ALGORAND_ADDRESS",
    "social": "PURECORTEX_SOCIAL_ALGORAND_ADDRESS",
    "vm": "PURECORTEX_VM_ALGORAND_ADDRESS",
}

LEGACY_SHARED_MNEMONIC_SECRET_NAME = "PURECORTEX_DEPLOYER_MNEMONIC_GPG"
PLAINTEXT_EXPORT_FLAG = "PURECORTEX_ALLOW_PLAINTEXT_MNEMONIC_EXPORT"
DEFAULT_SECRET_DIR = "/run/purecortex/secrets"


def get_gpg_secret_key_secret_name(identity: str) -> str:
    return GPG_SECRET_KEY_SECRET_NAMES.get(identity, GPG_SECRET_KEY_SECRET_NAMES["agent"])


def get_gpg_passphrase_secret_name(identity: str) -> str:
    return GPG_PASSPHRASE_SECRET_NAMES.get(identity, GPG_PASSPHRASE_SECRET_NAMES["agent"])


def get_expected_algorand_address_env_name(identity: str) -> str:
    return ALGORAND_ADDRESS_ENV_NAMES.get(identity, ALGORAND_ADDRESS_ENV_NAMES["agent"])


def get_mnemonic_secret_candidates(identity: str) -> list[str]:
    preferred = MNEMONIC_SECRET_NAMES.get(identity, MNEMONIC_SECRET_NAMES["agent"])
    candidates = [preferred]
    if preferred != LEGACY_SHARED_MNEMONIC_SECRET_NAME:
        candidates.append(LEGACY_SHARED_MNEMONIC_SECRET_NAME)
    return candidates


def load_secret_value(secret_name: str, *, allow_env: bool = True) -> str:
    secret_dir = os.getenv("PURECORTEX_SECRET_DIR", DEFAULT_SECRET_DIR).strip()
    if secret_dir:
        secret_path = os.path.join(secret_dir, secret_name)
        try:
            if os.path.isfile(secret_path):
                with open(secret_path, "r", encoding="utf-8") as handle:
                    return handle.read().strip()
        except Exception:
            pass

    file_env = os.getenv(f"{secret_name}_FILE", "").strip()
    if file_env:
        with open(file_env, "r", encoding="utf-8") as handle:
            return handle.read().strip()

    if allow_env:
        env_val = os.getenv(secret_name, "")
        if env_val:
            return env_val

    from google.cloud import secretmanager

    client = secretmanager.SecretManagerServiceClient()
    project_id = os.getenv("GCP_PROJECT_ID", "purecortexai")
    name = f"projects/{project_id}/secrets/{secret_name}/versions/latest"
    response = client.access_secret_version(request={"name": name})
    return response.payload.data.decode("utf-8")


def load_first_available_secret(
    secret_names: Iterable[str], *, allow_env: bool = True
) -> tuple[Optional[str], str]:
    errors: list[str] = []
    for secret_name in secret_names:
        try:
            value = load_secret_value(secret_name, allow_env=allow_env)
        except Exception as exc:
            errors.append(f"{secret_name}: {exc}")
            continue

        if value:
            return secret_name, value

    if errors:
        raise RuntimeError("; ".join(errors))

    return None, ""


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
        try:
            return load_secret_value(get_gpg_passphrase_secret_name(self.identity))
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

    key_secret_name = get_gpg_secret_key_secret_name(identity)
    pass_secret_name = get_gpg_passphrase_secret_name(identity)

    secret_key = ""
    passphrase = ""
    public_keys = ""

    try:
        secret_key = load_secret_value(key_secret_name)
        passphrase = load_secret_value(pass_secret_name)
        public_keys = load_secret_value("PURECORTEX_GPG_PUBLIC_KEYS")
        logger.info("Loaded GPG key material for %s", identity)
    except Exception as e:
        logger.warning("Could not load GPG keys for %s: %s", identity, e)

    if secret_key and passphrase and public_keys:
        try:
            await gpg.initialize(secret_key, passphrase, public_keys)
        finally:
            secret_key = "0" * len(secret_key)
            passphrase = "0" * len(passphrase)
            del secret_key, passphrase
    else:
        logger.warning(
            "GPG keys not available for %s — encrypted operations will fail",
            identity,
        )

    return gpg


async def decrypt_mnemonic(gpg: GPGCrypto) -> Optional[str]:
    """
    Break-glass helper to decrypt an agent mnemonic into plaintext memory.

    This is intentionally disabled by default. Set
    PURECORTEX_ALLOW_PLAINTEXT_MNEMONIC_EXPORT=1 only for a temporary,
    audited recovery workflow.
    """
    if os.getenv(PLAINTEXT_EXPORT_FLAG) != "1":
        logger.warning(
            "Plaintext mnemonic export is disabled. Set %s=1 only for audited recovery operations.",
            PLAINTEXT_EXPORT_FLAG,
        )
        return None

    encrypted_name: Optional[str] = None
    encrypted = ""

    try:
        encrypted_name, encrypted = load_first_available_secret(
            get_mnemonic_secret_candidates(gpg.identity)
        )
    except Exception as e:
        logger.warning("Could not load encrypted mnemonic for %s: %s", gpg.identity, e)
        return None

    if not encrypted_name or not encrypted:
        return None

    if encrypted_name == LEGACY_SHARED_MNEMONIC_SECRET_NAME:
        preferred = get_mnemonic_secret_candidates(gpg.identity)[0]
        logger.warning(
            "Using legacy shared mnemonic secret %s for %s. Configure %s to isolate signer identities.",
            LEGACY_SHARED_MNEMONIC_SECRET_NAME,
            gpg.identity,
            preferred,
        )

    try:
        plaintext = await gpg.decrypt(encrypted)
        return plaintext.strip()
    except Exception as e:
        logger.error("Failed to decrypt mnemonic: %s", e)
        return None
