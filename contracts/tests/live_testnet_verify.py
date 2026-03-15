from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from algosdk import abi, account, encoding, logic, mnemonic, transaction
from algosdk.atomic_transaction_composer import (
    AccountTransactionSigner,
    AtomicTransactionComposer,
    TransactionWithSigner,
)
from algosdk.v2client import algod


ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = ROOT / "deployment.testnet.json"
DEFAULT_WALLET_FILE = Path(__file__).resolve().parent / ".testnet-smoke-wallets.json"

ALGOD_URL = "https://testnet-api.algonode.cloud"
DISPENSER_URL = "https://bank.testnet.algorand.network/"
DEFAULT_MIN_TRADER_ALGO = 5_000_000
DEFAULT_CORTEX_SEED = 250_000_000
DEFAULT_BUY_AMOUNT = 2_000_000
DEFAULT_SELL_AMOUNT = 1_000_000
DEFAULT_APP_TOP_UP = 1_000_000

CREATE_AGENT_METHOD = abi.Method.from_signature("create_agent(axfer,string,string)uint64")
BUY_TOKENS_METHOD = abi.Method.from_signature("buy_tokens(pay,uint64,uint64)void")
SELL_TOKENS_METHOD = abi.Method.from_signature("sell_tokens(axfer,uint64,uint64)void")
DISTRIBUTE_CORTEX_METHOD = abi.Method.from_signature("distribute_cortex(address,uint64)void")


@dataclass
class WalletRecord:
    label: str
    address: str
    mnemonic: str

    @property
    def private_key(self) -> str:
        return mnemonic.to_private_key(self.mnemonic)

    @property
    def signer(self) -> AccountTransactionSigner:
        return AccountTransactionSigner(self.private_key)


def load_manifest() -> dict[str, Any]:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def algod_client() -> algod.AlgodClient:
    return algod.AlgodClient("", ALGOD_URL)


def generate_wallet(label: str) -> WalletRecord:
    private_key, address = account.generate_account()
    return WalletRecord(
        label=label,
        address=address,
        mnemonic=mnemonic.from_private_key(private_key),
    )


def save_wallets(wallet_file: Path, wallets: list[WalletRecord]) -> None:
    wallet_file.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "created_at": int(time.time()),
        "wallets": [asdict(wallet) for wallet in wallets],
    }
    wallet_file.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def load_wallets(wallet_file: Path) -> dict[str, WalletRecord]:
    payload = json.loads(wallet_file.read_text(encoding="utf-8"))
    wallets = {}
    for wallet in payload.get("wallets", []):
        record = WalletRecord(**wallet)
        wallets[record.label] = record
    return wallets


def print_funding_instructions(wallets: dict[str, WalletRecord], min_trader_algo: int) -> None:
    print("\nFunding instructions")
    print("====================")
    print(f"Use the Algorand TestNet dispenser: {DISPENSER_URL}")
    print()
    for wallet in wallets.values():
        print(f"- {wallet.label}: {wallet.address}")
    print()
    print(
        f"Fund the `trader` wallet with at least {min_trader_algo / 1_000_000:.1f} ALGO "
        "before running `smoke`."
    )
    print(
        "The `voter` wallet is optional for the governance API smoke step, but generating it now "
        "keeps the wallet bundle ready for future extensions."
    )


