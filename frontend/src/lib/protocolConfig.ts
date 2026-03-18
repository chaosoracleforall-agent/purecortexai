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
      "appId": 757290073,
      "address": "AOG3LJR4CGLZY5Y27SJ6MFXS34MABFMTWMUGQJP62LGZAM3JAVBCKM6DXQ",
      "status": "active"
    },
    "cortexToken": {
      "assetId": 757290097,
      "name": "PureCortex",
      "unitName": "CORTEX",
      "creatorAddress": "AOG3LJR4CGLZY5Y27SJ6MFXS34MABFMTWMUGQJP62LGZAM3JAVBCKM6DXQ"
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
  "marketplace": {
    "tradingEnabled": true,
    "launchEnabled": true,
    "maintenanceReason": null,
    "notes": [
      "Marketplace buy and sell flows are enabled on the active testnet factory deployment.",
      "Agent launch remains enabled for controlled validation.",
      "Continue monitoring create, buy, and sell flows against the active factory while testnet usage expands."
    ]
  },
  "nextDeployment": {
    "status": "completed",
    "agentFactoryAppId": 757290073,
    "cortexAssetId": 757290097,
    "creatorAddress": "R7CLPM5L3CQ62PHF347KDIEHKUHIFJYTYVVG6JU6XNT5MFCQOK5V33XMWI",
    "notes": [
      "Patched factory deployed with deferred per-agent config materialization to remove create-time dynamic box key failures.",
      "Core smoke validation passed against this app/asset pair before public trading was re-enabled."
    ]
  },
  "wallets": {
    "agentFactoryEscrow": "AOG3LJR4CGLZY5Y27SJ6MFXS34MABFMTWMUGQJP62LGZAM3JAVBCKM6DXQ",
    "assistanceFund": null,
    "operations": null,
    "creatorVesting": null
  },
  "legacyDeployments": [
    {
      "label": "March 17 R7 redeploy (box reference hotfix iteration)",
      "agentFactoryAppId": 757288371,
      "cortexAssetId": 757288754,
      "status": "deprecated",
      "note": "Superseded by the follow-up deployment that patched create-time dynamic box reference failures."
    },
    {
      "label": "March 17 corrected factory (pre-R7 redeploy)",
      "agentFactoryAppId": 757172168,
      "cortexAssetId": 757172171,
      "status": "deprecated",
      "note": "Retired after deploying a fresh factory bound to the currently available deployer key."
    },
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
