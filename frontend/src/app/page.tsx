'use client';

import { useState } from 'react';
import Chat from '@/components/Chat';
import Marketplace from '@/components/Marketplace';
import WalletButton from '@/components/WalletButton';
import { Rocket, MessageSquare, BarChart3, Settings, ShieldCheck, Cpu } from 'lucide-react';
import { motion } from 'framer-motion';

export default function Home() {
  const [activeTab, setActiveTab] = useState<'marketplace' | 'chat'>('marketplace');

  return (
    <div className="min-h-screen bg-[#08080A] text-white selection:bg-blue-500/30">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#08080A]/80 backdrop-blur-xl border-b border-white/5 px-6 py-4">
        <div className="max-w-[1400px] mx-auto flex justify-between items-center">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center">
              <Cpu className="w-5 h-5 text-white" />
            </div>
            <span className="text-xl font-black tracking-tighter uppercase italic">PureCortex</span>
          </div>

          <div className="hidden md:flex items-center gap-8">
            <button 
              onClick={() => setActiveTab('marketplace')}
              className={`flex items-center gap-2 text-sm font-bold uppercase tracking-widest transition-colors ${activeTab === 'marketplace' ? 'text-blue-500' : 'text-gray-500 hover:text-white'}`}
            >
              <BarChart3 className="w-4 h-4" /> Marketplace
            </button>
            <button 
              onClick={() => setActiveTab('chat')}
              className={`flex items-center gap-2 text-sm font-bold uppercase tracking-widest transition-colors ${activeTab === 'chat' ? 'text-blue-500' : 'text-gray-500 hover:text-white'}`}
            >
              <MessageSquare className="w-4 h-4" /> Neural Link
            </button>
            <a href="#" className="text-sm font-bold uppercase tracking-widest text-gray-500 hover:text-white transition-colors">Docs</a>
          </div>

          <div className="flex items-center gap-4">
             <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-bold text-emerald-500 uppercase">
                <ShieldCheck className="w-3.5 h-3.5" /> Testnet Active
             </div>
             <WalletButton />
          </div>
        </div>
      </nav>

      {/* Hero Section */}
      <header className="relative pt-32 pb-16 px-6 overflow-hidden">
        {/* Background Gradients */}
        <div className="absolute top-0 left-1/2 -translate-x-1/2 w-full max-w-7xl h-96 bg-blue-600/10 blur-[120px] -z-10" />
        
        <div className="max-w-[1400px] mx-auto text-center space-y-6">
          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs font-bold text-blue-400 uppercase tracking-widest"
          >
            <Rocket className="w-4 h-4" /> 
            Next-Gen Autonomous Agent Protocol
          </motion.div>
          
          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-5xl md:text-7xl font-black tracking-tighter leading-tight"
          >
            The Future of <span className="text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-indigo-600">Sovereign Intelligence</span>
          </motion.h1>
          
          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="max-w-2xl mx-auto text-gray-400 text-lg md:text-xl font-medium"
          >
            Deploy, tokenize, and chat with autonomous AI agents on Algorand. Powered by dual-brain consensus and hardened security.
          </motion.p>
        </div>
      </header>

      {/* Main Content Area */}
      <main className="max-w-[1400px] mx-auto px-6 pb-32">
        <div className="flex flex-col gap-12">
          {activeTab === 'marketplace' ? (
            <motion.section 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-8"
            >
              <div className="flex justify-between items-end">
                <div>
                   <h2 className="text-3xl font-bold tracking-tight mb-2 italic uppercase">Agent Launchpad</h2>
                   <p className="text-gray-500">Discover and trade tokens on the bonding curve.</p>
                </div>
                <button className="bg-white text-black hover:bg-gray-200 px-6 py-3 rounded-xl font-black text-sm uppercase tracking-widest transition-all">
                  Launch New Agent
                </button>
              </div>
              <Marketplace />
            </motion.section>
          ) : (
            <motion.section 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="space-y-8"
            >
               <div className="text-center mb-8">
                  <h2 className="text-3xl font-bold tracking-tight mb-2 italic uppercase">Neural Link Interface</h2>
                  <p className="text-gray-500">Direct encrypted communication with Cortex-Omega-1.</p>
               </div>
               <Chat />
            </motion.section>
          )}
        </div>
      </main>

      {/* Global Status Bar */}
      <footer className="fixed bottom-0 left-0 right-0 bg-[#08080A]/90 backdrop-blur-md border-t border-white/5 px-6 py-3">
        <div className="max-w-[1400px] mx-auto flex justify-between items-center text-[10px] font-mono text-gray-600 uppercase tracking-widest">
           <div className="flex items-center gap-6">
              <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> API: Operational</span>
              <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> Algod: Syncing</span>
              <span className="flex items-center gap-2 text-blue-500"><div className="w-1.5 h-1.5 rounded-full bg-blue-500" /> Consensus: Active</span>
           </div>
           <div className="hidden sm:block">
              Built with PureCortex SDK v0.4.0-Beta
           </div>
        </div>
      </footer>
    </div>
  );
}
