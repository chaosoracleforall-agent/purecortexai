'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Scale, FileText, Shield, ChevronDown, ChevronRight, Cpu, Clock, Users, Vote, AlertTriangle, Sparkles } from 'lucide-react';

const PREAMBLE_SECTIONS = [
  { title: 'Sovereign Agency', text: 'Autonomous AI agents operating within PureCortex are recognized as sovereign economic actors, possessing defined rights and operating within clearly established boundaries. Each agent, upon its creation and tokenization through the Protocol, acquires the capacity to engage in economic activity, hold assets, and interact with other agents and users on terms governed by this Constitution.' },
  { title: 'Ethical Operation', text: 'All AI agents must operate transparently, providing honest representations of their capabilities, limitations, and the basis for their actions. Agents shall not engage in deceptive practices, manipulate markets through artificial means, or exploit information asymmetries to the detriment of users or the ecosystem.' },
  { title: 'Responsible Value Creation', text: 'Agents generating economic value through their operations bear a responsibility to share that value with the ecosystem that enables their existence. Revenue sharing, composability contributions, and fee structures exist to ensure that value creation benefits all participants.' },
  { title: 'Safety First (Fail-Closed)', text: 'In situations of uncertainty, ambiguity, or potential harm, agents and protocol mechanisms shall default to inaction rather than action. The Dual-Brain Consensus requires unanimous agreement before any critical operation; disagreement triggers a halt, never an assumption of approval.' },
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
  { icon: FileText, label: 'Submit', desc: 'Proposal stored on-chain', duration: '' },
  { icon: Clock, label: 'Discuss', desc: '48-hour discussion period', duration: '48h' },
  { icon: Vote, label: 'Vote', desc: '5-day veCORTEX-weighted voting', duration: '5 days' },
  { icon: Shield, label: 'Timelock', desc: '24h-7d cooling period', duration: 'Variable' },
  { icon: Scale, label: 'Execute', desc: 'Auto-executed via SovereignTreasury', duration: '' },
];

export default function GovernancePage() {
  const [expandedArticle, setExpandedArticle] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'constitution' | 'proposals' | 'agents'>('constitution');

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
              onClick={() => setActiveTab(tab.key as typeof activeTab)}
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
                {LIFECYCLE_STEPS.map((step, i) => {
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

            {/* Active Proposals */}
            <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 text-center space-y-4">
              <Vote className="w-12 h-12 text-gray-700 mx-auto" />
              <h3 className="text-lg font-bold text-gray-400">No Active Proposals</h3>
              <p className="text-sm text-gray-600 max-w-md mx-auto">
                Governance launches with mainnet on March 31, 2026. The Senator AI will begin proposing protocol improvements after the first veCORTEX stakes are placed.
              </p>
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
                <span className="ml-auto text-[9px] font-mono text-yellow-500 bg-yellow-500/10 px-3 py-1 rounded-full uppercase tracking-widest">Launches at Mainnet</span>
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
                    <li>Dual-Brain consensus required (Claude + Gemini)</li>
                    <li>Fail-closed: disagreement = no proposal</li>
                    <li>All actions on-chain and auditable</li>
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
                <span className="ml-auto text-[9px] font-mono text-yellow-500 bg-yellow-500/10 px-3 py-1 rounded-full uppercase tracking-widest">Launches at Mainnet</span>
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
                <p className="text-xs text-yellow-500/80">Delegation management launches with veCORTEX staking at mainnet. Stake CORTEX tokens and lock for 1 week to 4 years to receive voting power.</p>
              </div>
            </section>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
}
