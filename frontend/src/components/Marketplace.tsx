'use client';

import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Zap, Search, ArrowUpRight, BarChart3, Plus, X, Loader2, AlertCircle, RefreshCw, ShoppingCart, Coins, ExternalLink } from 'lucide-react';
import { useWallet } from '@txnlab/use-wallet-react';
import { useMarketplace } from '@/hooks/useMarketplace';
import WalletButton from '@/components/WalletButton';
import {
  accountHasAssetOptIn,
  buildAssetOptInTxn,
  buildBuyTokensTxns,
  buildCreateAgentTxns,
  buildSellTokensTxns,
  getAccountAssetBalance,
  submitSignedTransactions,
  waitForConfirmation,
} from '@/lib/transactions';
import { BUY_FEE_BPS, calculateBuyPrice, calculateNetSellReturn, calculateSellPrice } from '@/lib/algorand';
import type { AgentData } from '@/lib/marketplace';

const MAX_MARKET_TRADE_AMOUNT = 100_000_000_000n;

function parseTokenAmountToMicroUnits(value: string): bigint | null {
  const trimmed = value.trim();
  if (!trimmed || !/^\d+(\.\d{0,6})?$/.test(trimmed)) {
    return null;
  }

  const [whole = '0', fractional = ''] = trimmed.split('.');
  return (BigInt(whole) * 1_000_000n) + BigInt((fractional + '000000').slice(0, 6));
}

function formatFixedUnits(value: bigint, decimals = 6): string {
  const divisor = 10n ** BigInt(decimals);
  const whole = value / divisor;
  const fraction = (value % divisor).toString().padStart(decimals, '0').replace(/0+$/, '');
  return fraction ? `${whole.toString()}.${fraction}` : whole.toString();
}

function formatAlgoAmount(value: bigint): string {
  return `${formatFixedUnits(value, 6)} ALGO`;
}

function calculateBuyQuote(currentSupply: bigint, amount: bigint) {
  const baseCost = calculateBuyPrice(currentSupply, amount);
  const fee = (baseCost * BigInt(BUY_FEE_BPS)) / 10_000n;
  return {
    baseCost,
    fee,
    totalCost: baseCost + fee,
  };
}

function calculateSellQuote(currentSupply: bigint, amount: bigint) {
  const grossReturn = calculateSellPrice(currentSupply, amount);
  const netReturn = calculateNetSellReturn(currentSupply, amount);
  return {
    grossReturn,
    fee: grossReturn - netReturn,
    netReturn,
  };
}

