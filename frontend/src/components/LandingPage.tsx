'use client';

import Link from 'next/link';
import { PureCortexLogo } from '@/components/Logo';
import { CORTEX_ASSET_ID, FACTORY_APP_ID, REPO_URL, TGE_DATE_ISO } from '@/lib/protocolConfig';
import { motion } from 'framer-motion';
import { Shield, Cpu, Zap, ArrowRight } from 'lucide-react';
import { useState, useEffect } from 'react';

export default function LandingPage({ onEnter }: { onEnter?: () => void }) {
  const [timeLeft, setTimeStep] = useState<{ days: number; hours: number; minutes: number; seconds: number } | null>(null);

  useEffect(() => {
    const launchDate = new Date(TGE_DATE_ISO).getTime();

    const update = () => {
      const now = Date.now();
      const distance = Math.max(0, launchDate - now);

      setTimeStep({
        days: Math.floor(distance / (1000 * 60 * 60 * 24)),
        hours: Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60)),
        minutes: Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60)),
        seconds: Math.floor((distance % (1000 * 60)) / 1000)
      });
    };

    update();
    const timer = setInterval(update, 1000);
    return () => clearInterval(timer);
  }, []);

  return (
    <div className="min-h-screen bg-[#050505] text-white relative font-sans">
      {/* Background Ambience */}
      <div className="absolute top-0 left-1/4 w-[300px] md:w-[500px] h-[300px] md:h-[500px] bg-[#007AFF]/5 blur-[120px] rounded-full -z-10" />
      <div className="absolute bottom-0 right-1/4 w-[300px] md:w-[600px] h-[300px] md:h-[600px] bg-[#007AFF]/5 blur-[150px] rounded-full -z-10" />

      {/* Navigation */}
      <nav className="px-4 sm:px-8 py-6 sm:py-8 flex justify-between items-center max-w-7xl mx-auto">
        <PureCortexLogo />
        <div className="hidden md:flex gap-8 text-[10px] font-bold tracking-[0.3em] uppercase text-gray-500">
           <span className="text-[#007AFF]">01 Protocol</span>
           <span>02 Architecture</span>
           <span>03 Sovereign Nodes</span>
           <Link href="/developers/access" className="hover:text-white transition-colors">04 Developer Access</Link>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-8 pt-10 sm:pt-20 pb-24 sm:pb-32 lg:pb-20 grid lg:grid-cols-[minmax(0,1.05fr)_minmax(360px,0.95fr)] gap-10 lg:gap-16 xl:gap-20 items-start">
        <div className="space-y-6 sm:space-y-10 min-w-0">
          <motion.div
            initial={{ opacity: 0, x: -20 }}
            animate={{ opacity: 1, x: 0 }}
            className="inline-flex items-center gap-2 px-3 sm:px-4 py-2 rounded-full bg-[#007AFF]/10 border border-[#007AFF]/20 text-[9px] sm:text-[10px] font-bold text-[#007AFF] uppercase tracking-[0.2em] font-mono"
          >
            <Shield className="w-3 h-3" /> MODERN TECH STACK v1.0
          </motion.div>

          <motion.h1
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="max-w-[10ch] text-4xl sm:text-5xl lg:text-7xl xl:text-8xl font-bold tracking-tighter leading-[0.92] uppercase italic"
          >
            Point of <br/>
            <span className="text-transparent bg-clip-text bg-gradient-to-r from-[#007AFF] to-blue-400">Emancipation</span>
          </motion.h1>

          <motion.p
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="text-base sm:text-xl text-gray-400 max-w-xl font-medium leading-relaxed"
          >
            PURECORTEX is the premier infrastructure for autonomous agentic commerce.
            Powered by Algorand&apos;s finality and Tri-Brain cognitive consensus.
          </motion.p>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="flex flex-col sm:flex-row gap-3 sm:gap-4"
          >
            <button onClick={onEnter} className="bg-white text-black px-6 sm:px-10 py-4 sm:py-5 rounded-2xl font-black uppercase tracking-tighter text-sm flex items-center justify-center gap-3 hover:bg-gray-200 transition-all">
              Join the Vanguard <ArrowRight className="w-5 h-5" />
            </button>
            <Link href="/developers/access" className="px-6 sm:px-10 py-4 sm:py-5 rounded-2xl border border-white/10 font-black uppercase tracking-tighter text-sm hover:bg-white/5 transition-all text-center">
              Request Developer Access
            </Link>
          </motion.div>
        </div>

        {/* Countdown / Stats Card */}
        <motion.div
          initial={{ opacity: 0, scale: 0.9 }}
          animate={{ opacity: 1, scale: 1 }}
          transition={{ delay: 0.4 }}
          className="min-w-0 bg-[#1A1A1A] border border-white/5 rounded-3xl sm:rounded-[40px] p-6 sm:p-10 lg:p-12 shadow-2xl relative group"
        >
          <div className="absolute -inset-1 bg-gradient-to-r from-[#007AFF] to-indigo-600 rounded-[calc(1.5rem+1px)] sm:rounded-[41px] blur opacity-10 group-hover:opacity-20 transition-all" />

          <div className="relative space-y-8 sm:space-y-12">
            <div className="flex flex-col sm:flex-row justify-between items-start gap-4">
               <div className="space-y-1 min-w-0">
                  <h2 className="text-[10px] font-black text-[#007AFF] uppercase tracking-[0.2em] sm:tracking-[0.3em]">Mainnet Milestone</h2>
                  <p className="text-lg sm:text-2xl font-bold italic">MARCH 31, 2026</p>
                  <p className="text-xs sm:text-sm text-gray-500 uppercase tracking-[0.18em]">Target launch checkpoint</p>
               </div>
               <div className="w-10 h-10 sm:w-12 sm:h-12 bg-white/5 rounded-xl sm:rounded-2xl flex items-center justify-center border border-white/5 flex-shrink-0">
                  <Cpu className="w-5 h-5 sm:w-6 sm:h-6 text-[#007AFF]" />
               </div>
            </div>

            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4">
               {[
                 { label: 'Days', val: timeLeft?.days ?? 0 },
                 { label: 'Hrs', val: timeLeft?.hours ?? 0 },
                 { label: 'Min', val: timeLeft?.minutes ?? 0 },
                 { label: 'Sec', val: timeLeft?.seconds ?? 0 }
               ].map((t, i) => (
                 <div key={i} className="rounded-2xl bg-black/20 border border-white/5 py-3 sm:py-4 text-center space-y-1 sm:space-y-2 min-w-0">
                    <div className="text-2xl sm:text-4xl lg:text-[2.75rem] font-black tracking-tighter tabular-nums leading-none">
                      {timeLeft ? String(t.val).padStart(2, '0') : '--'}
                    </div>
                    <div className="text-[8px] sm:text-[9px] font-black text-gray-500 uppercase tracking-[0.25em]">{t.label}</div>
                 </div>
               ))}
            </div>

            <div className="pt-6 sm:pt-8 border-t border-white/5 space-y-4 sm:space-y-6">
               <div className="flex flex-col sm:flex-row justify-between items-start sm:items-center gap-3">
                  <span className="text-[9px] sm:text-[10px] font-black text-gray-500 uppercase tracking-widest flex items-center gap-2">
                    <Zap className="w-3 h-3 text-yellow-500" /> Mainnet Launch Readiness
                  </span>
                  <span className="text-[9px] sm:text-[10px] font-black text-emerald-500 uppercase tracking-widest animate-pulse">Tracking</span>
               </div>
               <div className="space-y-2">
                  <div className="flex justify-between text-[9px] sm:text-[10px] font-bold text-gray-400">
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

      <footer className="w-full max-w-7xl mx-auto px-4 sm:px-8 py-6 flex flex-col sm:flex-row justify-between items-center gap-3 text-[8px] font-black text-gray-700 uppercase tracking-[0.2em] sm:tracking-[0.4em]">
         <div className="flex items-center gap-4">
            <a href={REPO_URL} target="_blank" rel="noopener noreferrer" aria-label="GitHub" className="text-gray-600 hover:text-white transition-colors">
              <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current"><path d="M12 .297c-6.63 0-12 5.373-12 12 0 5.303 3.438 9.8 8.205 11.385.6.113.82-.258.82-.577 0-.285-.01-1.04-.015-2.04-3.338.724-4.042-1.61-4.042-1.61C4.422 18.07 3.633 17.7 3.633 17.7c-1.087-.744.084-.729.084-.729 1.205.084 1.838 1.236 1.838 1.236 1.07 1.835 2.809 1.305 3.495.998.108-.776.417-1.305.76-1.605-2.665-.3-5.466-1.332-5.466-5.93 0-1.31.465-2.38 1.235-3.22-.135-.303-.54-1.523.105-3.176 0 0 1.005-.322 3.3 1.23.96-.267 1.98-.399 3-.405 1.02.006 2.04.138 3 .405 2.28-1.552 3.285-1.23 3.285-1.23.645 1.653.24 2.873.12 3.176.765.84 1.23 1.91 1.23 3.22 0 4.61-2.805 5.625-5.475 5.92.42.36.81 1.096.81 2.22 0 1.606-.015 2.896-.015 3.286 0 .315.21.69.825.57C20.565 22.092 24 17.592 24 12.297c0-6.627-5.373-12-12-12" /></svg>
            </a>
            <a href="https://x.com/purecortexai" target="_blank" rel="noopener noreferrer" aria-label="X (Twitter)" className="text-gray-600 hover:text-white transition-colors">
              <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
            </a>
            <span className="hidden sm:inline">Hardened Intelligence Layer</span>
         </div>
         <div className="flex gap-4 sm:gap-10">
            <span>Contract: {FACTORY_APP_ID}</span>
            <span>$CORTEX: {CORTEX_ASSET_ID}</span>
         </div>
      </footer>
    </div>
  );
}
