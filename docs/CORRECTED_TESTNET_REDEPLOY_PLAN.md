# Corrected Testnet Redeploy Plan

## Why a fresh deployment is needed

The current AgentFactory deployment is unsuitable for live marketplace trading.

- Bonding-curve math is using micro-token units directly without scaling by the token decimals.
- The marketplace UI was inferring curve supply from asset-holder balances instead of the factory's authoritative `agent_supplies` box state.
- Existing launched testnet agents remain useful for auditability and wallet/connectivity testing, but not for trustworthy market pricing.

## Immediate safety posture

- Keep **agent launch** enabled for controlled validation.
- Keep **buy / sell trading disabled** in public UX and tooling until the corrected factory is deployed.
- Surface the disabled-trading status consistently through:
  - `GET /api/marketplace/config`
  - SDKs
  - CLI
  - MCP

## Corrected factory requirements

### 1. Fix token-decimal scaling in contract math

The factory should treat all token amounts as 6-decimal micro-units and scale price calculations accordingly:

- `base_cost = amount * BASE_PRICE / TOKEN_SCALE`
- `slope_cost = SLOPE * (2*supply*amount + amount^2) / (2 * TOKEN_SCALE^2)`

The same scaling must be applied to:

- `calculate_buy_price`
- `calculate_sell_price`
- graduation-threshold progress

### 2. Support per-agent launch parameters

The next factory should allow the creator to set bounded launch parameters per agent:

- base price
- slope
- buy fee bps
- sell fee bps
- optional graduation threshold override

Recommended constraints:

- lower and upper bounds enforced on-chain
- protocol owner/governance can cap dangerous values
- launch transaction stores an immutable per-agent config record

### 3. Store per-agent config and supply separately

Each agent should have:

- a per-agent config box
- a per-agent live supply box

The frontend and tooling should read these directly or through backend mirrors rather than reconstructing them from indexer balances.

## Surface updates required

### Frontend

- Launch modal should expose bounded price/fee parameters to creators.
- Buy/sell UI should read:
  - live supply
  - agent-specific curve parameters
  - protocol fees

### API

- Add marketplace read endpoints for:
  - marketplace config/status
  - per-agent config
  - live supply
  - computed quote previews

### SDK / CLI / MCP

- Add marketplace status/config reads
- Add per-agent config inspection
- Add quote helpers where appropriate
- Keep launch/trade writes disabled until the corrected deployment is active

## Recommended deployment sequence

1. Finalize corrected factory contract math.
2. Add per-agent parameter model and regenerate artifacts.
3. Deploy the corrected factory to testnet.
4. Bootstrap a fresh `CORTEX` testnet asset if the deployment model requires it.
5. Update `deployment.testnet.json` with the new:
   - factory app ID
   - asset ID
   - escrow / creator addresses
6. Update the frontend, SDK, CLI, and MCP defaults to the new deployment.
7. Re-enable public buy / sell flows only after:
   - a real launch
   - a real buy
   - a real sell
   - supply and quote verification

## Validation checklist

- Launching a new agent succeeds from a real wallet
- Explorer shows the expected factory-created ASA
- Buy quote matches on-chain transaction requirements
- Sell quote matches on-chain return minus fee
- Marketplace displays:
  - correct live supply
  - correct holder count
  - sane token price
  - sane curve value

## Legacy deployment handling

- Keep the current broken deployment visible only for historical and audit context.
- Mark it clearly as **deprecated for trading** in all public surfaces.
- Do not route new live trading through the current factory once the corrected one is available.
