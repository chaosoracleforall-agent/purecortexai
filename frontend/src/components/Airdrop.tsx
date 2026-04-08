'use client';

import { useWallet } from '@txnlab/use-wallet-react';
import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import Link from 'next/link';
import Image from 'next/image';
import {
  Gift,
  Shield,
  CheckCircle2,
  Clock,
  Users,
  Coins,
  Code2,
  MessageSquare,
  ChevronRight,
  Wallet,
  ExternalLink,
  Sparkles,
} from 'lucide-react';
import {
  TGE_DATE_ISO,
  AIRDROP_CONTRACT_ID,
  AIRDROP_CLAIM_DEADLINE,
  CORTEX_ASSET_ID,
  PUBLIC_API_URL,
} from '@/lib/protocolConfig';

interface AirdropTier {
  id: string;
  name: string;
  icon: React.ElementType;
  allocationPct: number;
  description: string;
  criteria: string[];
  status: 'active' | 'upcoming' | 'closed';
}

const TOTAL_AIRDROP_CORTEX = 3_100_000_000_000_000;

const AIRDROP_TIERS: AirdropTier[] = [
  {
    id: 'testnet_pioneers',
    name: 'Testnet Pioneers',
    icon: Shield,
    allocationPct: 5,
    description: 'Early believers who tested the protocol on testnet before mainnet launch.',
    criteria: [
      'Interacted with PureCortex testnet contracts',
      'Created or traded agent tokens on testnet',
      'Participated in testnet governance',
    ],
    status: 'active',
  },
  {
    id: 'algorand_defi',
    name: 'Algorand DeFi Users',
    icon: Coins,
    allocationPct: 30,
    description: 'Active participants in the Algorand DeFi ecosystem.',
    criteria: [
      'Provided liquidity on Tinyman, Pact, or Humble',
      'Deposited or borrowed on Folks Finance',
      'Minimum 10 ALGO balance at snapshot',
    ],
    status: 'active',
  },
  {
    id: 'algorand_governors',
    name: 'Algorand Governors',
    icon: Users,
    allocationPct: 20,
    description: 'Wallets that participated in Algorand governance periods.',
    criteria: [
      'Committed ALGO to any governance period',
      'Maintained commitment through period end',
    ],
    status: 'active',
  },
  {
    id: 'nfd_holders',
    name: 'NFD Holders',
    icon: Sparkles,
    allocationPct: 10,
    description: 'Holders of .algo Non-Fungible Domains.',
    criteria: [
      'Own at least one .algo NFD at snapshot',
    ],
    status: 'active',
  },
  {
    id: 'developers',
    name: 'Developer Builders',
    icon: Code2,
    allocationPct: 10,
    description: 'Developers who have built on Algorand.',
    criteria: [
      'Deployed a smart contract to Algorand mainnet',
      'Contributed to open-source Algorand projects',
      'Registered as a PureCortex developer',
    ],
    status: 'active',
  },
  {
    id: 'social_campaign',
    name: 'Social Campaign',
    icon: MessageSquare,
    allocationPct: 15,
    description: 'Community members who help spread awareness.',
    criteria: [
      'Follow @purecortexai on X',
      'Retweet the launch announcement',
      'Connect wallet on this page',
    ],
    status: 'upcoming',
  },
  {
    id: 'community_tasks',
    name: 'Community Tasks',
    icon: CheckCircle2,
    allocationPct: 10,
    description: 'Active community participants completing engagement tasks.',
    criteria: [
      'Join the PureCortex Discord',
      'Participate in community discussions',
      'Create educational content about PureCortex',
    ],
    status: 'upcoming',
  },
];

function formatCortex(amount: number): string {
  const tokens = amount / 1_000_000;
  if (tokens >= 1_000_000_000_000) return `${(tokens / 1_000_000_000_000).toFixed(1)}T`;
  if (tokens >= 1_000_000_000) return `${(tokens / 1_000_000_000).toFixed(1)}B`;
  if (tokens >= 1_000_000) return `${(tokens / 1_000_000).toFixed(1)}M`;
  return tokens.toLocaleString();
}