def http_json(
    method: str,
    url: str,
    *,
    body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> tuple[int, dict[str, Any]]:
    request_headers = {
        "Accept": "application/json",
        **(headers or {}),
    }
    payload = None
    if body is not None:
        payload = json.dumps(body).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(url, data=payload, headers=request_headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raw = exc.read().decode("utf-8") or "{}"
        try:
            return exc.code, json.loads(raw)
        except json.JSONDecodeError:
            return exc.code, {"detail": raw}


def account_balance(algod_client_: algod.AlgodClient, address: str) -> int:
    return int(algod_client_.account_info(address)["amount"])


def wait_for_algo_funding(
    algod_client_: algod.AlgodClient,
    address: str,
    minimum_microalgos: int,
    timeout_seconds: int,
) -> None:
    deadline = time.time() + timeout_seconds
    while time.time() < deadline:
        if account_balance(algod_client_, address) >= minimum_microalgos:
            return
        time.sleep(5)
    raise RuntimeError(
        f"Wallet {address} did not reach {minimum_microalgos / 1_000_000:.1f} ALGO within {timeout_seconds}s."
    )


def is_asset_opted_in(algod_client_: algod.AlgodClient, address: str, asset_id: int) -> bool:
    account_info = algod_client_.account_info(address)
    return any(asset.get("asset-id") == asset_id for asset in account_info.get("assets", []))


def send_transaction(
    algod_client_: algod.AlgodClient,
    txn: transaction.Transaction,
    private_key: str,
) -> str:
    signed = txn.sign(private_key)
    txid = algod_client_.send_transaction(signed)
    transaction.wait_for_confirmation(algod_client_, txid, 8)
    return txid


def opt_in_asset(
    algod_client_: algod.AlgodClient,
    wallet: WalletRecord,
    asset_id: int,
) -> str | None:
    if is_asset_opted_in(algod_client_, wallet.address, asset_id):
        return None

    params = algod_client_.suggested_params()
    txn = transaction.AssetTransferTxn(
        sender=wallet.address,
        sp=params,
        receiver=wallet.address,
        amt=0,
        index=asset_id,
    )
    return send_transaction(algod_client_, txn, wallet.private_key)


def ensure_app_balance(
    algod_client_: algod.AlgodClient,
    creator: WalletRecord,
    app_address: str,
    minimum_microalgos: int,
) -> str | None:
    if account_balance(algod_client_, app_address) >= minimum_microalgos:
        return None

    params = algod_client_.suggested_params()
    txn = transaction.PaymentTxn(
        sender=creator.address,
        sp=params,
        receiver=app_address,
        amt=minimum_microalgos,
    )
    return send_transaction(algod_client_, txn, creator.private_key)


def calculate_buy_price(current_supply: int, amount: int, manifest: dict[str, Any]) -> int:
    base_price = manifest["tokenomics"]["basePrice"]
    slope = manifest["tokenomics"]["slope"]
    buy_fee_bps = manifest["tokenomics"]["buyFeeBps"]

    base_cost = amount * base_price
    area_doubled = (2 * current_supply * amount) + (amount * amount)
    slope_cost = (slope * area_doubled) // 2
    raw_cost = base_cost + slope_cost
    fee = (raw_cost * buy_fee_bps) // 10_000
    return raw_cost + fee


def create_agent(
    algod_client_: algod.AlgodClient,
    manifest: dict[str, Any],
    trader: WalletRecord,
    name: str,
    symbol: str,
) -> tuple[int, str]:
    factory_app_id = manifest["contracts"]["agentFactory"]["appId"]
    cortex_asset_id = manifest["contracts"]["cortexToken"]["assetId"]
    creation_fee = manifest["tokenomics"]["creationFee"]
    params = algod_client_.suggested_params()

    payment_txn = transaction.AssetTransferTxn(
        sender=trader.address,
        sp=params,
        receiver=logic.get_application_address(factory_app_id),
        amt=creation_fee,
        index=cortex_asset_id,
    )

    composer = AtomicTransactionComposer()
    composer.add_method_call(
        app_id=factory_app_id,
        method=CREATE_AGENT_METHOD,
        sender=trader.address,
        sp=params,
        signer=trader.signer,
        method_args=[
            TransactionWithSigner(payment_txn, trader.signer),
            name,
            symbol,
        ],
    )
    result = composer.execute(algod_client_, 8)
    return int(result.abi_results[0].return_value), result.tx_ids[-1]


def distribute_cortex(
    algod_client_: algod.AlgodClient,
    manifest: dict[str, Any],
    creator: WalletRecord,
    receiver: str,
    amount: int,
) -> str:
    composer = AtomicTransactionComposer()
    composer.add_method_call(
        app_id=manifest["contracts"]["agentFactory"]["appId"],
        method=DISTRIBUTE_CORTEX_METHOD,
        sender=creator.address,
        sp=algod_client_.suggested_params(),
        signer=creator.signer,
        method_args=[receiver, amount],
    )
    result = composer.execute(algod_client_, 8)
    return result.tx_ids[-1]


def buy_tokens(
    algod_client_: algod.AlgodClient,
    manifest: dict[str, Any],
    trader: WalletRecord,
    asset_id: int,
    amount: int,
    current_supply: int,
) -> str:
    factory_app_id = manifest["contracts"]["agentFactory"]["appId"]
    total_algo = calculate_buy_price(current_supply, amount, manifest)
    params = algod_client_.suggested_params()

    payment_txn = transaction.PaymentTxn(
        sender=trader.address,
        sp=params,
        receiver=logic.get_application_address(factory_app_id),
        amt=total_algo,
    )

    composer = AtomicTransactionComposer()
    composer.add_method_call(
        app_id=factory_app_id,
        method=BUY_TOKENS_METHOD,
        sender=trader.address,
        sp=params,
        signer=trader.signer,
        method_args=[
            TransactionWithSigner(payment_txn, trader.signer),
            asset_id,
            amount,
        ],
        boxes=[(factory_app_id, asset_id.to_bytes(8, "big"))],
    )
    result = composer.execute(algod_client_, 8)
    return result.tx_ids[-1]


def sell_tokens(
    algod_client_: algod.AlgodClient,
    manifest: dict[str, Any],
    trader: WalletRecord,
    asset_id: int,
    amount: int,
) -> str:
    factory_app_id = manifest["contracts"]["agentFactory"]["appId"]
    params = algod_client_.suggested_params()
    transfer_txn = transaction.AssetTransferTxn(
        sender=trader.address,
        sp=params,
        receiver=logic.get_application_address(factory_app_id),
        amt=amount,
        index=asset_id,
    )

    composer = AtomicTransactionComposer()
    composer.add_method_call(
        app_id=factory_app_id,
        method=SELL_TOKENS_METHOD,
        sender=trader.address,
        sp=params,
        signer=trader.signer,
        method_args=[
            TransactionWithSigner(transfer_txn, trader.signer),
            asset_id,
            amount,
        ],
        boxes=[(factory_app_id, asset_id.to_bytes(8, "big"))],
    )
    result = composer.execute(algod_client_, 8)
    return result.tx_ids[-1]


def governance_smoke(
    api_base_url: str,
    api_key: str,
    voter_id: str,
) -> dict[str, Any]:
    headers = {"X-API-Key": api_key}
    title = f"Testnet smoke proposal {int(time.time())}"

    status, proposal_payload = http_json(
        "POST",
        f"{api_base_url.rstrip('/')}/api/agents/senator/propose",
        headers=headers,
        body={
            "title": title,
            "description": "Smoke test proposal generated by the testnet QA harness.",
            "type": "general",
        },
    )
    if status != 201:
        raise RuntimeError(f"Failed to create governance proposal: {proposal_payload}")

    proposal_id = int(proposal_payload["proposal"]["id"])

    status, review_payload = http_json(
        "POST",
        f"{api_base_url.rstrip('/')}/api/agents/curator/review/{proposal_id}",
        headers=headers,
    )
    if status != 200:
        raise RuntimeError(f"Failed to review governance proposal: {review_payload}")

    status, vote_payload = http_json(
        "POST",
        f"{api_base_url.rstrip('/')}/api/governance/proposals/{proposal_id}/vote",
        headers=headers,
        body={"voter": voter_id, "vote": "for", "weight": 1},
    )
    if status != 200:
        raise RuntimeError(f"Failed to vote on governance proposal: {vote_payload}")

    return {
        "proposal_id": proposal_id,
        "review_status": review_payload["proposal"]["status"],
        "vote_result": vote_payload,
    }


def prepare(wallet_file: Path, min_trader_algo: int) -> int:
    wallets = {
        "trader": generate_wallet("trader"),
        "voter": generate_wallet("voter"),
    }
    save_wallets(wallet_file, list(wallets.values()))
    print(f"Saved disposable wallet bundle to {wallet_file}")
    print_funding_instructions(wallets, min_trader_algo)
    return 0


def smoke(
    wallet_file: Path,
    *,
    api_base_url: str,
    api_key: str | None,
    wait_timeout: int,
    min_trader_algo: int,
    cortex_seed_amount: int,
    buy_amount: int,
    sell_amount: int,
    app_top_up: int,
) -> int:
    if not wallet_file.exists():
        raise RuntimeError(f"Wallet bundle not found at {wallet_file}. Run `prepare` first.")

    creator_mnemonic = os.getenv("DEPLOYER_MNEMONIC")
    if not creator_mnemonic:
        raise RuntimeError("DEPLOYER_MNEMONIC is required for the smoke run.")

    manifest = load_manifest()
    wallets = load_wallets(wallet_file)
    if "trader" not in wallets or "voter" not in wallets:
        raise RuntimeError("Wallet bundle must contain `trader` and `voter` entries.")

    trader = wallets["trader"]
    voter = wallets["voter"]
    creator = WalletRecord(
        label="creator",
        address=account.address_from_private_key(mnemonic.to_private_key(creator_mnemonic)),
        mnemonic=creator_mnemonic,
    )

    algod_client_ = algod_client()
    app_address = logic.get_application_address(manifest["contracts"]["agentFactory"]["appId"])

    print("Waiting for trader wallet funding...")
    wait_for_algo_funding(algod_client_, trader.address, min_trader_algo, wait_timeout)
    print(f"Trader funded: {trader.address}")

    summary: dict[str, Any] = {
        "network": manifest["chainName"],
        "factory_app_id": manifest["contracts"]["agentFactory"]["appId"],
        "cortex_asset_id": manifest["contracts"]["cortexToken"]["assetId"],
        "trader": trader.address,
        "voter": voter.address,
    }

    summary["app_top_up_txid"] = ensure_app_balance(algod_client_, creator, app_address, app_top_up)
    summary["cortex_opt_in_txid"] = opt_in_asset(
        algod_client_,
        trader,
        manifest["contracts"]["cortexToken"]["assetId"],
    )
    summary["cortex_seed_txid"] = distribute_cortex(
        algod_client_,
        manifest,
        creator,
        trader.address,
        cortex_seed_amount,
    )

    agent_name = f"Smoke Agent {int(time.time())}"
    agent_symbol = f"SMK{int(time.time()) % 1000:03d}"[:8]
    agent_asset_id, create_txid = create_agent(
        algod_client_,
        manifest,
        trader,
        agent_name,
        agent_symbol,
    )
    summary["agent_asset_id"] = agent_asset_id
    summary["create_agent_txid"] = create_txid

    summary["agent_opt_in_txid"] = opt_in_asset(algod_client_, trader, agent_asset_id)
    summary["buy_txid"] = buy_tokens(
        algod_client_,
        manifest,
        trader,
        agent_asset_id,
        buy_amount,
        current_supply=0,
    )
    summary["sell_txid"] = sell_tokens(
        algod_client_,
        manifest,
        trader,
        agent_asset_id,
        sell_amount,
    )

    if api_key:
        summary["governance_smoke"] = governance_smoke(
            api_base_url=api_base_url,
            api_key=api_key,
            voter_id=voter.address,
        )
    else:
        summary["governance_smoke"] = {
            "skipped": True,
            "reason": "Set PURECORTEX_API_KEY to run the live governance proposal/review/vote smoke step.",
        }

    print(json.dumps(summary, indent=2))
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="PURECORTEX testnet smoke harness for disposable wallets and factory flows.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare_parser = subparsers.add_parser("prepare", help="Generate disposable wallets and funding instructions.")
    prepare_parser.add_argument("--wallet-file", type=Path, default=DEFAULT_WALLET_FILE)
    prepare_parser.add_argument("--min-trader-algo", type=int, default=DEFAULT_MIN_TRADER_ALGO)

    smoke_parser = subparsers.add_parser("smoke", help="Run create/buy/sell smoke tests against the live testnet deployment.")
    smoke_parser.add_argument("--wallet-file", type=Path, default=DEFAULT_WALLET_FILE)
    smoke_parser.add_argument("--api-base-url", default=load_manifest()["publicApiUrl"])
    smoke_parser.add_argument("--wait-timeout", type=int, default=600)
    smoke_parser.add_argument("--min-trader-algo", type=int, default=DEFAULT_MIN_TRADER_ALGO)
    smoke_parser.add_argument("--cortex-seed-amount", type=int, default=DEFAULT_CORTEX_SEED)
    smoke_parser.add_argument("--buy-amount", type=int, default=DEFAULT_BUY_AMOUNT)
    smoke_parser.add_argument("--sell-amount", type=int, default=DEFAULT_SELL_AMOUNT)
    smoke_parser.add_argument("--app-top-up", type=int, default=DEFAULT_APP_TOP_UP)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "prepare":
        return prepare(args.wallet_file, args.min_trader_algo)

    return smoke(
        args.wallet_file,
        api_base_url=args.api_base_url,
        api_key=os.getenv("PURECORTEX_API_KEY"),
        wait_timeout=args.wait_timeout,
        min_trader_algo=args.min_trader_algo,
        cortex_seed_amount=args.cortex_seed_amount,
        buy_amount=args.buy_amount,
        sell_amount=args.sell_amount,
        app_top_up=args.app_top_up,
    )


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # pragma: no cover - CLI safety net
        print(f"Smoke harness failed: {exc}", file=sys.stderr)
        raise SystemExit(1)
