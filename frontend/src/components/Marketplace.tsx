'use client';

import { motion } from 'framer-motion';
import { TrendingUp, Users, Zap, Search, Filter, ArrowUpRight, BarChart3 } from 'lucide-react';

const AGENTS = [
  { id: 1, name: 'Cortex-Omega-1', symbol: 'CORTX', price: '0.42 ALGO', mcap: '$1.2M', holders: 1240, change: '+12.5%', curve: 65 },
  { id: 2, name: 'Neural-Sentinel', symbol: 'SENT', price: '0.15 ALGO', mcap: '$450K', holders: 820, change: '-2.1%', curve: 22 },
  { id: 3, name: 'Chaos-Oracle', symbol: 'ORCL', price: '2.10 ALGO', mcap: '$8.4M', holders: 4100, change: '+45.8%', curve: 98 },
  { id: 4, name: 'Ghost-Protocol', symbol: 'GHOST', price: '0.08 ALGO', mcap: '$120K', holders: 310, change: '+5.4%', curve: 12 },
];

export default function Marketplace() {
  return (
    <div className="space-y-8">
      {/* Controls */}
      <div className="flex flex-col md:flex-row gap-4 justify-between items-center">
        <div className="relative w-full md:w-96">
          <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500 w-5 h-5" />
          <input 
            type="text" 
            placeholder="Search agents by name or symbol..." 
            className="w-full bg-[#16161D] border border-white/5 rounded-xl py-3 pl-12 pr-4 text-white focus:ring-2 focus:ring-blue-500/50 outline-none transition-all"
          />
        </div>
        <div className="flex gap-3 w-full md:w-auto">
          <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-[#16161D] border border-white/5 text-gray-400 px-4 py-3 rounded-xl hover:bg-white/5 transition-all text-sm font-medium">
            <Filter className="w-4 h-4" /> Filter
          </button>
          <button className="flex-1 md:flex-none flex items-center justify-center gap-2 bg-[#16161D] border border-white/5 text-gray-400 px-4 py-3 rounded-xl hover:bg-white/5 transition-all text-sm font-medium">
            <TrendingUp className="w-4 h-4" /> Trending
          </button>
        </div>
      </div>

      {/* Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        {AGENTS.map((agent, idx) => (
          <motion.div 
            key={agent.id}
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.1 }}
            className="bg-[#16161D] border border-white/5 rounded-2xl p-5 hover:border-blue-500/30 transition-all group cursor-pointer relative overflow-hidden"
          >
            {/* Background Glow */}
            <div className="absolute -top-24 -right-24 w-48 h-48 bg-blue-600/5 blur-[80px] group-hover:bg-blue-600/10 transition-all" />
            
            <div className="flex justify-between items-start mb-4">
              <div className="w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500/20 to-purple-500/20 border border-white/5 flex items-center justify-center text-blue-400 group-hover:scale-110 transition-transform">
                <Zap className="w-6 h-6" />
              </div>
              <div className={`px-2 py-1 rounded-md text-[10px] font-bold font-mono ${agent.change.startsWith('+') ? 'bg-emerald-500/10 text-emerald-500' : 'bg-rose-500/10 text-rose-500'}`}>
                {agent.change}
              </div>
            </div>

            <div className="space-y-1 mb-6">
              <h3 className="text-white font-bold text-lg flex items-center gap-2">
                {agent.name}
                <ArrowUpRight className="w-4 h-4 text-gray-600 group-hover:text-blue-400 transition-colors" />
              </h3>
              <p className="text-gray-500 text-xs font-mono uppercase tracking-widest">{agent.symbol}</p>
            </div>

            <div className="grid grid-cols-2 gap-4 mb-6">
              <div>
                <p className="text-[10px] text-gray-600 font-mono uppercase">Price</p>
                <p className="text-sm font-bold text-white">{agent.price}</p>
              </div>
              <div>
                <p className="text-[10px] text-gray-600 font-mono uppercase">Market Cap</p>
                <p className="text-sm font-bold text-white">{agent.mcap}</p>
              </div>
            </div>

            {/* Bonding Curve Progress */}
            <div className="space-y-2">
              <div className="flex justify-between text-[10px] font-mono uppercase text-gray-600">
                <span>Curve Progress</span>
                <span className="text-blue-400">{agent.curve}%</span>
              </div>
              <div className="w-full h-1.5 bg-black/40 rounded-full overflow-hidden">
                <motion.div 
                  initial={{ width: 0 }}
                  animate={{ width: `${agent.curve}%` }}
                  className="h-full bg-gradient-to-r from-blue-600 to-indigo-500"
                />
              </div>
            </div>
            
            <div className="mt-6 flex items-center justify-between text-[10px] text-gray-500 border-t border-white/5 pt-4">
               <div className="flex items-center gap-1"><Users className="w-3 h-3" /> {agent.holders}</div>
               <div className="flex items-center gap-1"><BarChart3 className="w-3 h-3" /> Trade</div>
            </div>
          </motion.div>
        ))}
      </div>
    </div>
  );
}
