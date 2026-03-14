'use client';

import { PureCortexLogo } from '@/components/Logo';
import { motion } from 'framer-motion';
import { Shield, Cpu, Zap, Globe, ArrowRight } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function LandingPage({ onEnter }: { onEnter?: () => void }) {
  const [timeLeft, setTimeStep] = useState({ days: 0, hours: 0, minutes: 0, seconds: 0 });

  useEffect(() => {
    const launchDate = new Date('March 31, 2026 00:00:00').getTime();
    
    const timer = setInterval(() => {
      const now = new Date().getTime();
      const distance = launchDate - now;
      
      setTimeStep({
        days: Math.floor(distance / (1000 * 60 * 60 * 24)),
        hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
        minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
        seconds: Math.floor((distance % (1000 * 60)) / 1000)
      });
    }, 1000);

    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-[#050505] text-white overflow-hidden relative font-sans">
      {/* Background Ambience - Strict Neural Blue */}
      <div className="absolute top-0 left-1/4 w-[500px] h-[500px] bg-[#007AFF]/5 blur-[120px] rounded-full -z-10" />
      <div className="absolute bottom-0 right-1/4 w-[600px] h-[600px] bg-[#007AFF]/5 blur-[150px] rounded-full -z-10" />
      
      {/* Navigation */}
      <nav className="p-8 flex justify-between items-center max-w-7xl mx-auto">
        <PureCortexLogo />
        <div className="hidden md:flex gap-8 text-[10px] font-bold tracking-[0.3em] uppercase text-gray-500">
           <span className="text-[#007AFF]">01 Protocol</span>
           <span>02 Architecture</span>
           <span>03 Sovereign Nodes</span>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-8 pt-20 pb-32 grid lg:grid-cols-2 gap-20 items-center">
        <div className="space-y-10">
          <motion.div 
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-[#007AFF]/10 border border-[#007AFF]/20 text-[10px] font-bold text-[#007AFF] uppercase tracking-[0.2em] font-mono"
          >
            <Shield className="w-3 h-3" /> MODERN TECH STACK v1.0
          </motion.div>

          <motion.h1 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="text-6xl md:text-8xl font-bold tracking-tighter leading-[0.9] uppercase italic"
          >
            Point of <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#007AFF] to-blue-400">Emancipation</span>
          </motion.h1>

          <motion.p 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-xl text-gray-400 max-w-xl font-medium leading-relaxed"
          >
            PureCortex is the premier infrastructure for autonomous agentic commerce. 
            Powered by Algorand's finality and Dual-Brain cognitive consensus.
          </motion.p>

          <motion.div 
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-wrap gap-4"
          >
            <button onClick={onEnter} className="bg-white text-black px-10 py-5 rounded-2xl font-black uppercase tracking-tighter text-sm flex items-center gap-3 hover:bg-gray-200 transition-all">
              Join the Vanguard <ArrowRight className="w-5 h-5" />
            </button>
            <a href="https://twitter.com/purecortexat" target="_blank" className="px-10 py-5 rounded-2xl border border-white/10 font-black uppercase tracking-tighter text-sm hover:bg-white/5 transition-all">
              Follow Node Intelligence
            </a>
          </motion.div>
        </div>

        {/* Countdown / Stats Card */}
        <motion.div 
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="bg-[#1A1A1A] border border-white/5 rounded-[40px] p-12 shadow-2xl relative group"
        >
          <div className="absolute -inset-1 bg-gradient-to-r from-[#007AFF] to-indigo-600 rounded-[41px] blur opacity-10 group-hover:opacity-20 transition-all" />
          
          <div className="relative space-y-12">
            <div className="flex justify-between items-start">
               <div className="space-y-1">
                  <h2 className="text-[10px] font-black text-[#007AFF] uppercase tracking-[0.3em]">Mainnet Deployment</h2>
                  <p className="text-2xl font-bold italic">MARCH 31, 2026</p>
               </div>
               <div className="w-12 h-12 bg-white/5 rounded-2xl flex items-center justify-center border border-white/5">
                  <Cpu className="w-6 h-6 text-[#007AFF]" />
               </div>
            </div>

            <div className="grid grid-cols-4 gap-4">
               {[
                 { label: 'Days', val: timeLeft.days },
                 { label: 'Hrs', val: timeLeft.hours },
                 { label: 'Min', val: timeLeft.minutes },
                 { label: 'Sec', val: timeLeft.seconds }
               ].map((t, i) => (
                 <div key={i} className="text-center space-y-2">
                    <div className="text-4xl md:text-5xl font-black tracking-tighter tabular-nums">{String(t.val).padStart(2, '0')}</div>
                    <div className="text-[8px] font-black text-gray-600 uppercase tracking-widest">{t.label}</div>
                 </div>
               ))}
            </div>

            <div className="pt-8 border-t border-white/5 space-y-6">
               <div className="flex justify-between items-center">
                  <span className="text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Zap className="w-3 h-3 text-yellow-500" /> Testnet Engagement
                  </span>
                  <span className="text-[10px] font-black text-emerald-500 uppercase tracking-widest animate-pulse">Live</span>
               </div>
               <div className="space-y-2">
                  <div className="flex justify-between text-[10px] font-bold text-gray-400">
                    <span>PROTOCOL STABILITY</span>
                    <span>99.9%</span>
                  </div>
                  <div className="w-full h-1.5 bg-black rounded-full overflow-hidden">
                    <div className="w-[99.9%] h-full bg-[#007AFF]" />
                  </div>
               </div>
            </div>
          </div>
        </motion.div>
      </main>

      {/* Visual Accents */}
      <footer className="fixed bottom-10 left-1/2 -translate-x-1/2 w-full max-w-7xl px-8 flex justify-between items-center text-[8px] font-black text-gray-700 uppercase tracking-[0.4em]">
         <span>Hardened Intelligence Layer</span>
         <div className="flex gap-10">
            <span>Verified Contract: 757091997</span>
            <span>$CORTEX: 757092088</span>
         </div>
      </footer>
    </div>
  );
}
