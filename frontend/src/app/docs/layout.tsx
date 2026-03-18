'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PureCortexLogo } from '@/components/Logo';
import { Menu, X, ArrowLeft } from 'lucide-react';
import { useState, useEffect, useCallback, useRef } from 'react';
import { AnimatePresence, motion } from 'framer-motion';

const DOC_NAV = [
  { slug: 'sdk', label: 'SDK' },
  { slug: 'api', label: 'API' },
  { slug: 'mcp', label: 'MCP' },
  { slug: 'cli', label: 'CLI' },
  { slug: 'terms', label: 'Terms' },
  { slug: 'privacy', label: 'Privacy' },
];

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const [menuOpen, setMenuOpen] = useState(false);
  const previousPathnameRef = useRef(pathname);

  useEffect(() => {
    if (previousPathnameRef.current !== pathname) {
      previousPathnameRef.current = pathname;
      queueMicrotask(() => setMenuOpen(false));
    }
  }, [pathname]);

  const handleEscape = useCallback((e: KeyboardEvent) => {
    if (e.key === 'Escape') setMenuOpen(false);
  }, []);

  useEffect(() => {
    document.addEventListener('keydown', handleEscape);
    return () => document.removeEventListener('keydown', handleEscape);
  }, [handleEscape]);

  useEffect(() => {
    if (menuOpen) {
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => { document.body.style.overflow = ''; };
  }, [menuOpen]);

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans">
      {/* Header */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#050505]/90 backdrop-blur-xl border-b border-white/5 px-4 sm:px-6 py-3 sm:py-4">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <div className="flex items-center gap-3 sm:gap-4">
            <Link href="/marketplace" className="p-1.5 text-gray-500 hover:text-white transition-colors" aria-label="Back to dashboard">
              <ArrowLeft className="w-4 h-4 sm:w-5 sm:h-5" />
            </Link>
            <Link href="/" className="hover:opacity-80 transition-opacity">
              <PureCortexLogo />
            </Link>
          </div>

          {/* Desktop nav */}
          <div className="hidden md:flex items-center gap-4 lg:gap-6">
            {DOC_NAV.map((doc) => {
              const isActive = pathname === `/docs/${doc.slug}`;
              return (
                <Link
                  key={doc.slug}
                  href={`/docs/${doc.slug}`}
                  className={`text-[10px] font-bold uppercase tracking-widest transition-colors ${
                    isActive ? 'text-[#007AFF]' : 'text-gray-500 hover:text-white'
                  }`}
                >
                  {doc.label}
                </Link>
              );
            })}
          </div>

          {/* Mobile menu button */}
          <button
            onClick={() => setMenuOpen(!menuOpen)}
            aria-label="Toggle docs menu"
            className="md:hidden p-2 text-gray-400 hover:text-white transition-colors"
          >
            {menuOpen ? <X className="w-5 h-5" /> : <Menu className="w-5 h-5" />}
          </button>
        </div>
      </nav>

      {/* Mobile menu overlay */}
      <AnimatePresence>
        {menuOpen && (
          <>
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              onClick={() => setMenuOpen(false)}
              className="fixed inset-0 z-40 bg-black/60 backdrop-blur-sm md:hidden"
            />
            <motion.div
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ type: 'tween', duration: 0.25 }}
              className="fixed top-0 right-0 bottom-0 z-40 w-64 bg-[#0A0A0A] border-l border-white/5 pt-20 px-6 md:hidden overflow-y-auto"
            >
              <p className="text-[9px] font-bold text-gray-600 uppercase tracking-widest mb-3 px-3">Documentation</p>
              <div className="space-y-1">
                {DOC_NAV.map((doc) => {
                  const isActive = pathname === `/docs/${doc.slug}`;
                  return (
                    <Link
                      key={doc.slug}
                      href={`/docs/${doc.slug}`}
                      onClick={() => setMenuOpen(false)}
                      className={`block px-3 py-2.5 rounded-xl text-sm font-bold uppercase tracking-wider transition-all ${
                        isActive
                          ? 'text-[#007AFF] bg-[#007AFF]/10'
                          : 'text-gray-400 hover:text-white hover:bg-white/5'
                      }`}
                    >
                      {doc.label}
                    </Link>
                  );
                })}
              </div>

              <div className="mt-6 pt-6 border-t border-white/5">
                <Link
                  href="/marketplace"
                  onClick={() => setMenuOpen(false)}
                  className="flex items-center gap-2 px-3 py-2.5 text-sm font-bold text-gray-400 hover:text-white transition-colors"
                >
                  <ArrowLeft className="w-4 h-4" /> Back to Dashboard
                </Link>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>

      {/* Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 pt-24 sm:pt-28 pb-16 sm:pb-20">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 px-4 sm:px-6 py-4 sm:py-6">
        <div className="max-w-4xl mx-auto flex justify-between items-center text-[9px] font-mono text-gray-600 uppercase tracking-widest">
          <Link href="/marketplace" className="hover:text-white transition-colors">
            Back to PURECORTEX
          </Link>
          <span>v0.7.0</span>
        </div>
      </footer>
    </div>
  );
}
