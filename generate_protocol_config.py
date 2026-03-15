from __future__ import annotations

import json
from pathlib import Path
from pprint import pformat


ROOT = Path(__file__).resolve().parent
MANIFEST_PATH = ROOT / "deployment.testnet.json"
BACKEND_OUTPUT = ROOT / "backend" / "src" / "services" / "protocol_config.py"
FRONTEND_OUTPUT = ROOT / "frontend" / "src" / "lib" / "protocolConfig.ts"


def load_manifest() -> dict:
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


def render_backend(manifest: dict) -> str:
    return f'''"""
Generated from `deployment.testnet.json` by `generate_protocol_config.py`.
Do not edit by hand.
"""

from __future__ import annotations

from typing import Any, Final


PROTOCOL_CONFIG: Final[dict[str, Any]] = {pformat(manifest, sort_dicts=False)}

NAME: Final = PROTOCOL_CONFIG["name"]
ENVIRONMENT: Final = PROTOCOL_CONFIG["environment"]
NETWORK: Final = PROTOCOL_CONFIG["network"]
CHAIN_NAME: Final = PROTOCOL_CONFIG["chainName"]
PUBLIC_APP_URL: Final = PROTOCOL_CONFIG["publicAppUrl"]
PUBLIC_API_URL: Final = PROTOCOL_CONFIG["publicApiUrl"]
PUBLIC_WS_URL: Final = PROTOCOL_CONFIG["publicWsUrl"]
REPO_URL: Final = PROTOCOL_CONFIG["repoUrl"]
TGE_DATE_ISO: Final = PROTOCOL_CONFIG["tgeDate"]

FACTORY_APP_ID: Final = PROTOCOL_CONFIG["contracts"]["agentFactory"]["appId"]
FACTORY_ADDRESS: Final = PROTOCOL_CONFIG["contracts"]["agentFactory"]["address"]
CORTEX_ASSET_ID: Final = PROTOCOL_CONFIG["contracts"]["cortexToken"]["assetId"]
CORTEX_NAME: Final = PROTOCOL_CONFIG["contracts"]["cortexToken"]["name"]
CORTEX_UNIT_NAME: Final = PROTOCOL_CONFIG["contracts"]["cortexToken"]["unitName"]
GOVERNANCE_APP_ID: Final = PROTOCOL_CONFIG["contracts"]["governance"]["appId"]
STAKING_APP_ID: Final = PROTOCOL_CONFIG["contracts"]["staking"]["appId"]
TREASURY_APP_ID: Final = PROTOCOL_CONFIG["contracts"]["treasury"]["appId"]

TOTAL_SUPPLY: Final = PROTOCOL_CONFIG["tokenomics"]["totalSupply"]
TOKEN_DECIMALS: Final = PROTOCOL_CONFIG["tokenomics"]["decimals"]
BASE_PRICE: Final = PROTOCOL_CONFIG["tokenomics"]["basePrice"]
SLOPE: Final = PROTOCOL_CONFIG["tokenomics"]["slope"]
CREATION_FEE: Final = PROTOCOL_CONFIG["tokenomics"]["creationFee"]
BUY_FEE_BPS: Final = PROTOCOL_CONFIG["tokenomics"]["buyFeeBps"]
SELL_FEE_BPS: Final = PROTOCOL_CONFIG["tokenomics"]["sellFeeBps"]
GRADUATION_THRESHOLD: Final = PROTOCOL_CONFIG["tokenomics"]["graduationThreshold"]

AGENT_FACTORY_ESCROW: Final = PROTOCOL_CONFIG["wallets"]["agentFactoryEscrow"]
ASSISTANCE_FUND_ADDRESS: Final = PROTOCOL_CONFIG["wallets"]["assistanceFund"]
OPERATIONS_ADDRESS: Final = PROTOCOL_CONFIG["wallets"]["operations"]
CREATOR_VESTING_ADDRESS: Final = PROTOCOL_CONFIG["wallets"]["creatorVesting"]

LEGACY_DEPLOYMENTS: Final = PROTOCOL_CONFIG["legacyDeployments"]
'''


def render_frontend(manifest: dict) -> str:
    json_blob = json.dumps(manifest, indent=2)
    return f"""// Generated from `deployment.testnet.json` by `generate_protocol_config.py`.
// Do not edit by hand.

export const protocolConfig = {json_blob} as const;

export type ProtocolConfig = typeof protocolConfig;

export const PROTOCOL_NAME = protocolConfig.name;
export const PROTOCOL_ENVIRONMENT = protocolConfig.environment;
export const PROTOCOL_NETWORK = protocolConfig.network;
export const CHAIN_NAME = protocolConfig.chainName;
export const PUBLIC_APP_URL = protocolConfig.publicAppUrl;
export const PUBLIC_API_URL = protocolConfig.publicApiUrl;
export const PUBLIC_WS_URL = protocolConfig.publicWsUrl;
export const REPO_URL = protocolConfig.repoUrl;
export const TGE_DATE_ISO = protocolConfig.tgeDate;

export const FACTORY_APP_ID = protocolConfig.contracts.agentFactory.appId;
export const FACTORY_ADDRESS = protocolConfig.contracts.agentFactory.address;
export const CORTEX_ASSET_ID = protocolConfig.contracts.cortexToken.assetId;
export const CORTEX_NAME = protocolConfig.contracts.cortexToken.name;
export const CORTEX_UNIT_NAME = protocolConfig.contracts.cortexToken.unitName;
export const GOVERNANCE_APP_ID = protocolConfig.contracts.governance.appId;
export const STAKING_APP_ID = protocolConfig.contracts.staking.appId;
export const TREASURY_APP_ID = protocolConfig.contracts.treasury.appId;

export const TOTAL_SUPPLY = protocolConfig.tokenomics.totalSupply;
export const TOKEN_DECIMALS = protocolConfig.tokenomics.decimals;
export const BASE_PRICE = protocolConfig.tokenomics.basePrice;
export const SLOPE = protocolConfig.tokenomics.slope;
export const CREATION_FEE = protocolConfig.tokenomics.creationFee;
export const BUY_FEE_BPS = protocolConfig.tokenomics.buyFeeBps;
export const SELL_FEE_BPS = protocolConfig.tokenomics.sellFeeBps;
export const GRADUATION_THRESHOLD = protocolConfig.tokenomics.graduationThreshold;

export const AGENT_FACTORY_ESCROW = protocolConfig.wallets.agentFactoryEscrow;
export const ASSISTANCE_FUND_ADDRESS = protocolConfig.wallets.assistanceFund;
export const OPERATIONS_ADDRESS = protocolConfig.wallets.operations;
export const CREATOR_VESTING_ADDRESS = protocolConfig.wallets.creatorVesting;

export const LEGACY_DEPLOYMENTS = protocolConfig.legacyDeployments;
"""


def main() -> None:
    manifest = load_manifest()
    BACKEND_OUTPUT.write_text(render_backend(manifest), encoding="utf-8")
    FRONTEND_OUTPUT.write_text(render_frontend(manifest), encoding="utf-8")
    print(f"Wrote {BACKEND_OUTPUT.relative_to(ROOT)}")
    print(f"Wrote {FRONTEND_OUTPUT.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
