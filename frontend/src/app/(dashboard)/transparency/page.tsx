'use client';

import { motion } from 'framer-motion';
import { Eye, Flame, Wallet, Clock, ExternalLink, BarChart3, ArrowDownRight, TrendingDown, Globe } from 'lucide-react';
import {
  AGENT_FACTORY_ESCROW,
  ASSISTANCE_FUND_ADDRESS,
  CREATOR_VESTING_ADDRESS,
  FACTORY_APP_ID,
  OPERATIONS_ADDRESS,
  TGE_DATE_ISO,
  TOTAL_SUPPLY,
} from '@/lib/protocolConfig';

const PROTOCOL_WALLETS = [
  { label: 'Agent Factory Escrow', address: AGENT_FACTORY_ESCROW, role: `Canonical factory deployment (App ID ${FACTORY_APP_ID})` },
  { label: 'Assistance Fund', address: ASSISTANCE_FUND_ADDRESS, role: '90% revenue → buyback-burn' },
  { label: 'Operations', address: OPERATIONS_ADDRESS, role: '10% revenue → operations' },
  { label: 'Creator Vesting', address: CREATOR_VESTING_ADDRESS, role: '10% TGE + daily vest over 6 months' },
];

const SUPPLY_ALLOCATION = [
  { label: 'Genesis Airdrop', pct: 31, color: '#007AFF' },
  { label: 'Staking Rewards', pct: 24, color: '#6366F1' },
  { label: 'Liquidity', pct: 15, color: '#10B981' },
  { label: 'Agent Incentives', pct: 15, color: '#F59E0B' },
  { label: 'Creator', pct: 10, color: '#EF4444' },
  { label: 'Assistance Fund', pct: 5, color: '#8B5CF6' },
];

const TGE_DATE = new Date(TGE_DATE_ISO);

function isAlgorandAddress(value: string | null): value is string {
  return typeof value === 'string' && /^[A-Z2-7]{58}$/.test(value);
}

function formatNumber(n: number): string {
  if (n >= 1e15) return (n / 1e15).toFixed(1) + 'Q';
  if (n >= 1e12) return (n / 1e12).toFixed(1) + 'T';
  if (n >= 1e9) return (n / 1e9).toFixed(1) + 'B';
  if (n >= 1e6) return (n / 1e6).toFixed(1) + 'M';
  return n.toLocaleString();
}

function getVestingProgress(): { released: number; remaining: number; pctReleased: number } {
  const now = new Date();
  const creatorTotal = TOTAL_SUPPLY * 0.10;
  const tgeAmount = creatorTotal * 0.10;

  if (now < TGE_DATE) {
    return { released: 0, remaining: creatorTotal, pctReleased: 0 };
  }

  const daysSinceTGE = Math.floor((now.getTime() - TGE_DATE.getTime()) / (1000 * 60 * 60 * 24));
  const vestDays = 180;
  const vestedPortion = Math.min(daysSinceTGE / vestDays, 1) * (creatorTotal - tgeAmount);
  const released = tgeAmount + vestedPortion;

  return {
    released,
    remaining: creatorTotal - released,
    pctReleased: (released / creatorTotal) * 100,
  };
}

