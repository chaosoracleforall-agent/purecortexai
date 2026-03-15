"""
Generated from `deployment.testnet.json` by `generate_protocol_config.py`.
Do not edit by hand.
"""

from __future__ import annotations

from typing import Any, Final


PROTOCOL_CONFIG: Final[dict[str, Any]] = {'name': 'PURECORTEX',
 'environment': 'testnet',
 'network': 'testnet',
 'chainName': 'Algorand Testnet',
 'publicAppUrl': 'https://purecortex.ai',
 'publicApiUrl': 'https://purecortex.ai',
 'publicWsUrl': 'wss://purecortex.ai/ws/chat',
 'repoUrl': 'https://github.com/chaosoracleforall-agent/purecortexai',
 'tgeDate': '2026-03-31T00:00:00Z',
 'contracts': {'agentFactory': {'appId': 757172168,
                                'address': 'RPBTMBSBFALFC4SOTUROMRBBSJGFOEGFFGULZEKPGHHXXFSHCNU247CJAM',
                                'status': 'active'},
               'cortexToken': {'assetId': 757172171,
                               'name': 'PureCortex',
                               'unitName': 'CORTEX',
                               'creatorAddress': 'RPBTMBSBFALFC4SOTUROMRBBSJGFOEGFFGULZEKPGHHXXFSHCNU247CJAM'},
               'governance': {'appId': 757157787, 'status': 'active'},
               'staking': {'appId': 757172306, 'status': 'active'},
               'treasury': {'appId': 757172354, 'status': 'active'}},
 'tokenomics': {'totalSupply': 10000000000000000,
                'decimals': 6,
                'basePrice': 10000,
                'slope': 1000,
                'creationFee': 100000000,
                'buyFeeBps': 100,
                'sellFeeBps': 200,
                'graduationThreshold': 50000000000},
 'wallets': {'agentFactoryEscrow': 'RPBTMBSBFALFC4SOTUROMRBBSJGFOEGFFGULZEKPGHHXXFSHCNU247CJAM',
             'assistanceFund': None,
             'operations': None,
             'creatorVesting': None},
 'legacyDeployments': [{'label': 'March 13 launchpad deployment',
                        'agentFactoryAppId': 757089323,
                        'cortexAssetId': 757092088,
                        'status': 'deprecated',
                        'note': 'Retained for auditability only. Do not target '
                                'this deployment from active clients.'}]}

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
