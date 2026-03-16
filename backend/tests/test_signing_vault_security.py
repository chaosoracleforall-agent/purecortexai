from __future__ import annotations

import asyncio
import base64
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


from src.services import gpg_crypto
from src.services.gpg_crypto import LEGACY_SHARED_MNEMONIC_SECRET_NAME
from src.services.signing_vault import SigningVault, create_signing_vault


def test_mnemonic_secret_candidates_prefer_identity_specific_secret():
    candidates = gpg_crypto.get_mnemonic_secret_candidates("social")

    assert candidates[0] == "PURECORTEX_SOCIAL_MNEMONIC_GPG"
    assert LEGACY_SHARED_MNEMONIC_SECRET_NAME in candidates


def test_decrypt_mnemonic_requires_explicit_opt_in(monkeypatch):
    class DummyGPG:
        identity = "social"
        called = False

        async def decrypt(self, _ciphertext: str) -> str:
            self.called = True
            return "mnemonic words"

    dummy = DummyGPG()
    monkeypatch.delenv(gpg_crypto.PLAINTEXT_EXPORT_FLAG, raising=False)

    plaintext = asyncio.run(gpg_crypto.decrypt_mnemonic(dummy))

    assert plaintext is None
    assert dummy.called is False


def test_create_signing_vault_prefers_identity_scoped_configuration(monkeypatch):
    monkeypatch.setenv("PURECORTEX_SOCIAL_ALGORAND_ADDRESS", "SOCIALADDR")

    vault = asyncio.run(create_signing_vault("social"))

    assert vault._mnemonic_secret_candidates[0] == "PURECORTEX_SOCIAL_MNEMONIC_GPG"
    assert LEGACY_SHARED_MNEMONIC_SECRET_NAME in vault._mnemonic_secret_candidates
    assert vault._gpg_secret_key_secret_name == "PURECORTEX_SOCIAL_GPG_SECRET_KEY"
    assert vault._expected_sender == "SOCIALADDR"
    assert vault._encrypted_mnemonic is None
    assert vault._gpg_secret_key is None


def test_sign_transaction_fetches_secret_material_per_operation(monkeypatch):
    captured: dict[str, object] = {}

    def fake_load_first_available_secret(_names, *, allow_env=True):
        assert allow_env is True
        return "PURECORTEX_SOCIAL_MNEMONIC_GPG", "encrypted-mnemonic"

    def fake_load_secret_value(secret_name: str, *, allow_env: bool = True) -> str:
        values = {
            "PURECORTEX_SOCIAL_GPG_SECRET_KEY": "armored-secret-key",
            "PURECORTEX_GPG_PUBLIC_KEYS": "armored-public-keys",
            "PURECORTEX_SOCIAL_GPG_PASSPHRASE": "sign-passphrase",
        }
        return values[secret_name]

    async def fake_get_passphrase() -> str:
        return "sign-passphrase"

    async def fake_run_isolated(script: str, input_data: str, timeout: int = 30) -> dict:
        captured["script"] = script
        captured["timeout"] = timeout
        captured["payload"] = json.loads(input_data)
        return {
            "signed_txn_b64": base64.b64encode(b"signed-by-vault").decode(),
            "sender": "SOCIALADDR",
        }

    monkeypatch.setattr("src.services.signing_vault.load_first_available_secret", fake_load_first_available_secret)
    monkeypatch.setattr("src.services.signing_vault.load_secret_value", fake_load_secret_value)

    vault = SigningVault(identity="social")
    asyncio.run(
        vault.initialize(
            mnemonic_secret_candidates=["PURECORTEX_SOCIAL_MNEMONIC_GPG"],
            gpg_secret_key_secret_name="PURECORTEX_SOCIAL_GPG_SECRET_KEY",
            expected_sender="SOCIALADDR",
        )
    )
    monkeypatch.setattr(vault, "_get_passphrase", fake_get_passphrase)
    monkeypatch.setattr(vault, "_run_isolated", fake_run_isolated)

    signed_txn = asyncio.run(vault.sign_transaction(b"unsigned-transaction"))

    assert signed_txn == b"signed-by-vault"
    assert captured["timeout"] == 30
    payload = captured["payload"]
    assert payload["encrypted_mnemonic"] == "encrypted-mnemonic"
    assert payload["gpg_secret_key"] == "armored-secret-key"
    assert payload["gpg_public_keys"] == "armored-public-keys"
    assert payload["gpg_passphrase"] == "sign-passphrase"
    assert payload["expected_sender"] == "SOCIALADDR"
