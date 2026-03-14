import Link from 'next/link';
import { PureCortexLogo } from '@/components/Logo';

const DOC_NAV = [
  { slug: 'api', label: 'API' },
  { slug: 'mcp', label: 'MCP' },
  { slug: 'cli', label: 'CLI' },
  { slug: 'terms', label: 'Terms' },
  { slug: 'privacy', label: 'Privacy' },
];

export default function DocsLayout({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans">
      {/* Header */}
      <nav className="fixed top-0 left-0 right-0 z-50 bg-[#050505]/90 backdrop-blur-xl border-b border-white/5 px-6 py-4">
        <div className="max-w-5xl mx-auto flex justify-between items-center">
          <Link href="/" className="hover:opacity-80 transition-opacity">
            <PureCortexLogo />
          </Link>
          <div className="flex items-center gap-6">
            {DOC_NAV.map((doc) => (
              <Link
                key={doc.slug}
                href={`/docs/${doc.slug}`}
                className="text-[10px] font-bold uppercase tracking-widest text-gray-500 hover:text-[#007AFF] transition-colors"
              >
                {doc.label}
              </Link>
            ))}
          </div>
        </div>
      </nav>

      {/* Content */}
      <main className="max-w-4xl mx-auto px-6 pt-28 pb-20">
        {children}
      </main>

      {/* Footer */}
      <footer className="border-t border-white/5 px-6 py-6">
        <div className="max-w-4xl mx-auto flex justify-between items-center text-[9px] font-mono text-gray-600 uppercase tracking-widest">
          <Link href="/" className="hover:text-white transition-colors">
            Back to PureCortex
          </Link>
          <span>v0.6.0</span>
        </div>
      </footer>
    </div>
  );
}
