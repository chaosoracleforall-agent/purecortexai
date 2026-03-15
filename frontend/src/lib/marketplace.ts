import { CORTEX_ASSET_ID, FACTORY_APP_ID, calculateCurrentPrice, calculateCurveProgress } from './algorand';

export interface AgentData {
  id: number;
  assetId: number;
  name: string;
  symbol: string;
  price: string;
  mcap: string;
  holders: number;
  change: string;
  curve: number;
  category: string;
  supply: bigint;
}

/**
 * Fetch agent tokens created by the AgentFactory on testnet.
 * Uses the Algorand indexer REST API directly to avoid algosdk type issues.
 */
export async function fetchAgents(): Promise<AgentData[]> {
  const agents: AgentData[] = [];

  try {
    // Query the indexer REST API directly for factory app transactions
    const resp = await fetch(
      `https://testnet-idx.algonode.cloud/v2/transactions?application-id=${FACTORY_APP_ID}&tx-type=appl&limit=50`,
      { headers: { Accept: 'application/json' } },
    );
    if (!resp.ok) throw new Error(`Indexer returned ${resp.status}`);
    const data = await resp.json();

    const assetIds = new Map<number, { id: number; name: string; symbol: string }>();

    for (const txn of data.transactions || []) {
      const innerTxns = txn['inner-txns'] || [];
      for (const inner of innerTxns) {
        if (inner['tx-type'] === 'acfg' && inner['created-asset-index']) {
          const assetId = inner['created-asset-index'];
          const params = inner['asset-config-transaction']?.params || {};
          const name = params.name || 'Unknown Agent';
          const symbol = params['unit-name'] || '???';

          if (
            assetId === CORTEX_ASSET_ID ||
            symbol.toUpperCase() === 'CORTEX' ||
            name.toUpperCase() === 'PURECORTEX'
          ) {
            continue;
          }

          assetIds.set(assetId, {
            id: assetId,
            name,
            symbol,
          });
        }
      }
    }

    // Enrich each agent with holder count
    for (const [index, agent] of Array.from(assetIds.values()).entries()) {
      let holders = 0;
      let supply = 0n;

      try {
        const balResp = await fetch(
          `https://testnet-idx.algonode.cloud/v2/assets/${agent.id}/balances?currency-greater-than=0&limit=100`,
          { headers: { Accept: 'application/json' } },
        );
        if (balResp.ok) {
          const balData = await balResp.json();
          holders = balData.balances?.length || 0;
          for (const bal of balData.balances || []) {
            if (bal.amount > 0) {
              supply += BigInt(bal.amount);
            }
          }
        }
      } catch {
        // Continue with defaults
      }

      const currentPrice = calculateCurrentPrice(supply);
      const curveProgress = calculateCurveProgress(supply);
      const mcapValue = currentPrice * Number(supply) / 1_000_000;

      agents.push({
        id: index + 1,
        assetId: agent.id,
        name: agent.name,
        symbol: agent.symbol,
        price: `${currentPrice.toFixed(2)} ALGO`,
        mcap: formatAlgoValue(mcapValue),
        holders,
        change: '+0.0%',
        curve: Math.round(curveProgress),
        category: 'AI',
        supply,
      });
    }
  } catch (err) {
    console.error('Failed to fetch agents from indexer:', err);
  }

  return agents.sort((left, right) => {
    if (right.holders !== left.holders) {
      return right.holders - left.holders;
    }
    if (right.supply === left.supply) {
      return 0;
    }
    return right.supply > left.supply ? 1 : -1;
  });
}

function formatAlgoValue(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M ALGO`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K ALGO`;
  if (value > 0) return `${value.toFixed(2)} ALGO`;
  return '0 ALGO';
}
