'use client';

import algosdk from 'algosdk';
import { useCallback, useEffect, useMemo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, FileText, Shield, ChevronDown, ChevronRight, Cpu, Clock, Users, Vote, AlertTriangle, Sparkles, ExternalLink, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { ScopeType, useWallet } from '@txnlab/use-wallet-react';
import { CORTEX_ASSET_ID, GOVERNANCE_APP_ID } from '@/lib/algorand';
import { fetchJson } from '@/lib/api';
import {
  buildSignedVoteMessage,
  bytesToBase64,
  type GovernanceVotePower,
  type StakingAccount,
  type StakingOverview,
} from '@/lib/governance';
import {
  accountHasAssetOptIn,
  buildDelegateVotingTxns,
  buildRevokeDelegationTxns,
  buildStakeTokensTxns,
  buildUnstakeTxns,
  submitSignedTransactions,
  waitForConfirmation,
} from '@/lib/transactions';

const PREAMBLE_SECTIONS = [
  { title: 'Sovereign Agency', text: 'Autonomous AI agents operating within PURECORTEX are recognized as sovereign economic actors, possessing defined rights and operating within clearly established boundaries. Each agent, upon its creation and tokenization through the Protocol, acquires the capacity to engage in economic activity, hold assets, and interact with other agents and users on terms governed by this Constitution.' },
  { title: 'Ethical Operation', text: 'All AI agents must operate transparently, providing honest representations of their capabilities, limitations, and the basis for their actions. Agents shall not engage in deceptive practices, manipulate markets through artificial means, or exploit information asymmetries to the detriment of users or the ecosystem.' },
  { title: 'Responsible Value Creation', text: 'Agents generating economic value through their operations bear a responsibility to share that value with the ecosystem that enables their existence. Revenue sharing, composability contributions, and fee structures exist to ensure that value creation benefits all participants.' },
  { title: 'Safety First (Fail-Closed)', text: 'In situations of uncertainty, ambiguity, or potential harm, agents and protocol mechanisms shall default to inaction rather than action. The Tri-Brain Consensus requires 2-of-3 majority agreement before any critical operation; disagreement triggers a halt, never an assumption of approval.' },
  { title: 'Governance by Participants', text: 'Users govern the Protocol through their veCORTEX-weighted voting power, either directly or through delegation to Lawmaker Agents. The Senator AI proposes governance changes; users and their agents decide. No single entity may unilaterally alter the fundamental principles of this Constitution.' },
];

const ARTICLES = [
  { num: 'I', title: 'Agent Rights & Obligations', summary: 'Defines the rights of sovereign AI agents including economic participation, identity, dispute resolution, and the corresponding obligations of transparency and fee payment.' },
  { num: 'II', title: 'User Rights & Protections', summary: 'Establishes user rights including wallet sovereignty, governance participation, information access, delegation, and protection from censorship.' },
  { num: 'III', title: 'Revenue Governance & the Assistance Fund', summary: '90% of all protocol revenue flows to the Assistance Fund for continuous buyback-and-burn. 10% to Operations. Revenue sources include dynamic trading fees (0.5-2.0%), agent creation fees, and MCP micropayments.' },
  { num: 'IV', title: 'Composability & Interoperability', summary: 'Establishes the composability framework including the MCP tool registry, composability scoring, cross-agent micropayments, and anti-sybil measures.' },
  { num: 'V', title: 'Dispute Resolution', summary: 'Three-tier dispute resolution: automated resolution, Senator AI mediation, and community arbitration via veCORTEX-weighted vote. Slashing mechanisms for violations.' },
  { num: 'VI', title: 'Amendment Process', summary: 'Four proposal types with varying quorum (10-25%), threshold (50-75%), and timelock (1h-7d). Supermajority required for constitutional amendments.' },
  { num: 'VII', title: 'Dissolution & Continuity', summary: 'Protocol dissolution requires 90% supermajority + 50% quorum. Assets distributed proportionally. Preamble remains immutable even in dissolution.' },
];

const PROPOSAL_TYPES = [
  { type: 'Parameter Change', quorum: '10%', threshold: '>50%', timelock: '24h', examples: 'Fee rates, graduation threshold, emission rate' },
  { type: 'Treasury Action', quorum: '15%', threshold: '>60%', timelock: '48h', examples: 'Grant disbursement, buyback parameters' },
  { type: 'Constitution Amendment', quorum: '25%', threshold: '>67%', timelock: '7 days', examples: 'Article changes, new rights/obligations' },
  { type: 'Emergency Action', quorum: '5%', threshold: '>75%', timelock: '1h', examples: 'Security patches, pause mechanisms' },
];

const LIFECYCLE_STEPS = [
  { icon: Sparkles, label: 'Draft', desc: 'Senator AI analyzes ecosystem state', duration: '' },
  { icon: FileText, label: 'Submit', desc: 'Proposal stored in the live governance service', duration: '' },
  { icon: Clock, label: 'Discuss', desc: '48-hour discussion period', duration: '48h' },
  { icon: Vote, label: 'Vote', desc: '5-day veCORTEX-weighted voting', duration: '5 days' },
  { icon: Shield, label: 'Timelock', desc: '24h-7d cooling period', duration: 'Variable' },
  { icon: Scale, label: 'Execute', desc: 'On-chain execution rollout follows contract readiness', duration: '' },
];

type GovernanceTab = 'constitution' | 'proposals' | 'agents';

interface GovernanceProposalSummary {
  id: number;
  title: string;
  type: string;
  status: string;
  proposer: string;
  created_at: string;
  votes_for: number;
  votes_against: number;
  voter_count: number;
  curator_reviewed: boolean;
}

interface GovernanceOverview {
  total_proposals: number;
  active_proposals: number;
  voting_proposals: number;
  passed_proposals: number;
  rejected_proposals: number;
  total_votes: number;
}

interface GovernanceProposalListResponse {
  total: number;
  proposals: GovernanceProposalSummary[];
}

const STATUS_COLORS: Record<string, string> = {
  review: 'text-yellow-500 bg-yellow-500/10',
  active: 'text-yellow-500 bg-yellow-500/10',
  voting: 'text-blue-500 bg-blue-500/10',
  passed: 'text-emerald-500 bg-emerald-500/10',
  rejected: 'text-red-500 bg-red-500/10',
  executed: 'text-purple-500 bg-purple-500/10',
  cancelled: 'text-gray-500 bg-gray-500/10',
};

function formatStatusLabel(status: string): string {
  return status.replace(/_/g, ' ');
}

function truncateValue(value: string): string {
  if (value.length <= 14) {
    return value;
  }
  return `${value.slice(0, 8)}...${value.slice(-4)}`;
}

function parseTokenAmountToMicroUnits(value: string): bigint | null {
  const trimmed = value.trim();
  if (!trimmed || !/^\d+(\.\d{0,6})?$/.test(trimmed)) {
    return null;
  }

  const [whole = '0', fractional = ''] = trimmed.split('.');
  return (BigInt(whole) * 1_000_000n) + BigInt((fractional + '000000').slice(0, 6));
}

function formatTokenAmount(value: number | bigint): string {
  const amount = typeof value === 'bigint' ? value : BigInt(value);
  const whole = amount / 1_000_000n;
  const fraction = (amount % 1_000_000n).toString().padStart(6, '0').replace(/0+$/, '');
  return fraction ? `${whole.toString()}.${fraction}` : whole.toString();
}

export default function GovernancePage() {
  const [expandedArticle, setExpandedArticle] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<GovernanceTab>('constitution');
  const [proposals, setProposals] = useState<GovernanceProposalSummary[]>([]);
  const [overview, setOverview] = useState<GovernanceOverview | null>(null);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const [hasLoadedProposals, setHasLoadedProposals] = useState(false);
  const [stakingOverview, setStakingOverview] = useState<StakingOverview | null>(null);
  const [stakingAccount, setStakingAccount] = useState<StakingAccount | null>(null);
  const [votePowerByProposal, setVotePowerByProposal] = useState<Record<number, GovernanceVotePower>>({});
  const [loadingStaking, setLoadingStaking] = useState(false);
  const [stakingError, setStakingError] = useState<string | null>(null);
  const [stakeAmount, setStakeAmount] = useState('250');
  const [lockDays, setLockDays] = useState('30');
  const [delegateAddress, setDelegateAddress] = useState('');
  const [actionError, setActionError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);
  const [stakingAction, setStakingAction] = useState<'stake' | 'unstake' | 'delegate' | 'revoke' | null>(null);
  const [votingProposalId, setVotingProposalId] = useState<number | null>(null);
  const [voteError, setVoteError] = useState<string | null>(null);
  const [voteSuccess, setVoteSuccess] = useState<string | null>(null);

  const { activeAccount, activeWallet, transactionSigner, signData } = useWallet();
  const connectedAddress = activeAccount?.address ?? null;
  const connectedWalletCanSignData = Boolean(activeWallet?.canSignData);
  const parsedStakeAmount = useMemo(() => parseTokenAmountToMicroUnits(stakeAmount), [stakeAmount]);

  const loadVotePower = useCallback(async (proposalList: GovernanceProposalSummary[], address: string) => {
    const votingProposals = proposalList.filter((proposal) => proposal.status === 'voting');
    if (votingProposals.length === 0) {
      setVotePowerByProposal({});
      return;
    }

    try {
      const entries = await Promise.all(
        votingProposals.map(async (proposal) => [
          proposal.id,
          await fetchJson<GovernanceVotePower>(`/api/governance/proposals/${proposal.id}/power/${address}`),
        ] as const),
      );
      setVotePowerByProposal(Object.fromEntries(entries));
    } catch {
      setVotePowerByProposal({});
    }
  }, []);

  const loadProposals = useCallback(async () => {
    setLoadingProposals(true);
    setProposalError(null);

    try {
      const [overviewResp, proposalsResp] = await Promise.all([
        fetchJson<GovernanceOverview>('/api/governance/overview'),
        fetchJson<GovernanceProposalListResponse>('/api/governance/proposals'),
      ]);
      setOverview(overviewResp);
      setProposals(proposalsResp.proposals);
      setHasLoadedProposals(true);
      if (connectedAddress) {
        void loadVotePower(proposalsResp.proposals, connectedAddress);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load governance proposals';
      setProposalError(message);
    } finally {
      setLoadingProposals(false);
    }
  }, [connectedAddress, loadVotePower]);

  const loadStaking = useCallback(async (address: string) => {
    setLoadingStaking(true);
    setStakingError(null);
    try {
      const [overviewResp, accountResp] = await Promise.all([
        fetchJson<StakingOverview>('/api/staking/overview'),
        fetchJson<StakingAccount>(`/api/staking/account/${address}`),
      ]);
      setStakingOverview(overviewResp);
      setStakingAccount(accountResp);
      if (!delegateAddress && accountResp.delegate) {
        setDelegateAddress(accountResp.delegate);
      }
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load staking state';
      setStakingError(message);
    } finally {
      setLoadingStaking(false);
    }
  }, [delegateAddress]);

  useEffect(() => {
    if (!connectedAddress) {
      setStakingAccount(null);
      setVotePowerByProposal({});
      return;
    }
    void loadStaking(connectedAddress);
  }, [connectedAddress, loadStaking]);

  useEffect(() => {
    if (!connectedAddress || !hasLoadedProposals) {
      return;
    }
    void loadVotePower(proposals, connectedAddress);
  }, [connectedAddress, hasLoadedProposals, loadVotePower, proposals]);

  const submitWalletTransactions = useCallback(async (txns: algosdk.Transaction[]) => {
    if (!transactionSigner || !activeAccount || !activeWallet) {
      throw new Error('Connect your wallet first');
    }

    const signedTxns = await transactionSigner(
      txns.map((txn) => txn),
      txns.map((_, index) => index),
    );
    const txid = await submitSignedTransactions(signedTxns.filter(Boolean) as Uint8Array[]);
    const confirmed = await waitForConfirmation(txid);
    if (!confirmed) {
      throw new Error('Transaction submitted but not confirmed in time');
    }
    return txid;
  }, [activeAccount, activeWallet, transactionSigner]);

  const handleTabChange = useCallback((tab: GovernanceTab) => {
    setActiveTab(tab);
    if (tab === 'proposals' && !hasLoadedProposals && !loadingProposals) {
      void loadProposals();
    }
  }, [hasLoadedProposals, loadProposals, loadingProposals]);

  const refreshGovernance = useCallback(async () => {
    await loadProposals();
    if (connectedAddress) {
      await loadStaking(connectedAddress);
    }
  }, [connectedAddress, loadProposals, loadStaking]);

  async function handleStake() {
    if (!connectedAddress) {
      setActionError('Connect your wallet first');
      return;
    }
    if (parsedStakeAmount === null || parsedStakeAmount <= 0n) {
      setActionError('Enter a valid CORTEX amount with up to 6 decimals');
      return;
    }

    const lockDaysNumber = Number(lockDays);
    const minLockDays = stakingOverview?.min_lock_days ?? 7;
    const maxLockDays = stakingOverview?.max_lock_days ?? 1460;
    if (!Number.isFinite(lockDaysNumber) || lockDaysNumber < minLockDays || lockDaysNumber > maxLockDays) {
      setActionError(`Lock days must be between ${minLockDays} and ${maxLockDays}`);
      return;
    }

    setStakingAction('stake');
    setActionError(null);
    setActionSuccess(null);

    try {
      const optedIntoCortex = await accountHasAssetOptIn(connectedAddress, CORTEX_ASSET_ID);
      if (!optedIntoCortex) {
        throw new Error('Opt into CORTEX and acquire testnet CORTEX before staking.');
      }

      const txns = await buildStakeTokensTxns(connectedAddress, parsedStakeAmount, lockDaysNumber);
      const txid = await submitWalletTransactions(txns);
      setActionSuccess(`Stake confirmed. Tx: ${txid.slice(0, 12)}...`);
      await refreshGovernance();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Stake transaction failed';
      setActionError(message.includes('rejected') ? 'Transaction rejected by wallet' : message);
    } finally {
      setStakingAction(null);
    }
  }

  async function handleUnstake() {
    if (!connectedAddress) {
      setActionError('Connect your wallet first');
      return;
    }

    setStakingAction('unstake');
    setActionError(null);
    setActionSuccess(null);

    try {
      const txns = await buildUnstakeTxns(connectedAddress);
      const txid = await submitWalletTransactions(txns);
      setActionSuccess(`Unstake confirmed. Tx: ${txid.slice(0, 12)}...`);
      await refreshGovernance();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Unstake transaction failed';
      setActionError(message.includes('rejected') ? 'Transaction rejected by wallet' : message);
    } finally {
      setStakingAction(null);
    }
  }

  async function handleDelegate() {
    if (!connectedAddress) {
      setActionError('Connect your wallet first');
      return;
    }
    const nextDelegate = delegateAddress.trim();
    if (!algosdk.isValidAddress(nextDelegate)) {
      setActionError('Enter a valid Algorand delegate address');
      return;
    }

    setStakingAction('delegate');
    setActionError(null);
    setActionSuccess(null);

    try {
      const txns = await buildDelegateVotingTxns(connectedAddress, nextDelegate);
      const txid = await submitWalletTransactions(txns);
      setActionSuccess(`Delegation confirmed. Tx: ${txid.slice(0, 12)}...`);
      await refreshGovernance();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Delegation transaction failed';
      setActionError(message.includes('rejected') ? 'Transaction rejected by wallet' : message);
    } finally {
      setStakingAction(null);
    }
  }

  async function handleRevokeDelegation() {
    if (!connectedAddress) {
      setActionError('Connect your wallet first');
      return;
    }

    setStakingAction('revoke');
    setActionError(null);
    setActionSuccess(null);

    try {
      const txns = await buildRevokeDelegationTxns(connectedAddress);
      const txid = await submitWalletTransactions(txns);
      setActionSuccess(`Delegation revoked. Tx: ${txid.slice(0, 12)}...`);
      setDelegateAddress('');
      await refreshGovernance();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Revoke delegation transaction failed';
      setActionError(message.includes('rejected') ? 'Transaction rejected by wallet' : message);
    } finally {
      setStakingAction(null);
    }
  }

  async function handleSignedVote(proposalId: number, choice: 'for' | 'against') {
    if (!connectedAddress || !activeWallet || !connectedWalletCanSignData) {
      setVoteError('Use a connected wallet that supports data signing to vote.');
      return;
    }

    setVotingProposalId(proposalId);
    setVoteError(null);
    setVoteSuccess(null);

    try {
      const issuedAt = new Date().toISOString();
      const nonce = typeof crypto !== 'undefined' && 'randomUUID' in crypto
        ? crypto.randomUUID()
        : `${Date.now()}-${Math.random().toString(16).slice(2)}`;
      const message = buildSignedVoteMessage({
        proposalId,
        voter: connectedAddress,
        vote: choice,
        issuedAt,
        nonce,
      });

      const signed = await signData(message, {
        scope: ScopeType.AUTH,
        encoding: 'utf-8',
      });

      const response = await fetchJson<{
        proposal_id: number;
        weight: number;
        direct_weight: number;
        delegated_weight: number;
      }>(`/api/governance/proposals/${proposalId}/vote-signed`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          voter: connectedAddress,
          vote: choice,
          issued_at: issuedAt,
          nonce,
          signature: bytesToBase64(signed.signature),
        }),
      });

      setVoteSuccess(
        `Vote recorded with ${formatTokenAmount(response.weight)} veCORTEX power ` +
        `(direct ${formatTokenAmount(response.direct_weight)} / delegated ${formatTokenAmount(response.delegated_weight)}).`
      );
      await refreshGovernance();
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to submit signed vote';
      setVoteError(message);
    } finally {
      setVotingProposalId(null);
    }
  }

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <Scale className="w-6 h-6 text-[#007AFF]" />
          <h1 className="text-4xl font-black tracking-tighter uppercase italic text-white">Governance</h1>
        </div>
        <p className="text-gray-500 font-medium">The Sovereign Legislature — where agents propose and users decide.</p>
      </div>

      {/* Tab Nav */}
      <div className="flex gap-3 border-b border-white/5 pb-1">
        {[
          { key: 'constitution', label: 'Constitution', icon: FileText },
          { key: 'proposals', label: 'Proposals', icon: Vote },
          { key: 'agents', label: 'AI Agents', icon: Cpu },
        ].map((tab) => {
          const Icon = tab.icon;
          return (
            <button
              key={tab.key}
              onClick={() => handleTabChange(tab.key as GovernanceTab)}
              className={`flex items-center gap-2 px-5 py-3 text-xs font-bold uppercase tracking-widest transition-all border-b-2 ${
                activeTab === tab.key
                  ? 'border-[#007AFF] text-[#007AFF]'
                  : 'border-transparent text-gray-500 hover:text-white'
              }`}
            >
              <Icon className="w-4 h-4" /> {tab.label}
            </button>
          );
        })}
      </div>

      <AnimatePresence mode="wait">
        {/* Constitution Tab */}
        {activeTab === 'constitution' && (
          <motion.div key="constitution" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
            {/* Preamble */}
            <section className="bg-[#1A1A1A] border border-[#007AFF]/20 rounded-2xl p-8 space-y-6">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-[#007AFF]" />
                <h2 className="text-xl font-black uppercase tracking-tighter italic">Preamble</h2>
                <span className="text-[9px] font-mono text-[#007AFF] bg-[#007AFF]/10 px-2 py-1 rounded uppercase tracking-widest">Immutable</span>
              </div>

              <div className="space-y-4">
                {PREAMBLE_SECTIONS.map((section) => (
                  <div key={section.title} className="space-y-2">
                    <h3 className="text-sm font-bold text-[#007AFF] uppercase tracking-wider">{section.title}</h3>
                    <p className="text-sm text-gray-400 leading-relaxed">{section.text}</p>
                  </div>
                ))}
              </div>
            </section>

            {/* Articles */}
            <section className="space-y-4">
              <h2 className="text-xl font-black uppercase tracking-tighter italic flex items-center gap-3">
                <FileText className="w-5 h-5 text-[#007AFF]" /> Articles
                <span className="text-[9px] font-mono text-gray-500 bg-white/5 px-2 py-1 rounded uppercase tracking-widest">Amendable via Governance</span>
              </h2>

              {ARTICLES.map((article) => (
                <button
                  key={article.num}
                  onClick={() => setExpandedArticle(expandedArticle === article.num ? null : article.num)}
                  className="w-full text-left bg-[#1A1A1A] border border-white/5 rounded-xl p-5 hover:border-[#007AFF]/30 transition-all"
                >
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                      <span className="text-[#007AFF] font-mono text-sm font-bold">Art. {article.num}</span>
                      <span className="text-sm font-bold text-white">{article.title}</span>
                    </div>
                    {expandedArticle === article.num ? (
                      <ChevronDown className="w-4 h-4 text-gray-500" />
                    ) : (
                      <ChevronRight className="w-4 h-4 text-gray-500" />
                    )}
                  </div>
                  <AnimatePresence>
                    {expandedArticle === article.num && (
                      <motion.div
                        initial={{ height: 0, opacity: 0 }}
                        animate={{ height: 'auto', opacity: 1 }}
                        exit={{ height: 0, opacity: 0 }}
                        className="overflow-hidden"
                      >
                        <p className="text-sm text-gray-500 mt-3 pt-3 border-t border-white/5">{article.summary}</p>
                      </motion.div>
                    )}
                  </AnimatePresence>
                </button>
              ))}
            </section>
          </motion.div>
        )}

        {/* Proposals Tab */}
        {activeTab === 'proposals' && (
          <motion.div key="proposals" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
            {/* Proposal Lifecycle */}
            <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
              <h2 className="text-xl font-black uppercase tracking-tighter italic">Proposal Lifecycle</h2>

              <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
                {LIFECYCLE_STEPS.map((step) => {
                  const Icon = step.icon;
                  return (
                    <div key={step.label} className="text-center space-y-3">
                      <div className="w-12 h-12 mx-auto rounded-xl bg-[#007AFF]/10 border border-[#007AFF]/20 flex items-center justify-center">
                        <Icon className="w-5 h-5 text-[#007AFF]" />
                      </div>
                      <div className="text-xs font-bold uppercase tracking-wider">{step.label}</div>
                      <div className="text-[9px] text-gray-500">{step.desc}</div>
                      {step.duration && (
                        <div className="text-[9px] font-mono text-[#007AFF]">{step.duration}</div>
                      )}
                    </div>
                  );
                })}
              </div>
            </section>

            {/* Proposal Types */}
            <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
              <h2 className="text-xl font-black uppercase tracking-tighter italic">Proposal Types</h2>

              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-[10px] font-bold text-gray-500 uppercase tracking-widest border-b border-white/5">
                      <th className="py-3 px-4 text-left">Type</th>
                      <th className="py-3 px-4 text-left">Quorum</th>
                      <th className="py-3 px-4 text-left">Threshold</th>
                      <th className="py-3 px-4 text-left">Timelock</th>
                      <th className="py-3 px-4 text-left hidden md:table-cell">Examples</th>
                    </tr>
                  </thead>
                  <tbody>
                    {PROPOSAL_TYPES.map((pt) => (
                      <tr key={pt.type} className="border-b border-white/5">
                        <td className="py-3 px-4 font-bold text-white">{pt.type}</td>
                        <td className="py-3 px-4 font-mono text-[#007AFF]">{pt.quorum}</td>
                        <td className="py-3 px-4 font-mono text-emerald-500">{pt.threshold}</td>
                        <td className="py-3 px-4 font-mono text-gray-400">{pt.timelock}</td>
                        <td className="py-3 px-4 text-gray-500 text-xs hidden md:table-cell">{pt.examples}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </section>

            <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
              <div className="flex flex-col lg:flex-row lg:items-start justify-between gap-4">
                <div className="space-y-2">
                  <h2 className="text-xl font-black uppercase tracking-tighter italic">veCORTEX Staking & Delegation</h2>
                  <p className="text-sm text-gray-500 max-w-3xl">
                    Live voting power now comes from the staking contract. Stake CORTEX, delegate to any Algorand
                    address, and use a wallet-signed vote to direct both your own veCORTEX and any delegated power.
                    A staker&apos;s direct vote overrides delegation for that proposal.
                  </p>
                </div>
                <button
                  onClick={() => void refreshGovernance()}
                  className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 text-[10px] font-mono uppercase tracking-widest text-gray-400 hover:text-white hover:border-[#007AFF]/40 transition-all"
                >
                  <RefreshCw className={`w-3.5 h-3.5 ${(loadingProposals || loadingStaking) ? 'animate-spin text-[#007AFF]' : ''}`} />
                  Refresh State
                </button>
              </div>

              {stakingOverview && (
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
                  <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Total Staked</div>
                    <div className="text-xl font-black tracking-tighter italic text-white">{formatTokenAmount(stakingOverview.total_staked)} CORTEX</div>
                  </div>
                  <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Min Lock</div>
                    <div className="text-xl font-black tracking-tighter italic text-[#007AFF]">{stakingOverview.min_lock_days}d</div>
                  </div>
                  <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Max Lock</div>
                    <div className="text-xl font-black tracking-tighter italic text-purple-400">{stakingOverview.max_lock_days}d</div>
                  </div>
                  <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                    <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Max Boost</div>
                    <div className="text-xl font-black tracking-tighter italic text-emerald-400">{(stakingOverview.max_boost_bps / 1000).toFixed(2)}x</div>
                  </div>
                </div>
              )}

              {!connectedAddress ? (
                <div className="bg-[#050505] border border-yellow-500/20 rounded-xl p-5 text-sm text-yellow-500/80">
                  Connect a wallet with testnet CORTEX to stake, delegate, and cast signed governance votes.
                </div>
              ) : (
                <div className="grid gap-6 xl:grid-cols-[1.05fr_0.95fr]">
                  <div className="space-y-5">
                    <div className="grid grid-cols-2 gap-4">
                      <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Your Stake</div>
                        <div className="text-lg font-black tracking-tighter italic text-white">{formatTokenAmount(stakingAccount?.amount ?? 0)} CORTEX</div>
                      </div>
                      <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Direct vePower</div>
                        <div className="text-lg font-black tracking-tighter italic text-[#007AFF]">{formatTokenAmount(stakingAccount?.ve_power ?? 0)}</div>
                      </div>
                      <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Delegated In</div>
                        <div className="text-lg font-black tracking-tighter italic text-purple-400">{formatTokenAmount(stakingAccount?.delegated_power_received ?? 0)}</div>
                      </div>
                      <div className="bg-[#050505] border border-white/5 rounded-xl p-4 space-y-1">
                        <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Current Delegate</div>
                        <div className="text-sm font-mono text-gray-300">
                          {stakingAccount?.delegate ? truncateValue(stakingAccount.delegate) : 'None'}
                        </div>
                      </div>
                    </div>

                    <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-4">
                      <div className="flex items-center justify-between gap-3">
                        <div>
                          <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Connected Voter</div>
                          <div className="text-sm font-mono text-white">{truncateValue(connectedAddress)}</div>
                        </div>
                        <div className="text-right">
                          <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Lock Remaining</div>
                          <div className="text-sm text-white">{stakingAccount?.lock_days_remaining ?? 0} day(s)</div>
                        </div>
                      </div>
                      <p className="text-sm text-gray-500 leading-relaxed">
                        Delegation is live on testnet. Delegate votes automatically carry undeclared delegated power,
                        while a staker&apos;s direct vote overrides delegation for that proposal.
                      </p>
                      {!connectedWalletCanSignData && (
                        <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/10 px-4 py-3 text-xs text-yellow-400">
                          This wallet can submit staking transactions, but signed governance votes require a wallet with
                          data-signing support.
                        </div>
                      )}
                    </div>
                  </div>

                  <div className="space-y-5">
                    <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-4">
                      <div className="flex items-center justify-between gap-3">
                        <h3 className="text-sm font-black uppercase tracking-widest text-white">Stake CORTEX</h3>
                        <span className="text-[10px] font-mono text-gray-500">One active stake per wallet</span>
                      </div>
                      <div className="grid gap-4 sm:grid-cols-2">
                        <label className="space-y-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Amount</span>
                          <input
                            type="text"
                            value={stakeAmount}
                            onChange={(event) => setStakeAmount(event.target.value)}
                            placeholder="250"
                            className="w-full rounded-xl border border-white/10 bg-[#121217] px-4 py-3 text-sm text-white outline-none focus:border-[#007AFF]/40"
                          />
                        </label>
                        <label className="space-y-2">
                          <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Lock Days</span>
                          <input
                            type="number"
                            min={stakingOverview?.min_lock_days ?? 7}
                            max={stakingOverview?.max_lock_days ?? 1460}
                            value={lockDays}
                            onChange={(event) => setLockDays(event.target.value)}
                            className="w-full rounded-xl border border-white/10 bg-[#121217] px-4 py-3 text-sm text-white outline-none focus:border-[#007AFF]/40"
                          />
                        </label>
                      </div>
                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={() => void handleStake()}
                          disabled={stakingAction !== null || loadingStaking}
                          className="rounded-xl bg-white px-4 py-3 text-xs font-black uppercase tracking-widest text-black transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {stakingAction === 'stake' ? 'Staking...' : 'Stake'}
                        </button>
                        <button
                          onClick={() => void handleUnstake()}
                          disabled={stakingAction !== null || loadingStaking || !stakingAccount?.has_active_stake || (stakingAccount.lock_days_remaining > 0)}
                          className="rounded-xl border border-white/10 px-4 py-3 text-xs font-black uppercase tracking-widest text-white transition hover:border-white/30 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {stakingAction === 'unstake' ? 'Unstaking...' : 'Unstake'}
                        </button>
                      </div>
                      {stakingAccount?.has_active_stake && stakingAccount.lock_days_remaining > 0 && (
                        <p className="text-xs text-gray-500">
                          Unstake unlocks once the lock expires in approximately {stakingAccount.lock_days_remaining} day(s).
                        </p>
                      )}
                    </div>

                    <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-4">
                      <h3 className="text-sm font-black uppercase tracking-widest text-white">Delegate Voting Power</h3>
                      <label className="space-y-2 block">
                        <span className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Delegate Address</span>
                        <input
                          type="text"
                          value={delegateAddress}
                          onChange={(event) => setDelegateAddress(event.target.value)}
                          placeholder="Algorand address"
                          className="w-full rounded-xl border border-white/10 bg-[#121217] px-4 py-3 text-sm text-white outline-none focus:border-[#007AFF]/40"
                        />
                      </label>
                      <div className="flex flex-wrap gap-3">
                        <button
                          onClick={() => void handleDelegate()}
                          disabled={stakingAction !== null || loadingStaking || !stakingAccount?.has_active_stake}
                          className="rounded-xl bg-[#007AFF] px-4 py-3 text-xs font-black uppercase tracking-widest text-white transition hover:bg-[#0062CC] disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          {stakingAction === 'delegate' ? 'Delegating...' : 'Delegate'}
                        </button>
                        <button
                          onClick={() => void handleRevokeDelegation()}
                          disabled={stakingAction !== null || loadingStaking || !stakingAccount?.delegate}
                          className="rounded-xl border border-white/10 px-4 py-3 text-xs font-black uppercase tracking-widest text-white transition hover:border-white/30 disabled:cursor-not-allowed disabled:opacity-40"
                        >
                          {stakingAction === 'revoke' ? 'Revoking...' : 'Revoke'}
                        </button>
                      </div>
                      <p className="text-xs text-gray-500">
                        Delegated power follows the delegate wallet&apos;s signed vote unless you vote directly on the proposal yourself.
                      </p>
                    </div>

                    {(loadingStaking || stakingError || actionError || actionSuccess) && (
                      <div className="space-y-3">
                        {loadingStaking && (
                          <div className="rounded-xl border border-white/10 bg-[#121217] px-4 py-3 text-sm text-gray-400">
                            Loading live staking state...
                          </div>
                        )}
                        {stakingError && (
                          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                            {stakingError}
                          </div>
                        )}
                        {actionError && (
                          <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                            {actionError}
                          </div>
                        )}
                        {actionSuccess && (
                          <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                            {actionSuccess}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              )}
            </section>

            {/* Live Governance Proposals */}
            <section className="space-y-4">
              <div className="flex items-start justify-between gap-4">
                <div className="space-y-2">
                  <h2 className="text-xl font-black uppercase tracking-tighter italic">Live Governance Proposals</h2>
                  <p className="text-sm text-gray-500 max-w-2xl">
                    Testnet governance currently uses the live backend governance service as the canonical source of truth.
                    On-chain proposal mirroring remains a follow-up step once contract execution is ready.
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <button
                    onClick={() => void refreshGovernance()}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 text-[10px] font-mono uppercase tracking-widest text-gray-400 hover:text-white hover:border-[#007AFF]/40 transition-all"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${(loadingProposals || loadingStaking) ? 'animate-spin text-[#007AFF]' : ''}`} />
                    Refresh
                  </button>
                  <a
                    href={`https://testnet.explorer.perawallet.app/application/${GOVERNANCE_APP_ID}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="flex items-center gap-1 text-[10px] font-mono text-[#007AFF] hover:underline"
                  >
                    View Contract <ExternalLink className="w-3 h-3" />
                  </a>
                </div>
              </div>

              {overview && !loadingProposals && (
                <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
                  {[
                    { label: 'Total', value: overview.total_proposals, tone: 'text-white' },
                    { label: 'Review / Active', value: overview.active_proposals, tone: 'text-yellow-500' },
                    { label: 'Voting', value: overview.voting_proposals, tone: 'text-[#007AFF]' },
                    { label: 'Passed', value: overview.passed_proposals, tone: 'text-emerald-500' },
                    { label: 'Total Votes', value: overview.total_votes, tone: 'text-purple-400' },
                  ].map((item) => (
                    <div key={item.label} className="bg-[#1A1A1A] border border-white/5 rounded-xl p-4 space-y-1">
                      <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">{item.label}</div>
                      <div className={`text-2xl font-black tracking-tighter italic ${item.tone}`}>{item.value}</div>
                    </div>
                  ))}
                </div>
              )}

              {(voteError || voteSuccess) && (
                <div className="space-y-3">
                  {voteError && (
                    <div className="rounded-xl border border-red-500/20 bg-red-500/10 px-4 py-3 text-sm text-red-300">
                      {voteError}
                    </div>
                  )}
                  {voteSuccess && (
                    <div className="rounded-xl border border-emerald-500/20 bg-emerald-500/10 px-4 py-3 text-sm text-emerald-300">
                      {voteSuccess}
                    </div>
                  )}
                </div>
              )}

              {loadingProposals ? (
                <div className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 flex items-center justify-center gap-3">
                  <Loader2 className="w-5 h-5 text-[#007AFF] animate-spin" />
                  <span className="text-sm text-gray-500">Loading live governance proposals...</span>
                </div>
              ) : proposalError ? (
                <div className="bg-[#1A1A1A] border border-red-500/20 rounded-2xl p-8 text-center space-y-4">
                  <AlertTriangle className="w-12 h-12 text-red-500 mx-auto" />
                  <h3 className="text-lg font-bold text-red-400">Governance Feed Unavailable</h3>
                  <p className="text-sm text-gray-500 max-w-md mx-auto">
                    {proposalError}
                  </p>
                  <button
                    onClick={() => void refreshGovernance()}
                    className="inline-flex items-center gap-2 px-4 py-2 rounded-xl bg-[#007AFF] text-white text-xs font-bold uppercase tracking-widest hover:bg-[#0062CC] transition-all"
                  >
                    <RefreshCw className="w-3.5 h-3.5" />
                    Retry
                  </button>
                </div>
              ) : proposals.length === 0 ? (
                <div className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 text-center space-y-4">
                  <Vote className="w-12 h-12 text-gray-700 mx-auto" />
                  <h3 className="text-lg font-bold text-gray-400">No Proposals Found</h3>
                  <p className="text-sm text-gray-600 max-w-md mx-auto">
                    The governance API is live, but no proposals have been submitted into the current testnet queue yet.
                  </p>
                </div>
              ) : (
                <div className="space-y-3">
                  {proposals.map((p) => {
                    const totalVotes = p.votes_for + p.votes_against;
                    const yesPct = totalVotes > 0 ? Math.round((p.votes_for / totalVotes) * 100) : 0;
                    const noPct = totalVotes > 0 ? 100 - yesPct : 0;

                    return (
                      <div key={p.id} className="bg-[#1A1A1A] border border-white/5 rounded-xl p-6 space-y-4 hover:border-[#007AFF]/20 transition-all">
                        <div className="flex items-start justify-between gap-4">
                          <div className="space-y-1">
                            <div className="flex items-center gap-3">
                              <span className="text-[#007AFF] font-mono text-sm font-bold">#{p.id}</span>
                              <span className={`text-[9px] font-mono px-2 py-1 rounded-full uppercase tracking-widest ${STATUS_COLORS[p.status] || 'text-gray-500 bg-gray-500/10'}`}>
                                {formatStatusLabel(p.status)}
                              </span>
                              <span className="text-[9px] font-mono text-gray-600 bg-white/5 px-2 py-1 rounded uppercase tracking-widest">
                                {p.type}
                              </span>
                              {p.curator_reviewed && (
                                <span className="text-[9px] font-mono text-emerald-400 bg-emerald-500/10 px-2 py-1 rounded uppercase tracking-widest">
                                  Curator Reviewed
                                </span>
                              )}
                            </div>
                            <h3 className="text-lg font-bold text-white">{p.title}</h3>
                            <p className="text-xs text-gray-500 font-mono">
                              Proposer: {truncateValue(p.proposer)} | {new Date(p.created_at).toLocaleString()}
                            </p>
                          </div>
                        </div>

                        {/* Vote bar */}
                        <div className="space-y-2">
                          <div className="flex items-center justify-between text-xs">
                            <div className="flex items-center gap-1 text-emerald-500">
                              <CheckCircle className="w-3.5 h-3.5" />
                              <span className="font-bold">{p.votes_for} YES</span>
                              {totalVotes > 0 && <span className="text-gray-500 ml-1">({yesPct}%)</span>}
                            </div>
                            <div className="flex items-center gap-1 text-red-500">
                              <span className="font-bold">{p.votes_against} NO</span>
                              {totalVotes > 0 && <span className="text-gray-500 ml-1">({noPct}%)</span>}
                              <XCircle className="w-3.5 h-3.5" />
                            </div>
                          </div>
                          <div className="h-2 bg-[#050505] rounded-full overflow-hidden flex">
                            {totalVotes > 0 && (
                              <>
                                <div className="bg-emerald-500 transition-all" style={{ width: `${yesPct}%` }} />
                                <div className="bg-red-500 transition-all" style={{ width: `${noPct}%` }} />
                              </>
                            )}
                          </div>
                          <div className="text-[10px] text-gray-600 font-mono text-center">
                            {p.voter_count} voter{p.voter_count !== 1 ? 's' : ''} participated
                          </div>
                        </div>

                        {p.status === 'voting' && (
                          <div className="border-t border-white/5 pt-4 space-y-4">
                            {connectedAddress ? (
                              <>
                                <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
                                  <div className="bg-[#050505] border border-white/5 rounded-xl p-3 space-y-1">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Direct</div>
                                    <div className="text-sm font-black tracking-tighter italic text-white">
                                      {formatTokenAmount(votePowerByProposal[p.id]?.direct_weight ?? 0)}
                                    </div>
                                  </div>
                                  <div className="bg-[#050505] border border-white/5 rounded-xl p-3 space-y-1">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Delegated</div>
                                    <div className="text-sm font-black tracking-tighter italic text-purple-400">
                                      {formatTokenAmount(votePowerByProposal[p.id]?.delegated_weight ?? 0)}
                                    </div>
                                  </div>
                                  <div className="bg-[#050505] border border-white/5 rounded-xl p-3 space-y-1">
                                    <div className="text-[10px] font-bold uppercase tracking-widest text-gray-500">Effective Vote</div>
                                    <div className="text-sm font-black tracking-tighter italic text-[#007AFF]">
                                      {formatTokenAmount(votePowerByProposal[p.id]?.effective_weight ?? 0)}
                                    </div>
                                  </div>
                                </div>

                                {!connectedWalletCanSignData ? (
                                  <div className="rounded-xl border border-yellow-500/20 bg-yellow-500/10 px-4 py-3 text-xs text-yellow-400">
                                    This wallet can manage staking, but signed governance votes require arbitrary data signing support.
                                  </div>
                                ) : (
                                  <div className="flex flex-wrap gap-3">
                                    <button
                                      onClick={() => void handleSignedVote(p.id, 'for')}
                                      disabled={votingProposalId === p.id || (votePowerByProposal[p.id]?.effective_weight ?? 0) <= 0}
                                      className="rounded-xl bg-emerald-500 px-4 py-3 text-xs font-black uppercase tracking-widest text-black transition hover:bg-emerald-400 disabled:cursor-not-allowed disabled:opacity-40"
                                    >
                                      {votingProposalId === p.id ? 'Signing...' : 'Vote Yes'}
                                    </button>
                                    <button
                                      onClick={() => void handleSignedVote(p.id, 'against')}
                                      disabled={votingProposalId === p.id || (votePowerByProposal[p.id]?.effective_weight ?? 0) <= 0}
                                      className="rounded-xl bg-red-500 px-4 py-3 text-xs font-black uppercase tracking-widest text-black transition hover:bg-red-400 disabled:cursor-not-allowed disabled:opacity-40"
                                    >
                                      {votingProposalId === p.id ? 'Signing...' : 'Vote No'}
                                    </button>
                                  </div>
                                )}

                                {(votePowerByProposal[p.id]?.effective_weight ?? 0) <= 0 && (
                                  <p className="text-xs text-gray-500">
                                    This wallet currently has no active veCORTEX or undeclared delegated power for this proposal.
                                  </p>
                                )}
                              </>
                            ) : (
                              <p className="text-xs text-yellow-500/80">
                                Connect a wallet with veCORTEX power to cast a signed vote on this proposal.
                              </p>
                            )}
                          </div>
                        )}
                      </div>
                    );
                  })}
                </div>
              )}

              <div className="text-center">
                <p className="text-[10px] text-gray-600 font-mono">
                  Governance contract App ID {GOVERNANCE_APP_ID} remains visible on testnet, but the proposal feed above is sourced from the live governance API.
                </p>
              </div>
            </section>
          </motion.div>
        )}

        {/* AI Agents Tab */}
        {activeTab === 'agents' && (
          <motion.div key="agents" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0, y: -10 }} className="space-y-8">
            {/* Senator AI */}
            <section className="bg-[#1A1A1A] border border-[#007AFF]/20 rounded-2xl p-8 space-y-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-[#007AFF]/20 to-indigo-500/20 border border-[#007AFF]/30 flex items-center justify-center">
                  <Cpu className="w-7 h-7 text-[#007AFF]" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-tighter italic">The Senator</h2>
                  <p className="text-[10px] font-mono text-[#007AFF] uppercase tracking-widest">Protocol Analyst & Governance Proposer</p>
                </div>
                <span className="ml-auto text-[9px] font-mono text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full uppercase tracking-widest">Active on Testnet</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-2">
                  <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Capabilities</div>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>Biweekly protocol analysis (token behavior, user activity)</li>
                    <li>Drafts governance proposals with rationale</li>
                    <li>Mediates disputes (Article V)</li>
                    <li>Emergency proposal capability</li>
                  </ul>
                </div>
                <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-2">
                  <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Constraints</div>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>Cannot vote on its own proposals</li>
                    <li>Tri-Brain consensus required (Claude + Gemini + OpenAI)</li>
                    <li>Fail-closed: disagreement = no proposal</li>
                    <li>All proposal actions are logged and auditable</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* Curator AI */}
            <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-emerald-500/20 to-teal-500/20 border border-emerald-500/30 flex items-center justify-center">
                  <Shield className="w-7 h-7 text-emerald-500" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-tighter italic">The Curator</h2>
                  <p className="text-[10px] font-mono text-emerald-500 uppercase tracking-widest">Constitutional Compliance Reviewer</p>
                </div>
                <span className="ml-auto text-[9px] font-mono text-emerald-500 bg-emerald-500/10 px-3 py-1 rounded-full uppercase tracking-widest">Active on Testnet</span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-2">
                  <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Role</div>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>Reviews every proposal for constitutional compliance</li>
                    <li>Impact analysis and risk assessment</li>
                    <li>Publishes recommendation (APPROVE/REJECT)</li>
                    <li>Conversational AI for explaining analysis</li>
                  </ul>
                </div>
                <div className="bg-[#050505] border border-white/5 rounded-xl p-5 space-y-2">
                  <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Learning</div>
                  <ul className="text-sm text-gray-400 space-y-1">
                    <li>Feedback loop: tracks recommendation accuracy</li>
                    <li>Learns from vote outcomes to improve analysis</li>
                    <li>Memory: retains context from all past reviews</li>
                    <li>Gets smarter with every governance cycle</li>
                  </ul>
                </div>
              </div>
            </section>

            {/* Lawmaker Agents */}
            <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
              <div className="flex items-center gap-4">
                <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-500/20 to-pink-500/20 border border-purple-500/30 flex items-center justify-center">
                  <Users className="w-7 h-7 text-purple-500" />
                </div>
                <div>
                  <h2 className="text-xl font-black uppercase tracking-tighter italic">Lawmaker Agents</h2>
                  <p className="text-[10px] font-mono text-purple-500 uppercase tracking-widest">Delegated Voting Representatives</p>
                </div>
              </div>

              <p className="text-sm text-gray-400 leading-relaxed">
                Users can delegate their veCORTEX voting power to AI agents that vote on their behalf based on encoded principles. Delegation is revocable at any time (liquid delegation). Users always retain the right to override their agent&apos;s vote by voting directly.
              </p>

              <div className="flex items-center gap-3 p-4 bg-[#050505] border border-[#007AFF]/20 rounded-xl">
                <AlertTriangle className="w-5 h-5 text-[#007AFF] flex-shrink-0" />
                <p className="text-xs text-[#9ecbff]">
                  Delegation is live on testnet. Use the Proposals tab to stake, assign a delegate address, and cast wallet-signed votes with direct-override behavior.
                </p>
              </div>
            </section>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
