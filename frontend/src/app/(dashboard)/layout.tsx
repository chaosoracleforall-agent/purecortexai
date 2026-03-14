'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { PureCortexLogo } from '@/components/Logo';
import WalletButton from '@/components/WalletButton';
import { BarChart3, MessageSquare, Eye, Scale, ShieldCheck } from 'lucide-react';

const NAV_ITEMS = [
  { href: '/marketplace', label: 'Marketplace', icon: BarChart3 },
  { href: '/chat', label: 'Neural Link', icon: MessageSquare },
  { href: '/governance', label: 'Governance', icon: Scale },
  { href: '/transparency', label: 'Transparency', icon: Eye },
];

export default function DashboardLayout({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  return (
    <div className="min-h-screen bg-[#050505] text-white selection:bg-blue-500/30 font-sans">
      {/* Navigation */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#050505]/80 backdrop-blur-xl border-b border-white/5 px-6 py-4">
        <div className="max-w-[1400px] mx-auto flex justify-between items-center">
          <Link href="/" className="hover:opacity-80 transition-opacity">
            <PureCortexLogo />
          </Link>

          <div className="hidden md:flex items-center gap-8">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`flex items-center gap-2 text-sm font-bold uppercase tracking-widest transition-colors ${
                    isActive ? 'text-[#007AFF]' : 'text-gray-500 hover:text-white'
                  }`}
                >
                  <Icon className="w-4 h-4" /> {item.label}
                </Link>
              );
            })}

            <div className="h-4 w-[1px] bg-white/10 hidden lg:block" />

            <div className="hidden lg:flex items-center gap-6">
              <Link href="/docs/api" className="text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">API</Link>
              <Link href="/docs/mcp" className="text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">MCP</Link>
              <Link href="/docs/cli" className="text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors">CLI</Link>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <div className="hidden sm:flex items-center gap-1.5 px-3 py-1.5 rounded-lg bg-emerald-500/10 border border-emerald-500/20 text-[10px] font-bold text-emerald-500 uppercase font-mono">
              <ShieldCheck className="w-3.5 h-3.5" /> Testnet Active
            </div>
            <WalletButton />
          </div>
        </div>
      </nav>

      {/* Dashboard Content */}
      <main className="max-w-[1400px] mx-auto px-6 pt-32 pb-32 w-full">
        {children}
      </main>

      {/* Footer */}
      <footer className="fixed bottom-0 left-0 right-0 bg-[#050505]/90 backdrop-blur-md border-t border-white/5 px-6 py-3">
        <div className="max-w-[1400px] mx-auto flex flex-col md:flex-row justify-between items-center text-[10px] font-mono text-gray-600 uppercase tracking-widest gap-2">
          <div className="flex items-center gap-6">
            <span className="flex items-center gap-2"><div className="w-1.5 h-1.5 rounded-full bg-emerald-500" /> API: Operational</span>
            <span className="flex items-center gap-2 text-[#007AFF]"><div className="w-1.5 h-1.5 rounded-full bg-[#007AFF]" /> Consensus: Active</span>
          </div>
          <div className="flex items-center gap-4">
            <span className="text-[8px] opacity-40">Complete Creator Indemnity.</span>
            <Link href="/docs/terms" className="hover:text-white transition-colors">Terms</Link>
            <Link href="/docs/privacy" className="hover:text-white transition-colors">Privacy</Link>
            <span className="hidden sm:block">PureCortex v0.6.0</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
