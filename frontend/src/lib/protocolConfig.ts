// Generated from `deployment.testnet.json` by `generate_protocol_config.py`.
// Do not edit by hand.

export const protocolConfig = {
  "name": "PURECORTEX",
  "environment": "testnet",
  "network": "testnet",
  "chainName": "Algorand Testnet",
  "publicAppUrl": "https://purecortex.ai",
  "publicApiUrl": "https://purecortex.ai",
  "publicWsUrl": "wss://purecortex.ai/ws/chat",
  "repoUrl": "https://github.com/chaosoracleforall-agent/purecortexai",
  "tgeDate": "2026-03-31T00:00:00Z",
  "contracts": {
    "agentFactory": {
      "appId": 757172168,
      "address": "RPBTMBSBFALFC4SOTUROMRBBSJGFOEGFFGULZEKPGHHXXFSHCNU247CJAM",
      "status": "active"
    },
    "cortexToken": {
      "assetId": 757172171,
      "name": "PureCortex",
      "unitName": "CORTEX",
      "creatorAddress": "RPBTMBSBFALFC4SOTUROMRBBSJGFOEGFFGULZEKPGHHXXFSHCNU247CJAM"
    },
    "governance": {
      "appId": 757157787,
      "status": "active"
    },
    "staking": {
      "appId": 757172306,
      "status": "active"
    },
    "treasury": {
      "appId": 757172354,
      "status": "active"
    }
  },
  "tokenomics": {
    "totalSupply": 10000000000000000,
    "decimals": 6,
    "basePrice": 10000,
    "slope": 1000,
    "creationFee": 100000000,
    "buyFeeBps": 100,
    "sellFeeBps": 200,
    "graduationThreshold": 50000000000
  },
  "wallets": {
    "agentFactoryEscrow": "RPBTMBSBFALFC4SOTUROMRBBSJGFOEGFFGULZEKPGHHXXFSHCNU247CJAM",
    "assistanceFund": null,
    "operations": null,
    "creatorVesting": null
  },
  "legacyDeployments": [
    {
      "label": "March 13 launchpad deployment",
      "agentFactoryAppId": 757089323,
      "cortexAssetId": 757092088,
      "status": "deprecated",
      "note": "Retained for auditability only. Do not target this deployment from active clients."
    }
  ]
} as const;

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
