import algosdk from 'algosdk';
import {
  BUY_FEE_BPS,
  FACTORY_APP_ID,
  FACTORY_ADDRESS,
  CORTEX_ASSET_ID,
  CREATION_FEE,
  ALGOD_URL,
  calculateBuyPrice,
} from './algorand';

/**
 * Fetch suggested params directly via fetch() to avoid algosdk bundling issues in the browser.
 */
async function fetchSuggestedParams(): Promise<algosdk.SuggestedParams> {
  const resp = await fetch(`${ALGOD_URL}/v2/transactions/params`, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) throw new Error(`Algod returned ${resp.status}`);
  const data = await resp.json();

  return {
    flatFee: false,
    fee: BigInt(data['fee']),
    firstValid: BigInt(data['last-round']),
    lastValid: BigInt(data['last-round']) + 1000n,
    genesisID: data['genesis-id'],
    genesisHash: algosdk.base64ToBytes(data['genesis-hash']),
    minFee: BigInt(data['min-fee']),
  };
}

export async function accountHasAssetOptIn(address: string, assetId: number): Promise<boolean> {
  const resp = await fetch(`${ALGOD_URL}/v2/accounts/${address}`, {
    headers: { Accept: 'application/json' },
  });
  if (!resp.ok) {
    throw new Error(`Unable to load account state (${resp.status})`);
  }

  const data = await resp.json();
  return (data.assets || []).some((asset: { 'asset-id': number }) => asset['asset-id'] === assetId);
}

export async function buildAssetOptInTxn(
  sender: string,
  assetId: number,
): Promise<algosdk.Transaction> {
  const params = await fetchSuggestedParams();
  return algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
    sender,
    receiver: sender,
    assetIndex: assetId,
    amount: 0,
    suggestedParams: params,
  });
}

export async function submitSignedTransactions(signedTxns: Uint8Array[]): Promise<string> {
  const combined = new Uint8Array(signedTxns.reduce((sum, txn) => sum + txn.length, 0));
  let offset = 0;
  for (const txn of signedTxns) {
    combined.set(txn, offset);
    offset += txn.length;
  }

  const submitResp = await fetch(`${ALGOD_URL}/v2/transactions`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-binary' },
    body: combined,
  });
  if (!submitResp.ok) {
    const errBody = await submitResp.json().catch(() => ({}));
    throw new Error(errBody.message || `Submit failed: ${submitResp.status}`);
  }

  const body = await submitResp.json();
  const txid = body.txId || body.txid;
  if (!txid) {
    throw new Error('Transaction submitted but no txid was returned');
  }
  return txid;
}

export async function waitForConfirmation(txid: string, maxAttempts = 10, pollMs = 2000): Promise<boolean> {
  for (let attempt = 0; attempt < maxAttempts; attempt++) {
    await new Promise((resolve) => setTimeout(resolve, pollMs));
    const statusResp = await fetch(`${ALGOD_URL}/v2/transactions/pending/${txid}`);
    if (!statusResp.ok) {
      continue;
    }

    const status = await statusResp.json();
    if (status['confirmed-round'] && status['confirmed-round'] > 0) {
      return true;
    }
  }

  return false;
}

// ABI method selectors from the ARC56 spec
const ABI_CREATE_AGENT = new algosdk.ABIMethod({
  name: 'create_agent',
  args: [
    { type: 'axfer', name: 'cortex_payment' },
    { type: 'string', name: 'name' },
    { type: 'string', name: 'unit_name' },
  ],
  returns: { type: 'uint64' },
});

const ABI_BUY_TOKENS = new algosdk.ABIMethod({
  name: 'buy_tokens',
  args: [
    { type: 'pay', name: 'payment' },
    { type: 'uint64', name: 'asset' },
    { type: 'uint64', name: 'amount' },
  ],
  returns: { type: 'void' },
});

/**
 * Build an atomic transaction group for creating a new agent.
 * Group: [CORTEX asset transfer → create_agent app call]
 */
export async function buildCreateAgentTxns(
  sender: string,
  name: string,
  symbol: string,
): Promise<algosdk.Transaction[]> {
  const params = await fetchSuggestedParams();

  const composer = new algosdk.AtomicTransactionComposer();

  // 1. CORTEX asset transfer (fee payment)
  const cortexTransfer = algosdk.makeAssetTransferTxnWithSuggestedParamsFromObject({
    sender,
    receiver: FACTORY_ADDRESS,
    assetIndex: CORTEX_ASSET_ID,
    amount: CREATION_FEE,
    suggestedParams: params,
  });

  // 2. App call to create_agent
  composer.addMethodCall({
    appID: FACTORY_APP_ID,
    method: ABI_CREATE_AGENT,
    methodArgs: [
      { txn: cortexTransfer, signer: algosdk.makeEmptyTransactionSigner() },
      name,
      symbol,
    ],
    sender,
    suggestedParams: params,
    signer: algosdk.makeEmptyTransactionSigner(),
  });

  const group = composer.buildGroup();
  return group.map((g) => g.txn);
}

/**
 * Build an atomic transaction group for buying agent tokens.
 * Group: [ALGO payment → buy_tokens app call]
 */
export async function buildBuyTokensTxns(
  sender: string,
  assetId: number,
  amount: bigint,
  currentSupply: bigint,
): Promise<algosdk.Transaction[]> {
  const params = await fetchSuggestedParams();

  // Calculate required ALGO (add 1% fee on top)
  const rawPrice = calculateBuyPrice(currentSupply, amount);
  const fee = (rawPrice * BigInt(BUY_FEE_BPS)) / 10_000n;
  const totalAlgo = rawPrice + fee;

  if (totalAlgo > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new Error('Transaction amount exceeds safe precision limit');
  }

  const composer = new algosdk.AtomicTransactionComposer();

  // 1. ALGO payment to factory
  const payment = algosdk.makePaymentTxnWithSuggestedParamsFromObject({
    sender,
    receiver: FACTORY_ADDRESS,
    amount: Number(totalAlgo),
    suggestedParams: params,
  });

  // 2. App call to buy_tokens
  composer.addMethodCall({
    appID: FACTORY_APP_ID,
    method: ABI_BUY_TOKENS,
    methodArgs: [
      { txn: payment, signer: algosdk.makeEmptyTransactionSigner() },
      assetId,
      Number(amount),
    ],
    sender,
    suggestedParams: params,
    signer: algosdk.makeEmptyTransactionSigner(),
    boxes: [
      { appIndex: FACTORY_APP_ID, name: algosdk.bigIntToBytes(assetId, 8) },
    ],
  });

  const group = composer.buildGroup();
  return group.map((g) => g.txn);
}
