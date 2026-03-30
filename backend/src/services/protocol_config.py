"""
Generated from `deployment.mainnet.json` by `generate_protocol_config.py`.
Do not edit by hand.
"""

from __future__ import annotations

from typing import Any, Final


PROTOCOL_CONFIG: Final[dict[str, Any]] = {'name': 'PURECORTEX',
 'environment': 'mainnet',
 'network': 'mainnet',
 'chainName': 'Algorand MainNet',
 'publicAppUrl': 'https://purecortex.ai',
 'publicApiUrl': 'https://purecortex.ai',
 'publicWsUrl': 'wss://purecortex.ai/ws/chat',
 'repoUrl': 'https://github.com/chaosoracleforall-agent/purecortexai',
 'tgeDate': '2026-03-31T00:00:00Z',
 'contracts': {'agentFactory': {'appId': 3493064595,
                                'address': '34SJEEP5EXNVAUHDC73IXM64VPLA2ISNEHDFRPEZWQJMPHRUL3CHCXF3MU',
                                'status': 'active'},
               'cortexToken': {'assetId': 3493064714,
                               'name': 'PureCortex',
                               'unitName': 'CORTEX',
                               'creatorAddress': '34SJEEP5EXNVAUHDC73IXM64VPLA2ISNEHDFRPEZWQJMPHRUL3CHCXF3MU'},
               'governance': {'appId': 3493064034, 'status': 'active'},
               'staking': {'appId': 3493064261, 'status': 'active'},
               'treasury': {'appId': 3493064463, 'status': 'active'},
               'creatorVesting': {'appId': 3493064628, 'status': 'active'}},
 'tokenomics': {'totalSupply': 10000000000000000,
                'decimals': 6,
                'basePrice': 10000,
                'slope': 1000,
                'creationFee': 100000000,
                'buyFeeBps': 100,
                'sellFeeBps': 200,
                'graduationThreshold': 50000000000},
 'allocation': {'creator': {'percentage': 10,
                            'amount': 1000000000000000,
                            'vestingTgePct': 10,
                            'vestingDays': 180,
                            'wallet': ''},
                'genesisDistribution': {'percentage': 31,
                                        'amount': 3100000000000000,
                                        'wallet': ''},
                'futureEmissions': {'percentage': 24,
                                    'amount': 2400000000000000,
                                    'halvingSchedule': [0.4, 0.3, 0.2, 0.1],
                                    'wallet': ''},
                'liquidity': {'percentage': 15,
                              'amount': 1500000000000000,
                              'lockYears': 10,
                              'wallet': ''},
                'agentIncentives': {'percentage': 15,
                                    'amount': 1500000000000000,
                                    'wallet': ''},
                'assistanceFund': {'percentage': 5,
                                   'amount': 500000000000000,
                                   'wallet': ''}},
 'marketplace': {'tradingEnabled': False,
                 'launchEnabled': False,
                 'maintenanceReason': 'Pre-launch: mainnet contracts pending '
                                      'deployment',
                 'notes': ['Trading and launch are disabled until mainnet '
                           'contracts are deployed and smoke-tested.',
                           'Enable after deployment validation completes and '
                           'liquidity pools are seeded.']},
 'wallets': {'agentFactoryEscrow': '34SJEEP5EXNVAUHDC73IXM64VPLA2ISNEHDFRPEZWQJMPHRUL3CHCXF3MU',
             'assistanceFund': None,
             'operations': None,
             'creatorVesting': None,
             'liquidityPool': None},
 'dex': {'tinyman': {'poolId': None,
                     'pair': 'CORTEX/ALGO',
                     'status': 'pending'},
         'pact': {'poolId': None, 'pair': 'CORTEX/ALGO', 'status': 'pending'}},
 'airdrop': {'snapshotBlock': None,
             'merkleRoot': None,
             'distributionContract': None,
             'claimDeadline': '2026-07-01T00:00:00Z',
             'tiers': {'testnetPioneers': {'allocationPct': 5,
                                           'minWalletAge': None},
                       'algorandDefiUsers': {'allocationPct': 30,
                                             'snapshotProtocols': ['tinyman',
                                                                   'pact',
                                                                   'folks_finance']},
                       'nfdHolders': {'allocationPct': 10},
                       'algorandGovernors': {'allocationPct': 20},
                       'developerBuilders': {'allocationPct': 10},
                       'socialCampaign': {'allocationPct': 15},
                       'communityTasks': {'allocationPct': 10}}},
 'legacyDeployments': []}

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