export default function Airdrop() {
  const { activeAccount, wallets, transactionSigner } = useWallet();
  const [timeLeft, setTimeLeft] = useState<{ days: number; hours: number; minutes: number; seconds: number } | null>(null);
  const [registered, setRegistered] = useState(false);
  const [registering, setRegistering] = useState(false);
  const [registerError, setRegisterError] = useState<string | null>(null);
  const [expandedTier, setExpandedTier] = useState<string | null>(null);
  const [walletModalOpen, setWalletModalOpen] = useState(false);
  const [connecting, setConnecting] = useState<string | null>(null);

  // Claim flow state
  const [eligibility, setEligibility] = useState<{
    eligible: boolean;
    allocation: number;
    tiers: string[];
  } | null>(null);
  const [checkingEligibility, setCheckingEligibility] = useState(false);
  const [claiming, setClaiming] = useState(false);
  const [claimed, setClaimed] = useState(false);
  const [claimError, setClaimError] = useState<string | null>(null);
  const [claimTxId, setClaimTxId] = useState<string | null>(null);

  const claimsOpen = new Date(AIRDROP_CLAIM_DEADLINE).getTime() > Date.now()
    && new Date('2026-04-21T00:00:00Z').getTime() <= Date.now();

  useEffect(() => {
    const launchDate = new Date(TGE_DATE_ISO).getTime();
    const update = () => {
      const distance = Math.max(0, launchDate - Date.now());
      setTimeLeft({
        days: Math.floor(distance / (1000 * 60 * 60 * 24)),
        hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
        minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
        seconds: Math.floor((distance % (1000 * 60)) / 1000),
      });
    };
    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  const handleRegister = useCallback(async () => {
    if (!activeAccount || registering) return;
    setRegistering(true);
    setRegisterError(null);
    try {
      const response = await fetch('/api/airdrop/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ wallet_address: activeAccount.address }),
      });
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || 'Failed to register wallet');
      }
      setRegistered(true);
    } catch (error) {
      setRegisterError(error instanceof Error ? error.message : 'Failed to register wallet');
    } finally {
      setRegistering(false);
    }
  }, [activeAccount, registering]);

  async function handleConnect(walletId: string) {
    const wallet = wallets?.find((w) => w.id === walletId);
    if (!wallet) return;
    setConnecting(walletId);
    try {
      await wallet.connect();
      setWalletModalOpen(false);
    } catch {
      // cancelled
    } finally {
      setConnecting(null);
    }
  }

  // Check eligibility when wallet connects
  const checkEligibility = useCallback(async () => {
    if (!activeAccount) return;
    setCheckingEligibility(true);
    setClaimError(null);
    try {
      const res = await fetch(`${PUBLIC_API_URL}/api/airdrop/eligibility/${activeAccount.address}`);
      if (!res.ok) {
        if (res.status === 503) {
          setEligibility(null);
          return;
        }
        throw new Error('Failed to check eligibility');
      }
      const data = await res.json();
      setEligibility({
        eligible: data.eligible,
        allocation: data.allocation || 0,
        tiers: data.tiers || [],
      });
    } catch {
      setEligibility(null);
    } finally {
      setCheckingEligibility(false);
    }
  }, [activeAccount]);

  useEffect(() => {
    if (activeAccount && claimsOpen) {
      checkEligibility();
    }
  }, [activeAccount, claimsOpen, checkEligibility]);

  const handleClaim = useCallback(async () => {
    if (!activeAccount || !AIRDROP_CONTRACT_ID || claiming) return;
    setClaiming(true);
    setClaimError(null);
    try {
      // 1. Fetch proof from backend
      const proofRes = await fetch(`${PUBLIC_API_URL}/api/airdrop/proof/${activeAccount.address}`);
      if (!proofRes.ok) throw new Error('No airdrop allocation found for this address');
      const proofData = await proofRes.json();

      // 2. Build the claim transaction using algosdk
      const algosdk = await import('algosdk');
      const algodClient = new algosdk.Algodv2('', 'https://mainnet-api.4160.nodely.dev', '');
      const suggestedParams = await algodClient.getTransactionParams().do();

      // Encode ABI call: claim(uint64, byte[])
      const packedProof = new Uint8Array(
        (proofData.proof_packed_hex.match(/.{1,2}/g) || []).map((b: string) => parseInt(b, 16))
      );

      const abiMethod = new algosdk.ABIMethod({
        name: 'claim',
        args: [
          { type: 'uint64', name: 'amount' },
          { type: 'byte[]', name: 'proof' },
        ],
        returns: { type: 'uint64' },
      });

      const atc = new algosdk.AtomicTransactionComposer();

      if (!transactionSigner) throw new Error('Wallet signer not available');

      atc.addMethodCall({
        appID: AIRDROP_CONTRACT_ID,
        method: abiMethod,
        methodArgs: [proofData.amount, packedProof],
        sender: activeAccount.address,
        suggestedParams: {
          ...suggestedParams,
          fee: 2000,
          flatFee: true,
        },
        signer: transactionSigner,
        boxes: [{
          appIndex: AIRDROP_CONTRACT_ID,
          name: algosdk.decodeAddress(activeAccount.address).publicKey,
        }],
        appForeignAssets: [CORTEX_ASSET_ID],
      });

      const result = await atc.execute(algodClient, 4);
      setClaimTxId(result.txIDs[0]);
      setClaimed(true);
    } catch (error) {
      setClaimError(error instanceof Error ? error.message : 'Claim failed');
    } finally {
      setClaiming(false);
    }
  }, [activeAccount, claiming, wallets]);

  return (
    <div className="space-y-8 sm:space-y-12 max-w-5xl mx-auto">
      {/* Header */}
      <div
        style={{ animation: 'fadeInUp 0.5s ease-out both' }}
        className="space-y-4"
      >
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 sm:w-12 sm:h-12 rounded-2xl bg-[#007AFF]/10 border border-[#007AFF]/20 flex items-center justify-center">
            <Gift className="w-5 h-5 sm:w-6 sm:h-6 text-[#007AFF]" />
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-black tracking-tighter uppercase italic">
              Genesis Airdrop
            </h1>
            <p className="text-xs sm:text-sm text-gray-500 font-bold uppercase tracking-widest">
              31% of $CORTEX supply to the community
            </p>
          </div>
        </div>
      </div>

      {/* Stats Row */}
      <div
        style={{ animation: 'fadeInUp 0.5s ease-out 0.1s both' }}
        className="grid grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4"
      >
        {[
          { label: 'Total Allocation', value: formatCortex(TOTAL_AIRDROP_CORTEX), sub: '31% of supply' },
          { label: 'Eligible Tiers', value: '7', sub: 'qualification paths' },
          { label: 'Claim Window', value: '90 days', sub: 'after TGE' },
          { label: 'Anti-Sybil', value: 'Active', sub: 'wallet scoring' },
        ].map((stat, i) => (
          <div key={i} className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-4 sm:p-5 space-y-1">
            <p className="text-[9px] sm:text-[10px] font-bold text-gray-500 uppercase tracking-widest">{stat.label}</p>
            <p className="text-xl sm:text-2xl font-black tracking-tighter">{stat.value}</p>
            <p className="text-[9px] sm:text-[10px] font-bold text-[#007AFF] uppercase tracking-wider">{stat.sub}</p>
          </div>
        ))}
      </div>

      {/* Countdown + Registration */}
      <div
        style={{ animation: 'fadeInUp 0.5s ease-out 0.15s both' }}
        className="bg-[#1A1A1A] border border-white/5 rounded-3xl p-6 sm:p-8 space-y-6"
      >
        <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
          <div className="space-y-1">
            <h2 className="text-[10px] font-black text-[#007AFF] uppercase tracking-[0.3em]">Claims Open At TGE</h2>
            <p className="text-lg sm:text-2xl font-bold italic">MARCH 31, 2026</p>
          </div>
          <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-amber-500/10 border border-amber-500/20">
            <Clock className="w-3.5 h-3.5 text-amber-500" />
            <span className="text-[10px] font-bold text-amber-500 uppercase tracking-widest">Registration Open</span>
          </div>
        </div>

        <div className="grid grid-cols-4 gap-3">
          {[
            { label: 'Days', val: timeLeft?.days ?? 0 },
            { label: 'Hrs', val: timeLeft?.hours ?? 0 },
            { label: 'Min', val: timeLeft?.minutes ?? 0 },
            { label: 'Sec', val: timeLeft?.seconds ?? 0 },
          ].map((t, i) => (
            <div key={i} className="rounded-2xl bg-black/30 border border-white/5 py-3 sm:py-4 text-center">
              <div className="text-2xl sm:text-4xl font-black tracking-tighter tabular-nums leading-none">
                {timeLeft ? String(t.val).padStart(2, '0') : '--'}
              </div>
              <div className="text-[8px] sm:text-[9px] font-black text-gray-500 uppercase tracking-[0.25em] mt-1">{t.label}</div>
            </div>
          ))}
        </div>

        {/* Registration CTA */}
        <div className="pt-4 border-t border-white/5">
          {!activeAccount ? (
            <button
              onClick={() => setWalletModalOpen(true)}
              className="w-full flex items-center justify-center gap-3 bg-[#007AFF] hover:bg-[#0062CC] text-white px-6 py-4 rounded-2xl font-black uppercase tracking-tighter text-sm transition-all shadow-lg shadow-[#007AFF]/20 active:scale-[0.98]"
            >
              <Wallet className="w-5 h-5" />
              Connect Wallet to Register
            </button>
          ) : registered ? (
            <div className="flex items-center justify-center gap-3 bg-emerald-500/10 border border-emerald-500/20 px-6 py-4 rounded-2xl">
              <CheckCircle2 className="w-5 h-5 text-emerald-500" />
              <span className="text-sm font-black uppercase tracking-wider text-emerald-500">
                Registered — {activeAccount.address.substring(0, 8)}...{activeAccount.address.substring(activeAccount.address.length - 6)}
              </span>
            </div>
          ) : (
            <button
              onClick={handleRegister}
              disabled={registering}
              className="w-full flex items-center justify-center gap-3 bg-[#007AFF] hover:bg-[#0062CC] text-white px-6 py-4 rounded-2xl font-black uppercase tracking-tighter text-sm transition-all shadow-lg shadow-[#007AFF]/20 active:scale-[0.98]"
            >
              <Gift className="w-5 h-5" />
              {registering ? 'Registering...' : 'Register for Genesis Airdrop'}
            </button>
          )}
          {registerError && (
            <p className="text-center text-[10px] text-red-400 mt-3 font-semibold">
              {registerError}
            </p>
          )}
          <p className="text-center text-[9px] text-gray-600 mt-3 font-mono uppercase tracking-widest">
            Registration does not guarantee allocation. Eligibility verified at snapshot.
          </p>
        </div>
      </div>

      {/* Claim Section — visible after claims open */}
      {claimsOpen && activeAccount && (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.17 }}
          className="bg-[#1A1A1A] border border-white/5 rounded-3xl p-6 sm:p-8 space-y-5"
        >
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 flex items-center justify-center">
              <Gift className="w-5 h-5 text-emerald-500" />
            </div>
            <div>
              <h2 className="text-lg font-black tracking-tighter uppercase italic">Claim Your $CORTEX</h2>
              <p className="text-[10px] text-gray-500 font-bold uppercase tracking-widest">Non-custodial on-chain claim</p>
            </div>
          </div>

          {checkingEligibility ? (
            <div className="text-center py-6">
              <p className="text-sm text-gray-400 animate-pulse">Checking eligibility...</p>
            </div>
          ) : eligibility?.eligible ? (
            <div className="space-y-4">
              <div className="bg-black/30 border border-emerald-500/10 rounded-2xl p-4 space-y-2">
                <p className="text-[10px] font-bold text-emerald-500 uppercase tracking-widest">You are eligible</p>
                <p className="text-2xl font-black tracking-tighter">{formatCortex(eligibility.allocation)} <span className="text-sm text-gray-500">CORTEX</span></p>
                {eligibility.tiers.length > 0 && (
                  <p className="text-[10px] text-gray-500">Qualified tiers: {eligibility.tiers.join(', ')}</p>
                )}
              </div>

              {claimed ? (
                <div className="flex items-center justify-center gap-3 bg-emerald-500/10 border border-emerald-500/20 px-6 py-4 rounded-2xl">
                  <CheckCircle2 className="w-5 h-5 text-emerald-500" />
                  <div className="text-center">
                    <span className="text-sm font-black uppercase tracking-wider text-emerald-500 block">Claimed Successfully</span>
                    {claimTxId && (
                      <a
                        href={`https://explorer.perawallet.app/tx/${claimTxId}`}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-[10px] text-[#007AFF] font-mono hover:underline mt-1 inline-flex items-center gap-1"
                      >
                        View transaction <ExternalLink className="w-3 h-3" />
                      </a>
                    )}
                  </div>
                </div>
              ) : !AIRDROP_CONTRACT_ID ? (
                <div className="flex items-center justify-center gap-3 bg-amber-500/10 border border-amber-500/20 px-6 py-4 rounded-2xl">
                  <Clock className="w-4 h-4 text-amber-500" />
                  <span className="text-sm font-bold text-amber-500">Claim contract deployment pending</span>
                </div>
              ) : (
                <button
                  onClick={handleClaim}
                  disabled={claiming}
                  className="w-full flex items-center justify-center gap-3 bg-emerald-500 hover:bg-emerald-600 text-white px-6 py-4 rounded-2xl font-black uppercase tracking-tighter text-sm transition-all shadow-lg shadow-emerald-500/20 active:scale-[0.98] disabled:opacity-60"
                >
                  <Gift className="w-5 h-5" />
                  {claiming ? 'Claiming...' : `Claim ${formatCortex(eligibility.allocation)} CORTEX`}
                </button>
              )}
              {claimError && (
                <p className="text-center text-[10px] text-red-400 font-semibold">{claimError}</p>
              )}
              <p className="text-center text-[9px] text-gray-600 font-mono uppercase tracking-widest">
                You pay the transaction fee. Tokens are sent directly to your wallet via smart contract.
              </p>
            </div>
          ) : eligibility && !eligibility.eligible ? (
            <div className="bg-black/30 border border-white/5 rounded-2xl p-4 text-center">
              <p className="text-sm text-gray-400">This wallet is not eligible for the airdrop.</p>
              <p className="text-[10px] text-gray-600 mt-1">Check eligibility criteria below or try a different wallet.</p>
            </div>
          ) : (
            <div className="bg-black/30 border border-white/5 rounded-2xl p-4 text-center">
              <p className="text-sm text-gray-400">Snapshot data not yet available.</p>
              <p className="text-[10px] text-gray-600 mt-1">Eligibility checker goes live April 15.</p>
            </div>
          )}
        </motion.div>
      )}

      {/* Airdrop Tiers */}
      <div
        style={{ animation: 'fadeInUp 0.5s ease-out 0.2s both' }}
        className="space-y-4"
      >
        <h2 className="text-lg sm:text-xl font-black tracking-tighter uppercase italic">
          Eligibility Tiers
        </h2>

        <div className="space-y-3">
          {AIRDROP_TIERS.map((tier) => {
            const Icon = tier.icon;
            const allocation = (TOTAL_AIRDROP_CORTEX * tier.allocationPct) / 100;
            const isExpanded = expandedTier === tier.id;

            return (
              <motion.div
                key={tier.id}
                layout
                className="bg-[#1A1A1A] border border-white/5 rounded-2xl overflow-hidden"
              >
                <button
                  onClick={() => setExpandedTier(isExpanded ? null : tier.id)}
                  className="w-full flex items-center gap-3 sm:gap-4 p-4 sm:p-5 text-left hover:bg-white/[0.02] transition-colors"
                >
                  <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
                    <Icon className="w-5 h-5 text-[#007AFF]" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <h3 className="text-sm font-bold uppercase tracking-wider">{tier.name}</h3>
                      {tier.status === 'active' && (
                        <span className="px-2 py-0.5 rounded-full bg-emerald-500/10 text-[8px] font-bold text-emerald-500 uppercase tracking-widest">Active</span>
                      )}
                      {tier.status === 'upcoming' && (
                        <span className="px-2 py-0.5 rounded-full bg-amber-500/10 text-[8px] font-bold text-amber-500 uppercase tracking-widest">Soon</span>
                      )}
                    </div>
                    <p className="text-xs text-gray-500 mt-0.5">{tier.description}</p>
                  </div>
                  <div className="text-right flex-shrink-0">
                    <p className="text-sm sm:text-base font-black text-[#007AFF]">{tier.allocationPct}%</p>
                    <p className="text-[9px] font-mono text-gray-600">{formatCortex(allocation)} CORTEX</p>
                  </div>
                  <ChevronRight className={`w-4 h-4 text-gray-600 transition-transform flex-shrink-0 ${isExpanded ? 'rotate-90' : ''}`} />
                </button>

                <AnimatePresence>
                  {isExpanded && (
                    <motion.div
                      initial={{ height: 0, opacity: 0 }}
                      animate={{ height: 'auto', opacity: 1 }}
                      exit={{ height: 0, opacity: 0 }}
                      transition={{ duration: 0.2 }}
                      className="overflow-hidden"
                    >
                      <div className="px-5 pb-5 pt-0 border-t border-white/5">
                        <p className="text-[10px] font-bold text-gray-500 uppercase tracking-widest mt-4 mb-2">Eligibility Criteria</p>
                        <ul className="space-y-2">
                          {tier.criteria.map((criterion, i) => (
                            <li key={i} className="flex items-start gap-2 text-sm text-gray-400">
                              <CheckCircle2 className="w-4 h-4 text-[#007AFF] mt-0.5 flex-shrink-0" />
                              {criterion}
                            </li>
                          ))}
                        </ul>
                      </div>
                    </motion.div>
                  )}
                </AnimatePresence>
              </motion.div>
            );
          })}
        </div>
      </div>

      {/* Timeline */}
      <div
        style={{ animation: 'fadeInUp 0.5s ease-out 0.25s both' }}
        className="bg-[#1A1A1A] border border-white/5 rounded-3xl p-6 sm:p-8 space-y-6"
      >
        <h2 className="text-lg font-black tracking-tighter uppercase italic">Airdrop Timeline</h2>
        <div className="space-y-0">
          {[
            { date: 'Mar 31', label: 'TGE + Airdrop Announcement', status: 'upcoming' as const, detail: 'Eligibility criteria published, registration opens' },
            { date: 'Apr 1-7', label: 'Snapshot Window', status: 'upcoming' as const, detail: 'On-chain activity evaluated for all tiers' },
            { date: 'Apr 8', label: 'Snapshot Taken', status: 'upcoming' as const, detail: 'Merkle tree generated from eligible wallets' },
            { date: 'Apr 9-14', label: 'Social Campaign Opens', status: 'upcoming' as const, detail: 'Follow, retweet, and engage for social tier' },
            { date: 'Apr 15', label: 'Eligibility Checker Live', status: 'upcoming' as const, detail: 'Check your allocation before claims open' },
            { date: 'Apr 21', label: 'Claims Open', status: 'upcoming' as const, detail: 'Opt-in to CORTEX ASA and claim tokens' },
            { date: 'Jul 1', label: 'Claim Deadline', status: 'upcoming' as const, detail: 'Unclaimed tokens return to treasury' },
          ].map((event, i) => (
            <div key={i} className="flex gap-4 sm:gap-6">
              <div className="flex flex-col items-center">
                <div className={`w-3 h-3 rounded-full border-2 ${
                  event.status === 'upcoming' ? 'border-gray-600 bg-transparent' : 'border-[#007AFF] bg-[#007AFF]'
                }`} />
                {i < 6 && <div className="w-[2px] h-12 sm:h-14 bg-white/5" />}
              </div>
              <div className="pb-6 sm:pb-8 -mt-1">
                <p className="text-[10px] font-bold text-[#007AFF] uppercase tracking-widest">{event.date}</p>
                <p className="text-sm font-bold mt-0.5">{event.label}</p>
                <p className="text-xs text-gray-500 mt-0.5">{event.detail}</p>
              </div>
            </div>
          ))}
        </div>
      </div>

      {/* Learn More */}
      <div
        style={{ animation: 'fadeInUp 0.5s ease-out 0.3s both' }}
        className="grid sm:grid-cols-2 gap-4"
      >
        <a
          href="https://x.com/purecortexai"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-4 bg-[#1A1A1A] border border-white/5 rounded-2xl p-5 hover:border-[#007AFF]/30 transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
            <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current text-gray-400 group-hover:text-[#007AFF] transition-colors">
              <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
            </svg>
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold">Follow @purecortexai</p>
            <p className="text-xs text-gray-500">Qualify for the social campaign tier</p>
          </div>
          <ExternalLink className="w-4 h-4 text-gray-600 group-hover:text-[#007AFF] transition-colors" />
        </a>

        <Link
          href="/docs/api"
          className="flex items-center gap-4 bg-[#1A1A1A] border border-white/5 rounded-2xl p-5 hover:border-[#007AFF]/30 transition-all group"
        >
          <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center flex-shrink-0">
            <Code2 className="w-5 h-5 text-gray-400 group-hover:text-[#007AFF] transition-colors" />
          </div>
          <div className="flex-1">
            <p className="text-sm font-bold">Build on PureCortex</p>
            <p className="text-xs text-gray-500">Qualify for the developer builder tier</p>
          </div>
          <ChevronRight className="w-4 h-4 text-gray-600 group-hover:text-[#007AFF] transition-colors" />
        </Link>
      </div>

      {/* Wallet Connect Modal */}
      <AnimatePresence>
        {walletModalOpen && (
          <div className="fixed inset-0 z-[200] flex items-end sm:items-center justify-center sm:p-6">
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setWalletModalOpen(false)}
              className="absolute inset-0 bg-black/80 backdrop-blur-sm"
            />
            <motion.div
              initial={{ y: '100%', opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              exit={{ y: '100%', opacity: 0 }}
              transition={{ type: 'spring', damping: 30, stiffness: 300 }}
              className="bg-[#121217] border border-white/10 rounded-t-3xl sm:rounded-3xl p-6 sm:p-8 max-w-md w-full relative shadow-2xl z-[201]"
            >
              <h2 className="text-xl font-black tracking-tighter uppercase italic mb-2">Connect Wallet</h2>
              <p className="text-gray-500 text-xs mb-5 font-bold uppercase tracking-widest">Register for the Genesis Airdrop</p>
              <div className="space-y-2">
                {wallets?.map((wallet) => {
                  const isConnecting = connecting === wallet.id;
                  const rawIcon = wallet.metadata?.icon;
                  const iconUrl = rawIcon && (rawIcon.startsWith('https://') || rawIcon.startsWith('data:image/')) ? rawIcon : undefined;
                  return (
                    <button
                      key={wallet.id}
                      onClick={() => handleConnect(wallet.id)}
                      disabled={isConnecting}
                      className="w-full flex items-center gap-4 p-4 rounded-xl bg-[#050505] border border-white/5 hover:border-[#007AFF]/40 transition-all disabled:opacity-50"
                    >
                      <div className="w-10 h-10 rounded-xl bg-white/5 flex items-center justify-center">
                        {iconUrl ? (
                          <Image
                            src={iconUrl}
                            alt={wallet.metadata?.name || wallet.id}
                            width={28}
                            height={28}
                            unoptimized
                            className="w-7 h-7 object-contain"
                          />
                        ) : (
                          <Wallet className="w-5 h-5 text-gray-400" />
                        )}
                      </div>
                      <span className="text-sm font-bold uppercase tracking-wider">{wallet.metadata?.name || wallet.id}</span>
                      {isConnecting && (
                        <span className="ml-auto text-[10px] text-[#007AFF] font-mono uppercase animate-pulse">Connecting...</span>
                      )}
                    </button>
                  );
                })}
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