export default function TransparencyPage() {
  const vesting = getVestingProgress();
  const now = new Date();
  const isPreTGE = now < TGE_DATE;

  return (
    <div className="space-y-12">
      {/* Header */}
      <div className="space-y-2">
        <div className="flex items-center gap-3">
          <Eye className="w-6 h-6 text-[#007AFF]" />
          <h1 className="text-4xl font-black tracking-tighter uppercase italic text-white">Transparency</h1>
        </div>
        <p className="text-gray-500 font-medium">Real-time protocol metrics. Fully verifiable on Algorand.</p>
      </div>

      {/* Supply Overview */}
      <section className="grid grid-cols-1 md:grid-cols-3 gap-6">
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-6 space-y-3">
          <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Total Supply</div>
          <div className="text-3xl font-black tracking-tighter italic">{formatNumber(TOTAL_SUPPLY)}</div>
          <div className="text-[10px] font-mono text-gray-600">10 quadrillion CORTEX</div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-6 space-y-3">
          <div className="flex items-center gap-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
            <Flame className="w-3 h-3 text-orange-500" /> Burned
          </div>
          <div className="text-3xl font-black tracking-tighter italic text-orange-500">0</div>
          <div className="text-[10px] font-mono text-gray-600">{isPreTGE ? 'Burns begin after TGE' : 'Via Assistance Fund buyback-burn'}</div>
        </motion.div>

        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }} className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-6 space-y-3">
          <div className="flex items-center gap-2 text-[10px] font-bold text-gray-500 uppercase tracking-widest">
            <TrendingDown className="w-3 h-3 text-[#007AFF]" /> Circulating
          </div>
          <div className="text-3xl font-black tracking-tighter italic">{isPreTGE ? '—' : formatNumber(TOTAL_SUPPLY * 0.31)}</div>
          <div className="text-[10px] font-mono text-gray-600">{isPreTGE ? 'Launches at TGE' : '31% genesis airdrop at TGE'}</div>
        </motion.div>
      </section>

      {/* Allocation Breakdown */}
      <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
        <h2 className="text-xl font-black uppercase tracking-tighter italic flex items-center gap-3">
          <BarChart3 className="w-5 h-5 text-[#007AFF]" /> Supply Allocation
        </h2>

        <div className="space-y-4">
          {SUPPLY_ALLOCATION.map((item) => (
            <div key={item.label} className="space-y-2">
              <div className="flex justify-between text-sm">
                <span className="font-bold text-gray-300">{item.label}</span>
                <span className="font-mono text-gray-500">{item.pct}% — {formatNumber(TOTAL_SUPPLY * item.pct / 100)} CORTEX</span>
              </div>
              <div className="w-full h-2 bg-black/60 rounded-full overflow-hidden border border-white/5">
                <motion.div
                  initial={{ width: 0 }}
                  animate={{ width: `${item.pct}%` }}
                  transition={{ duration: 1, delay: 0.3 }}
                  className="h-full rounded-full"
                  style={{ backgroundColor: item.color }}
                />
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Creator Vesting */}
      <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
        <h2 className="text-xl font-black uppercase tracking-tighter italic flex items-center gap-3">
          <Clock className="w-5 h-5 text-[#007AFF]" /> Creator Vesting Schedule
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
          <div className="space-y-1">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">TGE Release (10%)</div>
            <div className="text-2xl font-black tracking-tighter italic">{formatNumber(TOTAL_SUPPLY * 0.01)}</div>
            <div className="text-[10px] font-mono text-gray-600">March 31, 2026</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Daily Vest (90%)</div>
            <div className="text-2xl font-black tracking-tighter italic">{formatNumber(TOTAL_SUPPLY * 0.09 / 180)}/day</div>
            <div className="text-[10px] font-mono text-gray-600">Over 180 days (Apr 1 - Sep 27, 2026)</div>
          </div>
          <div className="space-y-1">
            <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Released So Far</div>
            <div className="text-2xl font-black tracking-tighter italic text-[#007AFF]">{vesting.pctReleased.toFixed(1)}%</div>
            <div className="text-[10px] font-mono text-gray-600">{formatNumber(vesting.released)} CORTEX</div>
          </div>
        </div>

        <div className="space-y-2">
          <div className="flex justify-between text-[10px] font-mono text-gray-500 uppercase tracking-widest">
            <span>Vesting Progress</span>
            <span>{vesting.pctReleased.toFixed(1)}%</span>
          </div>
          <div className="w-full h-3 bg-black/60 rounded-full overflow-hidden border border-white/5">
            <motion.div
              initial={{ width: 0 }}
              animate={{ width: `${vesting.pctReleased}%` }}
              transition={{ duration: 1 }}
              className="h-full bg-gradient-to-r from-[#007AFF] to-[#6366F1] rounded-full"
            />
          </div>
        </div>
      </section>

      {/* Revenue Flow */}
      <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
        <h2 className="text-xl font-black uppercase tracking-tighter italic flex items-center gap-3">
          <ArrowDownRight className="w-5 h-5 text-emerald-500" /> Revenue Flow
        </h2>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
          <div className="bg-[#050505] border border-white/5 rounded-xl p-6 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-emerald-500" />
              <span className="text-sm font-bold uppercase tracking-wider">90% → Assistance Fund</span>
            </div>
            <p className="text-xs text-gray-500">Continuous buyback-and-burn. All protocol revenue (trading fees, creation fees, MCP micropayments) flows to the Assistance Fund which buys back CORTEX and burns it.</p>
          </div>
          <div className="bg-[#050505] border border-white/5 rounded-xl p-6 space-y-3">
            <div className="flex items-center gap-2">
              <div className="w-3 h-3 rounded-full bg-[#007AFF]" />
              <span className="text-sm font-bold uppercase tracking-wider">10% → Operations</span>
            </div>
            <p className="text-xs text-gray-500">Infrastructure costs, AI API fees, node maintenance, and development. Governed by the SovereignTreasury contract with max 2%/year drawdown.</p>
          </div>
        </div>
      </section>

      {/* Protocol Wallets */}
      <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
        <h2 className="text-xl font-black uppercase tracking-tighter italic flex items-center gap-3">
          <Wallet className="w-5 h-5 text-[#007AFF]" /> Protocol Wallets
        </h2>

        <div className="space-y-3">
          {PROTOCOL_WALLETS.map((wallet) => (
            <div key={wallet.label} className="flex flex-col md:flex-row justify-between items-start md:items-center gap-2 p-4 bg-[#050505] border border-white/5 rounded-xl">
              <div className="space-y-1">
                <div className="text-sm font-bold text-white">{wallet.label}</div>
                <div className="text-[10px] text-gray-500">{wallet.role}</div>
              </div>
              <div className="flex items-center gap-2">
                <code className="text-[10px] font-mono text-[#007AFF] bg-[#007AFF]/10 px-2 py-1 rounded">
                  {wallet.address || 'Pending testnet assignment'}
                </code>
                {isAlgorandAddress(wallet.address) && (
                  <a href={`https://allo.info/account/${wallet.address}`} target="_blank" rel="noopener noreferrer" className="text-gray-600 hover:text-[#007AFF] transition-colors">
                    <ExternalLink className="w-3 h-3" />
                  </a>
                )}
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* API Endpoints */}
      <section className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-8 space-y-6">
        <h2 className="text-xl font-black uppercase tracking-tighter italic flex items-center gap-3">
          <Globe className="w-5 h-5 text-[#007AFF]" /> Transparency API
        </h2>
        <p className="text-sm text-gray-500">External applications can verify all protocol data via these public endpoints.</p>

        <div className="space-y-2">
          {[
            { method: 'GET', path: '/api/transparency/supply', desc: 'Token supply breakdown' },
            { method: 'GET', path: '/api/transparency/treasury', desc: 'Fund balances' },
            { method: 'GET', path: '/api/transparency/burns', desc: 'Burn history' },
            { method: 'GET', path: '/api/transparency/governance', desc: 'Governance metrics' },
            { method: 'GET', path: '/api/transparency/agents', desc: 'Agent registry' },
          ].map((endpoint) => (
            <div key={endpoint.path} className="flex items-center gap-4 p-3 bg-[#050505] border border-white/5 rounded-lg font-mono text-xs">
              <span className="text-emerald-500 font-bold w-10">{endpoint.method}</span>
              <span className="text-[#007AFF]">{endpoint.path}</span>
              <span className="text-gray-600 ml-auto hidden md:block">{endpoint.desc}</span>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
