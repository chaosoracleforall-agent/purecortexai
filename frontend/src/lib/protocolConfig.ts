// Generated from `deployment.mainnet.json` by `generate_protocol_config.py`.
// Do not edit by hand.

export const protocolConfig = {
  "name": "PURECORTEX",
  "environment": "mainnet",
  "network": "mainnet",
  "chainName": "Algorand MainNet",
  "publicAppUrl": "https://purecortex.ai",
  "publicApiUrl": "https://purecortex.ai",
  "publicWsUrl": "wss://purecortex.ai/ws/chat",
  "repoUrl": "https://github.com/chaosoracleforall-agent/purecortexai",
  "tgeDate": "2026-03-31T00:00:00Z",
  "contracts": {
    "agentFactory": {
      "appId": 3493064595,
      "address": "34SJEEP5EXNVAUHDC73IXM64VPLA2ISNEHDFRPEZWQJMPHRUL3CHCXF3MU",
      "status": "active"
    },
    "cortexToken": {
      "assetId": 3493064714,
      "name": "PureCortex",
      "unitName": "CORTEX",
      "creatorAddress": "34SJEEP5EXNVAUHDC73IXM64VPLA2ISNEHDFRPEZWQJMPHRUL3CHCXF3MU"
    },
    "governance": {
      "appId": 3493064034,
      "status": "active"
    },
    "staking": {
      "appId": 3493064261,
      "status": "active"
    },
    "treasury": {
      "appId": 3493064463,
      "status": "active"
    },
    "creatorVesting": {
      "appId": 3493064628,
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
  "allocation": {
    "creator": {
      "percentage": 10,
      "amount": 1000000000000000,
      "vestingTgePct": 10,
      "vestingDays": 180,
      "wallet": ""
    },
    "genesisDistribution": {
      "percentage": 31,
      "amount": 3100000000000000,
      "wallet": ""
    },
    "futureEmissions": {
      "percentage": 24,
      "amount": 2400000000000000,
      "halvingSchedule": [
        0.4,
        0.3,
        0.2,
        0.1
      ],
      "wallet": ""
    },
    "liquidity": {
      "percentage": 15,
      "amount": 1500000000000000,
      "lockYears": 10,
      "wallet": ""
    },
    "agentIncentives": {
      "percentage": 15,
      "amount": 1500000000000000,
      "wallet": ""
    },
    "assistanceFund": {
      "percentage": 5,
      "amount": 500000000000000,
      "wallet": ""
    }
  },
  "marketplace": {
    "tradingEnabled": false,
    "launchEnabled": false,
    "maintenanceReason": "Pre-launch: mainnet contracts pending deployment",
    "notes": [
      "Trading and launch are disabled until mainnet contracts are deployed and smoke-tested.",
      "Enable after deployment validation completes and liquidity pools are seeded."
    ]
  },
  "wallets": {
    "agentFactoryEscrow": "34SJEEP5EXNVAUHDC73IXM64VPLA2ISNEHDFRPEZWQJMPHRUL3CHCXF3MU",
    "assistanceFund": null,
    "operations": null,
    "creatorVesting": null,
    "liquidityPool": null
  },
  "dex": {
    "tinyman": {
      "poolId": null,
      "pair": "CORTEX/ALGO",
      "status": "pending"
    },
    "pact": {
      "poolId": null,
      "pair": "CORTEX/ALGO",
      "status": "pending"
    }
  },
  "airdrop": {
    "snapshotBlock": null,
    "merkleRoot": null,
    "distributionContract": null,
    "claimDeadline": "2026-07-01T00:00:00Z",
    "tiers": {
      "testnetPioneers": {
        "allocationPct": 5,
        "minWalletAge": null
      },
      "algorandDefiUsers": {
        "allocationPct": 30,
        "snapshotProtocols": [
          "tinyman",
          "pact",
          "folks_finance"
        ]
      },
      "nfdHolders": {
        "allocationPct": 10
      },
      "algorandGovernors": {
        "allocationPct": 20
      },
      "developerBuilders": {
        "allocationPct": 10
      },
      "socialCampaign": {
        "allocationPct": 15
      },
      "communityTasks": {
        "allocationPct": 10
      }
    }
  },
  "legacyDeployments": []
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
