import algosdk from 'algosdk';
import {
  BASE_PRICE as BASE_PRICE_MICROALGO,
  BUY_FEE_BPS,
  CORTEX_ASSET_ID,
  CREATION_FEE as CREATION_FEE_MICRO_CORTEX,
  FACTORY_ADDRESS,
  FACTORY_APP_ID,
  GOVERNANCE_APP_ID,
  GRADUATION_THRESHOLD,
  SELL_FEE_BPS,
  SLOPE as SLOPE_MICROALGO,
  STAKING_APP_ID,
  TREASURY_APP_ID,
} from './protocolConfig';

export {
  CORTEX_ASSET_ID,
  FACTORY_ADDRESS,
  FACTORY_APP_ID,
  GOVERNANCE_APP_ID,
  BUY_FEE_BPS,
  SELL_FEE_BPS,
  STAKING_APP_ID,
  TREASURY_APP_ID,
};

// Bonding curve parameters (from on-chain global state)
export const BASE_PRICE = BigInt(BASE_PRICE_MICROALGO); // micro-ALGO per token unit
export const SLOPE = BigInt(SLOPE_MICROALGO);
export const TOKEN_SCALE = 10n ** BigInt(6);
export const GOVERNANCE_ADDRESS = 'I36JTAQYRFSIRH7G3OTCQ7ZOUA7ARZ7YYZR4SV57QF5UU5P75VT55D2MO4';
export const CREATION_FEE = CREATION_FEE_MICRO_CORTEX; // 100 CORTEX (6 decimals)

// Testnet endpoints (algonode.cloud supports browser CORS)
export const ALGOD_URL = 'https://testnet-api.algonode.cloud';
const INDEXER_URL = 'https://testnet-idx.algonode.cloud';

export function getAlgodClient(): algosdk.Algodv2 {
  return new algosdk.Algodv2('', ALGOD_URL, '');
}

export function getIndexerClient(): algosdk.Indexer {
  return new algosdk.Indexer('', INDEXER_URL, '');
}

/**
 * Calculate bonding curve buy price (matching the contract formula).
 * Price = amount * BASE_PRICE + SLOPE * (2 * currentSupply * amount + amount^2) / 2
 */
export interface CurveParams {
  basePrice: bigint;
  slope: bigint;
  buyFeeBps: bigint;
  sellFeeBps: bigint;
  graduationThreshold: bigint;
}

export const DEFAULT_CURVE_PARAMS: CurveParams = {
  basePrice: BASE_PRICE,
  slope: SLOPE,
  buyFeeBps: BigInt(BUY_FEE_BPS),
  sellFeeBps: BigInt(SELL_FEE_BPS),
  graduationThreshold: BigInt(GRADUATION_THRESHOLD),
};

export function calculateBuyPrice(
  currentSupply: bigint,
  amount: bigint,
  params: CurveParams = DEFAULT_CURVE_PARAMS,
): bigint {
  const baseCost = (amount * params.basePrice) / TOKEN_SCALE;
  const twoSupplyAmount = 2n * currentSupply * amount;
  const amountSq = amount * amount;
  const areaDoubled = twoSupplyAmount + amountSq;
  const slopeCost = (params.slope * areaDoubled) / (2n * TOKEN_SCALE * TOKEN_SCALE);
  return baseCost + slopeCost;
}

/**
 * Calculate the current price per token (for 1 full token = 1_000_000 micro-units)
 */
export function calculateCurrentPrice(currentSupply: bigint, params: CurveParams = DEFAULT_CURVE_PARAMS): number {
  const oneToken = 1_000_000n;
  const priceInMicroAlgo = calculateBuyPrice(currentSupply, oneToken, params);
  return Number(priceInMicroAlgo) / 1_000_000; // Convert to ALGO
}

/**
 * Calculate curve progress as percentage toward graduation threshold.
 * Graduation = 50,000 CORTEX worth of ALGO locked.
 */
export function calculateCurveProgress(currentSupply: bigint, params: CurveParams = DEFAULT_CURVE_PARAMS): number {
  if (currentSupply === 0n) return 0;
  const baseCost = (currentSupply * params.basePrice) / TOKEN_SCALE;
  const currentSq = currentSupply * currentSupply;
  const slopeCost = (params.slope * currentSq) / (2n * TOKEN_SCALE * TOKEN_SCALE);
  const totalValue = baseCost + slopeCost;
  const pct = Number((totalValue * 100n) / params.graduationThreshold);
  return Math.min(pct, 100);
}

