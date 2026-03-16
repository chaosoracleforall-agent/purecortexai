'use client';

import Link from 'next/link';
import { FormEvent, useState } from 'react';

import { PureCortexLogo } from '@/components/Logo';

export default function AdminLoginPage() {
  const [email, setEmail] = useState('chaosoracleforall@gmail.com');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSubmitting(true);
    setError(null);

    try {
      const response = await fetch('/admin-api/dev-session', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email }),
      });
      const payload = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(payload?.detail || 'Local admin sign-in failed');
      }
      window.location.href = '/admin';
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Local admin sign-in failed');
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans">
      <div className="absolute top-0 left-1/4 w-[420px] h-[420px] bg-[#007AFF]/5 blur-[140px] rounded-full -z-10" />
      <div className="absolute bottom-0 right-1/4 w-[420px] h-[420px] bg-blue-500/5 blur-[160px] rounded-full -z-10" />

      <div className="max-w-2xl mx-auto px-6 py-10 space-y-8">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="hover:opacity-80 transition-opacity">
            <PureCortexLogo />
          </Link>
          <Link
            href="/admin"
            className="text-xs font-bold uppercase tracking-[0.2em] text-gray-500 hover:text-white transition-colors"
          >
            Back to Admin
          </Link>
        </div>

        <div className="rounded-[28px] border border-white/5 bg-[#121212] p-8 space-y-6">
          <div className="space-y-3">
            <div className="inline-flex items-center rounded-full border border-[#007AFF]/20 bg-[#007AFF]/10 px-4 py-2 text-[10px] font-bold uppercase tracking-[0.25em] text-[#007AFF]">
              Local Admin Login
            </div>
            <h1 className="text-4xl font-black tracking-tighter uppercase italic">Browser Admin Access</h1>
            <p className="text-sm text-gray-400 leading-relaxed">
              Local development can use a dev-only signed session cookie for the allowed owner email. This does not
              replace the production Google OAuth and reverse-proxy path.
            </p>
          </div>

          <form className="space-y-4" onSubmit={(event) => void handleSubmit(event)}>
            <label className="space-y-2 block">
              <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Allowed Admin Email</span>
              <input
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                autoComplete="email"
              />
            </label>

            {error && (
              <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-100">
                {error}
              </div>
            )}

            <button
              type="submit"
              disabled={submitting}
              className="rounded-2xl bg-white px-5 py-3 text-xs font-black uppercase tracking-wider text-black transition hover:bg-gray-200 disabled:opacity-50"
            >
              {submitting ? 'Signing In...' : 'Continue to Admin'}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
