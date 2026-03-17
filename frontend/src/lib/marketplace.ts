import { apiUrl } from './api';
import {
  CORTEX_ASSET_ID,
  FACTORY_APP_ID,
  calculateCurrentPrice,
  calculateCurveProgress,
  type CurveParams,
} from './algorand';

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
  config: CurveParams;
}

export interface MarketplaceConfig {
  trading_enabled: boolean;
  launch_enabled: boolean;
  maintenance_reason: string | null;
  active_factory_app_id: number;
  deprecated_factory_app_id: number;
  legacy_factory_app_ids: number[];
  cortex_asset_id: number;
  creation_fee: number;
  buy_fee_bps: number;
  sell_fee_bps: number;
  graduation_threshold: number;
  base_price: number;
  slope: number;
  next_deployment: Record<string, unknown>;
  notes: string[];
}

export interface QuotePreview {
  asset_id: number;
  amount: number;
  current_supply: number;
  config: {
    base_price: number;
    slope: number;
    buy_fee_bps: number;
    sell_fee_bps: number;
    graduation_threshold: number;
  };
  gross: number;
  fee: number;
  net: number;
}

function encodeFactorySupplyBoxName(assetId: number): string {
  const prefix = new TextEncoder().encode('s');
  const key = new Uint8Array(8);
  const view = new DataView(key.buffer);
  view.setBigUint64(0, BigInt(assetId));
  const bytes = new Uint8Array(prefix.length + key.length);
  bytes.set(prefix, 0);
  bytes.set(key, prefix.length);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

async function fetchAgentSupply(assetId: number): Promise<bigint> {
  const boxName = encodeFactorySupplyBoxName(assetId);
  const resp = await fetch(
    `https://testnet-api.algonode.cloud/v2/applications/${FACTORY_APP_ID}/box?name=b64:${encodeURIComponent(boxName)}`,
    { headers: { Accept: 'application/json' } },
  );
  if (!resp.ok) {
    return 0n;
  }
  const data = await resp.json();
  const raw = atob(data.value || '');
  if (!raw) {
    return 0n;
  }
  const bytes = Uint8Array.from(raw, (char) => char.charCodeAt(0));
  if (bytes.length !== 8) {
    return 0n;
  }
  return new DataView(bytes.buffer).getBigUint64(0);
}

function encodeFactoryConfigBoxName(assetId: number): string {
  const prefix = new TextEncoder().encode('c');
  const key = new Uint8Array(8);
  const view = new DataView(key.buffer);
  view.setBigUint64(0, BigInt(assetId));
  const bytes = new Uint8Array(prefix.length + key.length);
  bytes.set(prefix, 0);
  bytes.set(key, prefix.length);
  let binary = '';
  for (const byte of bytes) {
    binary += String.fromCharCode(byte);
  }
  return btoa(binary);
}

async function fetchAgentConfig(assetId: number): Promise<CurveParams | null> {
  const boxName = encodeFactoryConfigBoxName(assetId);
  const resp = await fetch(
    `https://testnet-api.algonode.cloud/v2/applications/${FACTORY_APP_ID}/box?name=b64:${encodeURIComponent(boxName)}`,
    { headers: { Accept: 'application/json' } },
  );
  if (!resp.ok) {
    return null;
  }
  const data = await resp.json();
  const raw = atob(data.value || '');
  if (!raw) {
    return null;
  }
  const bytes = Uint8Array.from(raw, (char) => char.charCodeAt(0));
  if (bytes.length !== 40) {
    return null;
  }
  const view = new DataView(bytes.buffer);
  return {
    basePrice: view.getBigUint64(0),
    slope: view.getBigUint64(8),
    buyFeeBps: view.getBigUint64(16),
    sellFeeBps: view.getBigUint64(24),
    graduationThreshold: view.getBigUint64(32),
  };
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

    // Enrich each agent with holder count and live curve supply/config from box state
    for (const [index, agent] of Array.from(assetIds.values()).entries()) {
      let holders = 0;
      let supply = 0n;
      let config: CurveParams | null = null;

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

      [supply, config] = await Promise.all([
        fetchAgentSupply(agent.id).catch(() => 0n),
        fetchAgentConfig(agent.id).catch(() => null),
      ]);

      if (!config) {
        continue;
      }

      const currentPrice = calculateCurrentPrice(supply, config);
      const curveProgress = calculateCurveProgress(supply, config);
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
        config,
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

export async function fetchMarketplaceConfig(): Promise<MarketplaceConfig> {
  const resp = await fetch(apiUrl('/api/marketplace/config'), {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) throw new Error(`Marketplace config returned ${resp.status}`);
  return resp.json();
}

export async function fetchBuyQuotePreview(assetId: number, amount: bigint): Promise<QuotePreview> {
  const params = new URLSearchParams({
    asset_id: String(assetId),
    amount: String(amount),
  });
  const resp = await fetch(apiUrl(`/api/marketplace/quote/buy?${params.toString()}`), {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) throw new Error(`Buy quote returned ${resp.status}`);
  return resp.json();
}

export async function fetchSellQuotePreview(assetId: number, amount: bigint): Promise<QuotePreview> {
  const params = new URLSearchParams({
    asset_id: String(assetId),
    amount: String(amount),
  });
  const resp = await fetch(apiUrl(`/api/marketplace/quote/sell?${params.toString()}`), {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) throw new Error(`Sell quote returned ${resp.status}`);
  return resp.json();
}

function formatAlgoValue(value: number): string {
  if (value >= 1_000_000) return `${(value / 1_000_000).toFixed(1)}M ALGO`;
  if (value >= 1_000) return `${(value / 1_000).toFixed(1)}K ALGO`;
  if (value > 0) return `${value.toFixed(2)} ALGO`;
  return '0 ALGO';
}