/**
 * Calculate the gross ALGO returned before sell fees.
 */
export function calculateSellPrice(
  currentSupply: bigint,
  amount: bigint,
  params: CurveParams = DEFAULT_CURVE_PARAMS,
): bigint {
  if (amount <= 0n || currentSupply < amount) {
    return 0n;
  }

  const newSupply = currentSupply - amount;
  const baseReturn = (amount * params.basePrice) / TOKEN_SCALE;
  const currentSq = currentSupply * currentSupply;
  const newSq = newSupply * newSupply;
  const slopeReturn = (params.slope * (currentSq - newSq)) / (2n * TOKEN_SCALE * TOKEN_SCALE);
  return baseReturn + slopeReturn;
}

/**
 * Calculate the net ALGO returned after the protocol sell fee.
 */
export function calculateNetSellReturn(
  currentSupply: bigint,
  amount: bigint,
  params: CurveParams = DEFAULT_CURVE_PARAMS,
): bigint {
  const gross = calculateSellPrice(currentSupply, amount, params);
  const fee = (gross * params.sellFeeBps) / 10_000n;
  return gross - fee;
}

// ------------------------------------------------------------------ //
//  On-chain governance reads
// ------------------------------------------------------------------ //

export interface OnChainProposal {
  id: number;
  proposer: string;
  createdRound: number;
  type: number;
  typeName: string;
  yesVotes: number;
  noVotes: number;
  status: number;
  statusName: string;
  totalVoters: number;
}

const STATUS_NAMES: Record<number, string> = {
  0: 'Discussion',
  1: 'Voting',
  2: 'Passed',
  3: 'Rejected',
  4: 'Executed',
  5: 'Cancelled',
};

const TYPE_NAMES: Record<number, string> = {
  0: 'Parameter Change',
  1: 'Treasury Action',
  2: 'Protocol Upgrade',
  3: 'Emergency Action',
};

/** Read proposal_count from governance contract global state. */
export async function getProposalCount(): Promise<number> {
  const resp = await fetch(`${ALGOD_URL}/v2/applications/${GOVERNANCE_APP_ID}`, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) return 0;
  const data = await resp.json();
  const globals = data.params?.['global-state'] || [];
  for (const kv of globals) {
    const key = atob(kv.key);
    if (key === 'proposal_count') return kv.value.uint || 0;
  }
  return 0;
}

/** Read a single proposal from on-chain box storage. */
export async function getProposal(proposalId: number): Promise<OnChainProposal | null> {
  // Box key = uint64 big-endian (8 bytes), no prefix (key_prefix=b"")
  const keyBytes = new Uint8Array(8);
  new DataView(keyBytes.buffer).setBigUint64(0, BigInt(proposalId));
  const b64Key = btoa(String.fromCharCode(...keyBytes));

  const resp = await fetch(
    `${ALGOD_URL}/v2/applications/${GOVERNANCE_APP_ID}/box?name=b64:${encodeURIComponent(b64Key)}`,
    { headers: { Accept: 'application/json' } },
  );
  if (!resp.ok) return null;

  const data = await resp.json();
  const raw = Uint8Array.from(atob(data.value), (c) => c.charCodeAt(0));
  if (raw.length !== 80) return null;

  const view = new DataView(raw.buffer);
  const proposerBytes = raw.slice(0, 32);
  const proposer = algosdk.encodeAddress(proposerBytes);
  const createdRound = Number(view.getBigUint64(32));
  const type = Number(view.getBigUint64(40));
  const yesVotes = Number(view.getBigUint64(48));
  const noVotes = Number(view.getBigUint64(56));
  const status = Number(view.getBigUint64(64));
  const totalVoters = Number(view.getBigUint64(72));

  return {
    id: proposalId,
    proposer,
    createdRound,
    type,
    typeName: TYPE_NAMES[type] || 'Unknown',
    yesVotes,
    noVotes,
    status,
    statusName: STATUS_NAMES[status] || 'Unknown',
    totalVoters,
  };
}

/** Fetch all proposals from on-chain. */
export async function getAllProposals(): Promise<OnChainProposal[]> {
  const count = await getProposalCount();
  if (count === 0) return [];

  const proposals: OnChainProposal[] = [];
  const fetches = [];
  for (let i = 1; i <= count; i++) {
    fetches.push(getProposal(i));
  }
  const results = await Promise.all(fetches);
  for (const p of results) {
    if (p) proposals.push(p);
  }
  return proposals.sort((a, b) => b.id - a.id); // newest first
}
