'use client';

import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { TrendingUp, Users, Zap, Search, Filter, ArrowUpRight, BarChart3, Plus, X } from 'lucide-react';

const AGENTS_DATA = [
  { id: 1, name: 'Cortex-Omega-1', symbol: 'CORTX', price: '0.42 ALGO', mcap: '$1.2M', holders: 1240, change: '+12.5%', curve: 65, category: 'AI' },
  { id: 2, name: 'Neural-Sentinel', symbol: 'SENT', price: '0.15 ALGO', mcap: '$450K', holders: 820, change: '-2.1%', curve: 22, category: 'Security' },
  { id: 3, name: 'Chaos-Oracle', symbol: 'ORCL', price: '2.10 ALGO', mcap: '$8.4M', holders: 4100, change: '+45.8%', curve: 98, category: 'Oracle' },
  { id: 4, name: 'Ghost-Protocol', symbol: 'GHOST', price: '0.08 ALGO', mcap: '$120K', holders: 310, change: '+5.4%', curve: 12, category: 'Privacy' },
];

export default function Marketplace() {
  const [search, setSearch] = useState('');
  const [filter, setFilter] = useState('All');
  const [isModalOpen, setIsModalOpen] = useState(false);

  const filteredAgents = AGENTS_DATA.filter(a => 
    (a.name.toLowerCase().includes(search.toLowerCase()) || a.symbol.toLowerCase().includes(search.toLowerCase())) &&
    (filter === 'All' || a.category === filter)
  );

  return (
    <div className="space-y-8">
      {/* Header with Launch Button */}
      <div className="flex flex-col md:flex-row justify-between items-start md:items-end gap-6 mb-12">
        <div className="space-y-2">
           <h2 className="text-4xl font-black tracking-tighter uppercase italic text-white">Agent Launchpad</h2>
           <p className="text-gray-500 font-medium">Neural-linked assets on the bonding curve.</p>
        </div>
        <button 
          onClick={() => setIsModalOpen(true)}
          className="bg-[#007AFF] hover:bg-[#0062CC] text-white px-8 py-4 rounded-2xl font-black uppercase tracking-widest text-xs flex items-center gap-3 transition-all shadow-lg shadow-[#007AFF]/20 active:scale-95"
        >
          <Plus className="w-5 h-5" /> Launch New Agent
        </button>
      </div>

      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-600 w-5 h-5" />
          <input 
            type="text" 
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Neural Search Agents..." 
            className="w-full bg-[#1A1A1A] border border-white/5 rounded-xl py-3 pl-12 pr-4 text-white focus:ring-2 focus:ring-[#007AFF]/50 outline-none transition-all font-medium"
          />
        </div>
        <div className="flex gap-3 w-full md:w-auto">
          {['All', 'AI', 'Security', 'Oracle', 'Privacy'].map(cat => (
            <button 
              key={cat}
              onClick={() => setFilter(cat)}
              className={`px-4 py-2 rounded-xl text-[10px] font-bold uppercase tracking-widest transition-all border ${filter === cat ? 'bg-[#007AFF] text-white border-[#007AFF]' : 'bg-[#1A1A1A] text-gray-500 hover:text-white border-white/5'}`}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <AnimatePresence mode="popLayout">
          {filteredAgents.map((agent, idx) => (
            <motion.div 
              key={agent.id}
              layout
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              exit={{ opacity: 0, scale: 0.9 }}
              className="bg-[#1A1A1A] border border-white/5 rounded-2xl p-5 hover:border-[#007AFF]/40 transition-all group cursor-pointer relative overflow-hidden"
            >
              <div className="absolute -top-24 -right-24 w-48 h-48 bg-[#007AFF]/5 blur-[80px] group-hover:bg-[#007AFF]/10 transition-all" />
              
              <div className="flex justify-between items-start mb-4">
                <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-[#007AFF]/20 to-indigo-500/20 border border-white/5 flex items-center justify-center text-[#007AFF] group-hover:scale-110 transition-transform shadow-inner">
                  <Zap className="w-6 h-6 fill-current" />
                </div>
                <div className={`px-2 py-1 rounded-md text-[10px] font-black font-mono ${agent.change.startsWith('+') ? 'bg-[#10B981]/10 text-[#10B981]' : 'bg-[#EF4444]/10 text-[#EF4444]'}`}>
                  {agent.change}
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
                  <p className="text-[9px] text-gray-600 font-mono uppercase font-bold tracking-widest">MCAP</p>
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
                 <div className="flex items-center gap-1 hover:text-white transition-colors"><BarChart3 className="w-3 h-3" /> Connect Node</div>
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {/* Launch Modal */}
      <AnimatePresence>
        {isModalOpen && (
          <div className="fixed inset-0 z-[100] flex items-center justify-center p-6">
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }} onClick={() => setIsModalOpen(false)} className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
            <motion.div initial={{ scale: 0.9, opacity: 0, y: 20 }} animate={{ scale: 1, opacity: 1, y: 0 }} exit={{ scale: 0.9, opacity: 0, y: 20 }} className="bg-[#121217] border border-white/10 rounded-[32px] p-10 max-w-lg w-full relative shadow-2xl z-[101]">
              <button onClick={() => setIsModalOpen(false)} className="absolute top-6 right-6 p-2 text-gray-500 hover:text-white transition-colors"><X className="w-6 h-6" /></button>
              <h2 className="text-3xl font-black tracking-tighter uppercase italic mb-2">Deploy Agent</h2>
              <p className="text-gray-500 text-xs mb-8 font-bold italic uppercase tracking-widest">Protocol Fee: 100 $CORTEX</p>
              
              <div className="space-y-6">
                 <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Agent Name</label>
                    <input type="text" placeholder="e.g. Neural Sentinel" className="w-full bg-[#050505] border border-white/5 rounded-xl p-4 text-white outline-none focus:ring-2 focus:ring-[#007AFF]/50 transition-all font-medium" />
                 </div>
                 <div className="space-y-2">
                    <label className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">Symbol</label>
                    <input type="text" placeholder="e.g. SENT" className="w-full bg-[#050505] border border-white/5 rounded-xl p-4 text-white outline-none focus:ring-2 focus:ring-[#007AFF]/50 transition-all font-medium" />
                 </div>
                 <button onClick={() => setIsModalOpen(false)} className="w-full bg-white text-black py-5 rounded-2xl font-black uppercase tracking-tighter text-sm hover:bg-gray-200 transition-all mt-4">Initialize Emancipation</button>
              </div>
            </motion.div>
          </div>
        )}
      </AnimatePresence>
    </div>
  );
}
