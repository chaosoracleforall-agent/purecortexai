# Testnet Smoke Harness

`contracts/tests/live_testnet_verify.py` is the disposable-wallet smoke harness for the canonical PURECORTEX testnet deployment.

It is split into two phases:

1. `prepare`: generate disposable wallets and print the funding path.
2. `smoke`: run creator-approved CORTEX seeding plus live create/buy/sell checks, with an optional governance proposal/review/vote smoke step against the current backend API.

## Funding Path

Use the official Algorand TestNet dispenser:

- `https://bank.testnet.algorand.network/`

Fund the generated `trader` wallet with at least `5 ALGO` before running the smoke step.

## Required Environment

- `DEPLOYER_MNEMONIC`: creator wallet mnemonic for the canonical testnet factory deployment.
- `PURECORTEX_API_KEY`: optional, only needed if you want the governance API smoke step to run.

## Prepare Disposable Wallets

```bash
cd contracts
PYTHONPATH=. .venv/bin/python tests/live_testnet_verify.py prepare
```

That command writes a wallet bundle at `contracts/tests/.testnet-smoke-wallets.json` and prints the addresses that need TestNet ALGOs.

## Run Smoke Test

```bash
cd contracts
export DEPLOYER_MNEMONIC="..."
export PURECORTEX_API_KEY="ctx_..."
PYTHONPATH=. .venv/bin/python tests/live_testnet_verify.py smoke
```

## What The Smoke Step Covers

- Ensures the factory app address has enough ALGO to cover testnet MBR.
- Opts the disposable trader into `CORTEX`.
- Seeds `CORTEX` from the creator-approved `distribute_cortex()` flow.
- Creates a new disposable agent token.
- Opts the trader into the new agent ASA.
- Buys tokens from the bonding curve.
- Sells tokens back into the bonding curve.
- Optionally exercises the live governance API source of truth:
  - Senator proposal creation
  - Curator review
  - Vote submission

## Notes

- Governance voting in this harness targets the live backend governance API because the frontend and API now use that source of truth until on-chain governance execution is fully rolled out.
- The wallet bundle contains disposable mnemonics. Treat it as sensitive and delete it after use.
