'use client';

import { useCallback, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, FileText, Shield, ChevronDown, ChevronRight, Cpu, Clock, Users, Vote, AlertTriangle, Sparkles, ExternalLink, CheckCircle, XCircle, Loader2, RefreshCw } from 'lucide-react';
import { GOVERNANCE_APP_ID } from '@/lib/algorand';
import { fetchJson } from '@/lib/api';

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

export default function GovernancePage() {
  const [expandedArticle, setExpandedArticle] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<GovernanceTab>('constitution');
  const [proposals, setProposals] = useState<GovernanceProposalSummary[]>([]);
  const [overview, setOverview] = useState<GovernanceOverview | null>(null);
  const [loadingProposals, setLoadingProposals] = useState(false);
  const [proposalError, setProposalError] = useState<string | null>(null);
  const [hasLoadedProposals, setHasLoadedProposals] = useState(false);

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
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Failed to load governance proposals';
      setProposalError(message);
    } finally {
      setLoadingProposals(false);
    }
  }, []);

  const handleTabChange = useCallback((tab: GovernanceTab) => {
    setActiveTab(tab);
    if (tab === 'proposals' && !hasLoadedProposals && !loadingProposals) {
      void loadProposals();
    }
  }, [hasLoadedProposals, loadProposals, loadingProposals]);

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
                    onClick={() => void loadProposals()}
                    className="flex items-center gap-2 px-3 py-2 rounded-xl border border-white/10 text-[10px] font-mono uppercase tracking-widest text-gray-400 hover:text-white hover:border-[#007AFF]/40 transition-all"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${loadingProposals ? 'animate-spin text-[#007AFF]' : ''}`} />
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
                    onClick={() => void loadProposals()}
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

              <div className="flex items-center gap-3 p-4 bg-[#050505] border border-yellow-500/20 rounded-xl">
                <AlertTriangle className="w-5 h-5 text-yellow-500 flex-shrink-0" />
                <p className="text-xs text-yellow-500/80">Delegation management is not active on testnet yet. veCORTEX staking and delegated voting remain part of the later rollout plan.</p>
              </div>
            </section>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