export default function Marketplace() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [selectedAgent, setSelectedAgent] = useState<AgentData | null>(null);
  const [agentName, setAgentName] = useState('');
  const [agentSymbol, setAgentSymbol] = useState('');
  const [deploying, setDeploying] = useState(false);
  const [deployError, setDeployError] = useState<string | null>(null);
  const [deploySuccess, setDeploySuccess] = useState<string | null>(null);
  const [buyAmount, setBuyAmount] = useState('1');
  const [buying, setBuying] = useState(false);
  const [buyError, setBuyError] = useState<string | null>(null);
  const [buySuccess, setBuySuccess] = useState<string | null>(null);
  const [sellAmount, setSellAmount] = useState('1');
  const [selling, setSelling] = useState(false);
  const [sellError, setSellError] = useState<string | null>(null);
  const [sellSuccess, setSellSuccess] = useState<string | null>(null);
  const [walletBalance, setWalletBalance] = useState<bigint | null>(null);
  const [loadingWalletBalance, setLoadingWalletBalance] = useState(false);

  const { agents, loading, error, refresh } = useMarketplace();
  const { activeAccount, activeWallet, transactionSigner } = useWallet();

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key !== 'Escape') return;
    if (selectedAgent) {
      setSelectedAgent(null);
      return;
    }
    if (isModalOpen) {
      setIsModalOpen(false);
    }
  }, [isModalOpen, selectedAgent]);

  useEffect(() => {
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [handleEscape]);

  const categories = ['All', ...new Set(agents.map(a => a.category))];

  const filteredAgents = agents.filter(a =>
    (a.name.toLowerCase().includes(search.toLowerCase()) || a.symbol.toLowerCase().includes(search.toLowerCase())) &&
    (filter === 'All' || a.category === filter)
  );

  const liveSelectedAgent = selectedAgent
    ? agents.find((agent) => agent.assetId === selectedAgent.assetId) ?? selectedAgent
    : null;
  const parsedBuyAmount = parseTokenAmountToMicroUnits(buyAmount);
  const buyQuote = liveSelectedAgent && parsedBuyAmount && parsedBuyAmount > 0n
    ? calculateBuyQuote(liveSelectedAgent.supply, parsedBuyAmount)
    : null;
  const parsedSellAmount = parseTokenAmountToMicroUnits(sellAmount);
  const sellQuote = liveSelectedAgent && parsedSellAmount && parsedSellAmount > 0n && parsedSellAmount <= liveSelectedAgent.supply
    ? calculateSellQuote(liveSelectedAgent.supply, parsedSellAmount)
    : null;

  function openAgent(agent: AgentData) {
    setSelectedAgent(agent);
    setWalletBalance(null);
    setLoadingWalletBalance(Boolean(activeAccount?.address));
    setBuyAmount('1');
    setSellAmount('1');
    setBuyError(null);
    setBuySuccess(null);
    setSellError(null);
    setSellSuccess(null);
    void refresh();
  }

  useEffect(() => {
    if (!liveSelectedAgent?.assetId || !activeAccount?.address) {
      setWalletBalance(null);
      setLoadingWalletBalance(false);
      return;
    }

    let cancelled = false;
    setWalletBalance(null);
    setLoadingWalletBalance(true);
    getAccountAssetBalance(activeAccount.address, liveSelectedAgent.assetId)
      .then((balance) => {
        if (!cancelled) {
          setWalletBalance(balance);
        }
      })
      .catch(() => {
        if (!cancelled) {
          setWalletBalance(0n);
        }
      })
      .finally(() => {
        if (!cancelled) {
          setLoadingWalletBalance(false);
        }
      });

    return () => {
      cancelled = true;
    };
  }, [activeAccount?.address, liveSelectedAgent?.assetId]);

  async function handleDeploy() {
    if (!activeAccount || !transactionSigner || !activeWallet) {
      setDeployError('Connect your wallet first');
      return;
    }
    if (!agentName.trim() || !agentSymbol.trim()) {
      setDeployError('Name and symbol are required');
      return;
    }
    if (agentSymbol.length > 8) {
      setDeployError('Symbol must be 8 characters or fewer');
      return;
    }

    setDeploying(true);
    setDeployError(null);
    setDeploySuccess(null);

    try {
      // First ensure the user has opted into CORTEX
      const txns = await buildCreateAgentTxns(
        activeAccount.address,
        agentName.trim(),
        agentSymbol.trim().toUpperCase(),
      );

      // Sign with the connected wallet
      const signedTxns = await transactionSigner(
        txns.map((txn) => txn),
        txns.map((_, i) => i),
      );

      const txid = await submitSignedTransactions(signedTxns.filter(Boolean) as Uint8Array[]);
      const confirmed = await waitForConfirmation(txid);
      if (!confirmed) {
        throw new Error('Deployment transaction was submitted but not confirmed in time');
      }

      setDeploySuccess(`Agent deployed! Tx: ${txid.substring(0, 12)}...`);
      setAgentName('');
      setAgentSymbol('');

      // Refresh the list
      setTimeout(() => {
        refresh();
        setIsModalOpen(false);
        setDeploySuccess(null);
      }, 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Transaction failed';
      setDeployError(msg.includes('rejected') ? 'Transaction rejected by wallet' : msg);
    } finally {
      setDeploying(false);
    }
  }

  async function handleBuy() {
    if (!liveSelectedAgent) {
      return;
    }
    if (!activeAccount || !transactionSigner || !activeWallet) {
      setBuyError('Connect your wallet first');
      return;
    }

    if (parsedBuyAmount === null || parsedBuyAmount <= 0n) {
      setBuyError('Enter a valid token amount with up to 6 decimals');
      return;
    }
    if (parsedBuyAmount > MAX_MARKET_TRADE_AMOUNT) {
      setBuyError('Buy amount exceeds the current testnet per-transaction limit');
      return;
    }

    setBuying(true);
    setBuyError(null);
    setBuySuccess(null);

    try {
      const optedIn = await accountHasAssetOptIn(activeAccount.address, liveSelectedAgent.assetId);
      if (!optedIn) {
        const optInTxn = await buildAssetOptInTxn(activeAccount.address, liveSelectedAgent.assetId);
        const signedOptIn = await transactionSigner([optInTxn], [0]);
        const optInTxid = await submitSignedTransactions(signedOptIn.filter(Boolean) as Uint8Array[]);
        const confirmedOptIn = await waitForConfirmation(optInTxid);
        if (!confirmedOptIn) {
          throw new Error('Asset opt-in was submitted but not confirmed in time');
        }
      }

      const txns = await buildBuyTokensTxns(
        activeAccount.address,
        liveSelectedAgent.assetId,
        parsedBuyAmount,
        liveSelectedAgent.supply,
      );
      const signedTxns = await transactionSigner(
        txns.map((txn) => txn),
        txns.map((_, i) => i),
      );
      const txid = await submitSignedTransactions(signedTxns.filter(Boolean) as Uint8Array[]);
      const confirmed = await waitForConfirmation(txid);
      if (!confirmed) {
        throw new Error('Buy transaction was submitted but not confirmed in time');
      }

      setBuySuccess(`Purchased ${buyAmount} ${liveSelectedAgent.symbol}. Tx: ${txid.substring(0, 12)}...`);
      setTimeout(() => {
        refresh();
        setSelectedAgent(null);
        setBuySuccess(null);
      }, 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Buy transaction failed';
      setBuyError(msg.includes('rejected') ? 'Transaction rejected by wallet' : msg);
    } finally {
      setBuying(false);
    }
  }

  async function handleSell() {
    if (!liveSelectedAgent) {
      return;
    }
    if (!activeAccount || !transactionSigner || !activeWallet) {
      setSellError('Connect your wallet first');
      return;
    }
    if (parsedSellAmount === null || parsedSellAmount <= 0n) {
      setSellError('Enter a valid token amount with up to 6 decimals');
      return;
    }
    if (loadingWalletBalance || walletBalance === null) {
      setSellError('Wallet balance is still loading. Try again in a moment.');
      return;
    }
    if (walletBalance !== null && parsedSellAmount > walletBalance) {
      setSellError('Sell amount exceeds your wallet balance');
      return;
    }

    setSelling(true);
    setSellError(null);
    setSellSuccess(null);

    try {
      const txns = await buildSellTokensTxns(
        activeAccount.address,
        liveSelectedAgent.assetId,
        parsedSellAmount,
      );
      const signedTxns = await transactionSigner(
        txns.map((txn) => txn),
        txns.map((_, i) => i),
      );
      const txid = await submitSignedTransactions(signedTxns.filter(Boolean) as Uint8Array[]);
      const confirmed = await waitForConfirmation(txid);
      if (!confirmed) {
        throw new Error('Sell transaction was submitted but not confirmed in time');
      }

      setSellSuccess(`Sold ${sellAmount} ${liveSelectedAgent.symbol}. Tx: ${txid.substring(0, 12)}...`);
      setTimeout(() => {
        refresh();
        setSelectedAgent(null);
        setSellSuccess(null);
      }, 3000);
    } catch (err) {
      const msg = err instanceof Error ? err.message : 'Sell transaction failed';
      setSellError(msg.includes('rejected') ? 'Transaction rejected by wallet' : msg);
    } finally {
      setSelling(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Header with Launch Button */}
      <div className="flex flex-col sm:flex-row justify-between items-start sm:items-end gap-4 sm:gap-6 mb-8 sm:mb-12">
        <div className="space-y-2">
          <h2 className="text-2xl sm:text-4xl font-black tracking-tighter uppercase italic text-white">Agent Launchpad</h2>
          <p className="text-gray-500 font-medium text-sm sm:text-base">Neural-linked assets on the bonding curve.</p>
        </div>
        <div className="flex items-center gap-3 w-full sm:w-auto">
          {!activeAccount && (
            <div className="hidden sm:block">
              <WalletButton />
            </div>
          )}
          <button
            onClick={() => refresh()}
            className="p-3 sm:p-4 rounded-2xl border border-white/5 text-gray-500 hover:text-white hover:border-white/10 transition-all active:scale-95"
            aria-label="Refresh agents"
          >
            <RefreshCw className="w-5 h-5" />
          </button>
          <button
            onClick={() => setIsModalOpen(true)}
            className="bg-[#007AFF] hover:bg-[#0062CC] text-white px-6 sm:px-8 py-3 sm:py-4 rounded-2xl font-black uppercase tracking-widest text-xs flex items-center gap-3 transition-all shadow-lg shadow-[#007AFF]/20 active:scale-95 flex-1 sm:flex-initial justify-center"
          >
            <Plus className="w-5 h-5" /> Launch New Agent
          </button>
        </div>
      </div>

      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-stretch md:items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 w-5 h-5" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            maxLength={100}
            aria-label="Search agents"
            placeholder="Search Agents..."
            className="w-full bg-[#1A1A1A] border border-white/5 rounded-xl py-3 pl-12 pr-4 text-white focus:ring-2 focus:ring-[#007AFF]/50 outline-none transition-all font-medium"
          />
        </div>
        <div className="flex gap-2 sm:gap-3 w-full md:w-auto overflow-x-auto pb-1 -mb-1 scrollbar-none">
          {categories.map(cat => (
            <button
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-3 sm:px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border whitespace-nowrap flex-shrink-0 ${filter === cat ? 'bg-[#007AFF] text-white border-[#007AFF]' : 'bg-[#1A1A1A] text-gray-500 hover:text-white border-white/5'}`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Loading State */}
      {loading && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-500">
          <Loader2 className="w-8 h-8 animate-spin text-[#007AFF] mb-4" />
          <p className="text-sm font-bold uppercase tracking-widest">Querying Algorand Testnet...</p>
        </div>
      )}

      {/* Error State */}
      {error && !loading && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-500">
          <AlertCircle className="w-8 h-8 text-red-500 mb-4" />
          <p className="text-sm font-bold uppercase tracking-widest mb-2">Failed to load agents</p>
          <p className="text-xs text-gray-600 mb-4">{error}</p>
          <button onClick={refresh} className="text-[#007AFF] text-xs font-bold uppercase tracking-widest hover:underline">
            Try Again
          </button>
        </div>
      )}

      {/* Empty State */}
      {!loading && !error && agents.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-500">
          <Zap className="w-8 h-8 text-[#007AFF] mb-4" />
          <p className="text-sm font-bold uppercase tracking-widest mb-2">No Agents Deployed Yet</p>
          <p className="text-xs text-gray-600">Be the first to launch an agent on the bonding curve.</p>
        </div>
      )}

      {!loading && !error && agents.length > 0 && filteredAgents.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-gray-500">
          <Search className="w-8 h-8 text-[#007AFF] mb-4" />
          <p className="text-sm font-bold uppercase tracking-widest mb-2">No Agents Match</p>
          <p className="text-xs text-gray-600">Try a different search term or category filter.</p>
        </div>
      )}

      {/* Grid */}
      {!loading && !error && filteredAgents.length > 0 && (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          <AnimatePresence mode="popLayout">
            {filteredAgents.map((agent) => (
              <AgentCard key={agent.assetId} agent={agent} onOpen={openAgent} />
            ))}
          </AnimatePresence>
        </div>
      )}

      {/* Launch Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-end sm:items-center justify-center sm:p-6">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsModalOpen(false)} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
            <motion.div
              initial={{ y: '100%', opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: '100%', opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="bg-[#121217] border border-white/10 rounded-t-3xl sm:rounded-3xl p-6 sm:p-10 max-w-lg w-full relative shadow-2xl z-[101] max-h-[90vh] overflow-y-auto"
            >
              <div className="w-10 h-1 bg-white/20 rounded-full mx-auto mb-4 sm:hidden" />
              <button onClick={() => setIsModalOpen(false)} aria-label="Close modal" className="absolute top-4 right-4 sm:top-6 sm:right-6 p-2 text-gray-500 hover:text-white transition-colors"><X className="w-6 h-6" /></button>
              <h2 className="text-2xl sm:text-3xl font-black tracking-tighter uppercase italic mb-2">Deploy Agent</h2>
              <p className="text-gray-500 text-xs mb-6 sm:mb-8 font-bold italic uppercase tracking-widest">Protocol Fee: 100 $CORTEX</p>

              <div className="space-y-5 sm:space-y-6">
                {!activeAccount && (
                  <div className="rounded-2xl border border-yellow-500/20 bg-yellow-500/5 px-4 py-4 text-center space-y-4">
                    <p className="text-yellow-500/80 text-xs font-bold uppercase tracking-widest">
                      Connect your wallet to deploy
                    </p>
                    <div className="flex justify-center">
                      <WalletButton />
                    </div>
                  </div>
                )}

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Agent Name</label>
                  <input
                    type="text"
                    value={agentName}
                    onChange={(e) => setAgentName(e.target.value)}
                    placeholder="e.g. Neural Sentinel"
                    maxLength={32}
                    aria-label="Agent name"
                    className="w-full bg-[#050505] border border-white/5 rounded-xl p-3 sm:p-4 text-white outline-none focus:ring-2 focus:ring-[#007AFF]/50 transition-all font-medium"
                  />
                </div>
                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Symbol</label>
                  <input
                    type="text"
                    value={agentSymbol}
                    onChange={(e) => setAgentSymbol(e.target.value.toUpperCase())}
                    placeholder="e.g. SENT"
                    maxLength={8}
                    aria-label="Agent symbol"
                    className="w-full bg-[#050505] border border-white/5 rounded-xl p-3 sm:p-4 text-white outline-none focus:ring-2 focus:ring-[#007AFF]/50 transition-all font-medium uppercase"
                  />
                </div>

                {deployError && (
                  <p className="text-red-400 text-xs font-bold text-center py-1">{deployError}</p>
                )}

                {deploySuccess && (
                  <p className="text-emerald-400 text-xs font-bold text-center py-1">{deploySuccess}</p>
                )}

                <button
                  onClick={handleDeploy}
                  disabled={deploying || !activeAccount}
                  className="w-full bg-white text-black py-4 sm:py-5 rounded-2xl font-black uppercase tracking-tighter text-sm hover:bg-gray-200 transition-all mt-2 sm:mt-4 active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                >
                  {deploying ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Deploying...
                    </>
                  ) : (
                    'Initialize Emancipation'
                  )}
                </button>

                <p className="text-[9px] text-gray-600 text-center font-mono uppercase tracking-widest">
                  Requires 100 CORTEX + ALGO for fees • Algorand Testnet
                </p>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>

      {/* Agent Detail / Buy Modal */}
      <AnimatePresence>
        {liveSelectedAgent && (
          <div className="fixed inset-0 z-[110] flex items-end sm:items-center justify-center sm:p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setSelectedAgent(null)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ y: '100%', opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: '100%', opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="bg-[#121217] border border-white/10 rounded-t-3xl sm:rounded-3xl p-6 sm:p-8 max-w-2xl w-full relative shadow-2xl z-[111] max-h-[90vh] overflow-y-auto"
            >
              <div className="w-10 h-1 bg-white/20 rounded-full mx-auto mb-4 sm:hidden" />
              <button
                onClick={() => setSelectedAgent(null)}
                aria-label="Close agent modal"
                className="absolute top-4 right-4 sm:top-6 sm:right-6 p-2 text-gray-500 hover:text-white transition-colors"
              >
                <X className="w-6 h-6" />
              </button>

              <div className="flex flex-col sm:flex-row sm:items-start justify-between gap-4 mb-6">
                <div className="space-y-2">
                  <div className="flex items-center gap-3">
                    <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-[#007AFF]/20 to-indigo-500/20 border border-white/5 flex items-center justify-center text-[#007AFF]">
                      <Zap className="w-6 h-6 fill-current" />
                    </div>
                    <div>
                      <h2 className="text-2xl sm:text-3xl font-black tracking-tighter uppercase italic text-white">{liveSelectedAgent.name}</h2>
                      <p className="text-[10px] font-mono uppercase tracking-[0.3em] text-[#007AFF]">{liveSelectedAgent.symbol}</p>
                    </div>
                  </div>
                  <p className="text-sm text-gray-500 max-w-xl">
                    Live testnet agent token discovered from the canonical PURECORTEX factory deployment.
                  </p>
                </div>
                <a
                  href={`https://testnet.explorer.perawallet.app/asset/${liveSelectedAgent.assetId}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-2 text-[10px] font-mono uppercase tracking-widest text-[#007AFF] hover:underline"
                >
                  Open in Explorer
                  <ExternalLink className="w-3.5 h-3.5" />
                </a>
              </div>

              <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
                <StatCard label="Current Price" value={liveSelectedAgent.price} />
                <StatCard label="Curve Value" value={liveSelectedAgent.mcap} />
                <StatCard label="Holders" value={String(liveSelectedAgent.holders)} />
                <StatCard label="Live Supply" value={formatFixedUnits(liveSelectedAgent.supply)} />
              </div>

              <div className="bg-[#050505] border border-white/5 rounded-2xl p-5 space-y-4 mb-6">
                <div className="flex items-center justify-between text-[10px] font-mono uppercase tracking-widest text-gray-500">
                  <span>Bonding Curve Progress</span>
                  <span className="text-[#007AFF]">{liveSelectedAgent.curve}%</span>
                </div>
                <div className="w-full h-2 bg-black/60 rounded-full overflow-hidden border border-white/5">
                  <motion.div
                    initial={{ width: 0 }}
                    animate={{ width: `${liveSelectedAgent.curve}%` }}
                    className="h-full bg-gradient-to-r from-[#007AFF] to-[#6366F1]"
                  />
                </div>
              </div>

              <div className="bg-[#050505] border border-white/5 rounded-2xl p-5 space-y-5">
                <div className="flex items-center gap-3">
                  <Coins className="w-5 h-5 text-[#007AFF]" />
                  <h3 className="text-lg font-black uppercase tracking-tighter italic">Buy Tokens</h3>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Amount</label>
                  <input
                    type="text"
                    value={buyAmount}
                    onChange={(e) => setBuyAmount(e.target.value)}
                    placeholder="1.0"
                    aria-label="Buy amount"
                    className="w-full bg-[#121217] border border-white/5 rounded-xl p-4 text-white outline-none focus:ring-2 focus:ring-[#007AFF]/50 transition-all font-medium"
                  />
                  <p className="text-[10px] text-gray-600 font-mono uppercase tracking-widest">
                    Up to 6 decimals. Asset opt-in is handled automatically if needed.
                  </p>
                  {activeAccount && (
                    <p className="text-[10px] text-gray-600 font-mono uppercase tracking-widest">
                      Wallet balance: {loadingWalletBalance ? 'Loading...' : `${formatFixedUnits(walletBalance ?? 0n)} ${liveSelectedAgent.symbol}`}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <StatCard label="Curve Cost" value={buyQuote ? formatAlgoAmount(buyQuote.baseCost) : '--'} />
                  <StatCard label="Protocol Fee" value={buyQuote ? formatAlgoAmount(buyQuote.fee) : '--'} />
                  <StatCard label="Total" value={buyQuote ? formatAlgoAmount(buyQuote.totalCost) : '--'} />
                </div>

                {!activeAccount && (
                  <p className="text-yellow-500/80 text-xs font-bold uppercase tracking-widest text-center py-2">
                    Connect your wallet to buy on testnet
                  </p>
                )}

                {buyError && (
                  <p className="text-red-400 text-xs font-bold text-center py-1">{buyError}</p>
                )}

                {buySuccess && (
                  <p className="text-emerald-400 text-xs font-bold text-center py-1">{buySuccess}</p>
                )}

                <div className="flex flex-col sm:flex-row gap-3">
                  <button
                    onClick={handleBuy}
                    disabled={buying || !activeAccount || !buyQuote}
                    className="flex-1 bg-white text-black py-4 rounded-2xl font-black uppercase tracking-tighter text-sm hover:bg-gray-200 transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                  >
                    {buying ? (
                      <>
                        <Loader2 className="w-5 h-5 animate-spin" />
                        Buying...
                      </>
                    ) : (
                      <>
                        <ShoppingCart className="w-4 h-4" />
                        Buy on Testnet
                      </>
                    )}
                  </button>
                  <a
                    href={`https://testnet.explorer.perawallet.app/asset/${liveSelectedAgent.assetId}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex-1 inline-flex items-center justify-center gap-2 border border-white/10 text-gray-300 py-4 rounded-2xl font-bold uppercase tracking-widest text-xs hover:text-white hover:border-[#007AFF]/40 transition-all"
                  >
                    <BarChart3 className="w-4 h-4" />
                    Asset Detail
                  </a>
                </div>
              </div>

              <div className="bg-[#050505] border border-white/5 rounded-2xl p-5 space-y-5">
                <div className="flex items-center gap-3">
                  <Coins className="w-5 h-5 text-red-400" />
                  <h3 className="text-lg font-black uppercase tracking-tighter italic">Sell Tokens</h3>
                </div>

                <div className="space-y-2">
                  <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Amount</label>
                  <input
                    type="text"
                    value={sellAmount}
                    onChange={(e) => setSellAmount(e.target.value)}
                    placeholder="1.0"
                    aria-label="Sell amount"
                    className="w-full bg-[#121217] border border-white/5 rounded-xl p-4 text-white outline-none focus:ring-2 focus:ring-red-400/40 transition-all font-medium"
                  />
                  <p className="text-[10px] text-gray-600 font-mono uppercase tracking-widest">
                    Sell back into the live testnet bonding curve. Wallet balance is checked before submission.
                  </p>
                  {activeAccount && (
                    <p className="text-[10px] text-gray-600 font-mono uppercase tracking-widest">
                      Wallet balance: {loadingWalletBalance ? 'Loading...' : `${formatFixedUnits(walletBalance ?? 0n)} ${liveSelectedAgent.symbol}`}
                    </p>
                  )}
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                  <StatCard label="Gross Return" value={sellQuote ? formatAlgoAmount(sellQuote.grossReturn) : '--'} />
                  <StatCard label="Protocol Fee" value={sellQuote ? formatAlgoAmount(sellQuote.fee) : '--'} />
                  <StatCard label="Net Return" value={sellQuote ? formatAlgoAmount(sellQuote.netReturn) : '--'} />
                </div>

                {!activeAccount && (
                  <p className="text-yellow-500/80 text-xs font-bold uppercase tracking-widest text-center py-2">
                    Connect your wallet to sell on testnet
                  </p>
                )}

                {sellError && (
                  <p className="text-red-400 text-xs font-bold text-center py-1">{sellError}</p>
                )}

                {sellSuccess && (
                  <p className="text-emerald-400 text-xs font-bold text-center py-1">{sellSuccess}</p>
                )}

                <button
                  onClick={handleSell}
                  disabled={selling || !activeAccount || !sellQuote || loadingWalletBalance || walletBalance === null || (parsedSellAmount !== null && parsedSellAmount > walletBalance)}
                  className="w-full bg-red-500 text-black py-4 rounded-2xl font-black uppercase tracking-tighter text-sm hover:bg-red-400 transition-all active:scale-[0.98] disabled:opacity-40 disabled:cursor-not-allowed flex items-center justify-center gap-3"
                >
                  {selling ? (
                    <>
                      <Loader2 className="w-5 h-5 animate-spin" />
                      Selling...
                    </>
                  ) : (
                    'Sell on Testnet'
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}

function StatCard({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-[#1A1A1A] border border-white/5 rounded-xl p-4 space-y-1">
      <p className="text-[9px] text-gray-600 font-mono uppercase font-bold tracking-widest">{label}</p>
      <p className="text-sm font-black text-white italic break-words">{value}</p>
    </div>
  );
}

function AgentCard({ agent, onOpen }: { agent: AgentData; onOpen: (agent: AgentData) => void }) {
  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-5 hover:border-[#007AFF]/40 transition-all group relative overflow-hidden"
    >
      <div className="absolute -top-24 -right-24 w-48 h-48 bg-[#007AFF]/5 blur-[80px] group-hover:bg-[#007AFF]/10 transition-all" />

      <div className="flex justify-between items-start mb-4">
        <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#007AFF]/20 to-indigo-500/20 border border-white/5 flex items-center justify-center text-[#007AFF] group-hover:scale-110 transition-transform shadow-inner">
          <Zap className="w-6 h-6 fill-current" />
        </div>
        <div className="text-right">
          <div className="px-2 py-1 rounded-md text-[10px] font-black font-mono bg-[#007AFF]/10 text-[#007AFF]">
            ASA {agent.assetId}
          </div>
        </div>
      </div>

      <div className="space-y-1 mb-6">
        <h3 className="text-white font-black text-lg flex items-center gap-2 tracking-tighter uppercase italic">
          {agent.name}
          <ArrowUpRight className="w-4 h-4 text-gray-700 group-hover:text-[#007AFF] transition-colors" />
        </h3>
        <p className="text-[#007AFF] text-[9px] font-mono uppercase tracking-[0.3em] font-bold">{agent.symbol}</p>
      </div>

      <div className="grid grid-cols-2 gap-4 mb-6">
        <div>
          <p className="text-[9px] text-gray-600 font-mono uppercase font-bold tracking-widest">Price</p>
          <p className="text-sm font-black text-white italic">{agent.price}</p>
        </div>
        <div>
          <p className="text-[9px] text-gray-600 font-mono uppercase font-bold tracking-widest">Curve Value</p>
          <p className="text-sm font-black text-white italic">{agent.mcap}</p>
        </div>
      </div>

      {/* Bonding Curve Progress */}
      <div className="space-y-2">
        <div className="flex justify-between text-[9px] font-mono uppercase font-bold text-gray-600 tracking-widest">
          <span>Curve Level</span>
          <span className="text-[#007AFF]">{agent.curve}%</span>
        </div>
        <div className="w-full h-1.5 bg-black/60 rounded-full overflow-hidden border border-white/5">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${agent.curve}%` }}
            className="h-full bg-gradient-to-r from-[#007AFF] to-[#6366F1]"
          />
        </div>
      </div>

      <div className="mt-6 flex items-center justify-between text-[9px] text-gray-500 border-t border-white/5 pt-4 font-mono uppercase font-bold tracking-tighter">
        <div className="flex items-center gap-1"><Users className="w-3 h-3 text-[#007AFF]" /> {agent.holders} Holders</div>
        <div className="flex items-center gap-2">
          <button
            onClick={() => onOpen(agent)}
            className="inline-flex items-center gap-1 text-gray-400 hover:text-white transition-colors"
          >
            <ShoppingCart className="w-3 h-3" />
            Buy
          </button>
          <a
            href={`https://testnet.explorer.perawallet.app/asset/${agent.assetId}`}
            target="_blank"
            rel="noopener noreferrer"
            onClick={(e) => e.stopPropagation()}
            className="inline-flex items-center gap-1 hover:text-white transition-colors"
          >
            <BarChart3 className="w-3 h-3" />
            Explorer
          </a>
        </div>
      </div>
    </motion.div>
  );
}
