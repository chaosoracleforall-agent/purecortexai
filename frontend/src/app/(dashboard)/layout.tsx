'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PureCortexLogo } from '@/components/Logo';
import WalletButton from '@/components/WalletButton';
import { BarChart3, MessageSquare, Eye, Scale, ShieldCheck, Menu, X, Github } from 'lucide-react';
import { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

const NAV_ITEMS = [
  { href: '/marketplace', label: 'Marketplace', icon: BarChart3 },
  { href: '/chat', label: 'Neural Link', icon: MessageSquare },
  { href: '/governance', label: 'Governance', icon: Scale },
  { href: '/transparency', label: 'Transparency', icon: Eye },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);
  const previousPathnameRef = useRef(pathname);

  // Close mobile menu on route change
  useEffect(() => {
    if (previousPathnameRef.current !== pathname) {
      previousPathnameRef.current = pathname;
      queueMicrotask(() => setMobileMenuOpen(false));
    }
  }, [pathname]);

  // Close on escape
  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') setMobileMenuOpen(false);
  }, []);

  useEffect(() => {
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [handleEscape]);

  // Prevent body scroll when menu is open
  useEffect(() => {
    if (mobileMenuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [mobileMenuOpen]);

  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-blue-500/30 font-sans">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#050505]/80 backdrop-blur-xl border-b border-white/5 px-4 sm:px-6 py-3 sm:py-4">
        <div className="max-w-[1400px] mx-auto flex justify-between items-center">
          <Link href="/" className="hover:opacity-80 transition-opacity flex-shrink-0">
            <PureCortexLogo />
          </Link>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-4 lg:gap-8">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-1.5 text-xs lg:text-sm font-bold uppercase tracking-wider lg:tracking-widest transition-colors whitespace-nowrap ${
                    isActive ? 'text-[#007AFF]' : 'text-gray-500 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" /> {item.label}
                </Link>
              );
            })}

            <div className="h-4 w-[1px] bg-white/10 hidden lg:block" />

            <div className="hidden lg:flex items-center gap-6">
              <Link href="/docs/sdk" className="text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">SDK</Link>
              <Link href="/docs/api" className="text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">Docs</Link>
            </div>
          </div>

          <div className="flex items-center gap-2 sm:gap-4">
            <div className="hidden lg:flex items-center gap-2">
              <a href="https://github.com/chaosoracleforall-agent/purecortexai" target="_blank" rel="noopener noreferrer" aria-label="GitHub" className="p-2 text-gray-500 hover:text-white transition-colors">
                <Github className="w-4 h-4" />
              </a>
              <a href="https://x.com/purecortexai" target="_blank" rel="noopener noreferrer" aria-label="X (Twitter)" className="p-2 text-gray-500 hover:text-white transition-colors">
                <svg viewBox="0 0 24 24" className="w-4 h-4 fill-current" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
              </a>
            </div>
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-bold text-emerald-500 uppercase font-mono">
              <ShieldCheck className="w-3.5 h-3.5" /> Testnet Active
            </div>
            <div className="hidden sm:block">
              <WalletButton />
            </div>

            {/* Mobile menu button */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              aria-label="Toggle menu"
              className="md:hidden p-2 text-gray-400 hover:text-white transition-colors"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
            </button>
          </div>
        </div>
      </nav>

      {/* Mobile menu overlay */}
      <AnimatePresence>
        {mobileMenuOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMobileMenuOpen(false)}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.25 }}
              className="fixed top-0 right-0 bottom-0 z-40 w-72 bg-[#0A0A0A] border-l border-white/5 pt-20 px-6 md:hidden overflow-y-auto"
            >
              <div className="space-y-1">
                {NAV_ITEMS.map((item) => {
                  const Icon = item.icon;
                  const isActive = pathname === item.href;
                  return (
                    <Link
                      key={item.href}
                      href={item.href}
                      onClick={() => setMobileMenuOpen(false)}
                      className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-bold uppercase tracking-wider transition-all ${
                        isActive
                          ? 'text-[#007AFF] bg-[#007AFF]/10'
                          : 'text-gray-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      <Icon className="w-5 h-5" /> {item.label}
                    </Link>
                  );
                })}
              </div>

              <div className="mt-6 pt-6 border-t border-white/5 space-y-1">
                <Link href="/docs/sdk" onClick={() => setMobileMenuOpen(false)} className="block px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">SDK</Link>
                <Link href="/docs/api" onClick={() => setMobileMenuOpen(false)} className="block px-4 py-2.5 text-xs font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">Docs</Link>
              </div>

              <div className="mt-6 pt-6 border-t border-white/5">
                <WalletButton />
              </div>

              <div className="mt-4 flex items-center gap-4 px-4">
                <a href="https://github.com/chaosoracleforall-agent/purecortexai" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white transition-colors">
                  <Github className="w-5 h-5" />
                </a>
                <a href="https://x.com/purecortexai" target="_blank" rel="noopener noreferrer" className="text-gray-500 hover:text-white transition-colors">
                  <svg viewBox="0 0 24 24" className="w-5 h-5 fill-current" aria-hidden="true"><path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" /></svg>
                </a>
              </div>
              <div className="mt-3 flex items-center gap-1.5 px-4 py-2 text-[10px] font-bold text-emerald-500 uppercase font-mono">
                <ShieldCheck className="w-3.5 h-3.5" /> Testnet Active
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Dashboard Content */}
      <main className="max-w-[1400px] mx-auto px-4 sm:px-6 pt-24 sm:pt-32 pb-24 sm:pb-32 w-full">
        {children}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-[#050505]/90 backdrop-blur-md border-t border-white/5 px-4 sm:px-6 py-2 sm:py-3 z-30">
        <div className="max-w-[1400px] mx-auto flex flex-col sm:flex-row justify-between items-center text-[9px] sm:text-[10px] font-mono text-gray-600 uppercase tracking-widest gap-1 sm:gap-2">
          <div className="flex items-center gap-4 sm:gap-6">
            <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> API: Operational</span>
            <span className="hidden sm:flex items-center gap-2 text-[#007AFF]"><div className="w-1.5 h-1.5 rounded-full bg-[#007AFF]" /> Consensus: Active</span>
          </div>
          <div className="flex items-center gap-3 sm:gap-4">
            <Link href="/docs/terms" className="hover:text-white transition-colors">Terms</Link>
            <Link href="/docs/privacy" className="hover:text-white transition-colors">Privacy</Link>
            <span className="hidden sm:block">PURECORTEX v0.7.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
