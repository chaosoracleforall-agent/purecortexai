'use client';

import Link from 'next/link';
import type { ComponentType, FormEvent } from 'react';
import { useMemo, useState } from 'react';
import { ArrowLeft, CheckCircle2, KeyRound, LockKeyhole, Shield, TerminalSquare } from 'lucide-react';

import { fetchJson } from '@/lib/api';
import { PureCortexLogo } from '@/components/Logo';


type AccessLevel = 'read' | 'write' | 'custom';
type Surface = 'api' | 'cli' | 'python_sdk' | 'typescript_sdk' | 'mcp';

interface DeveloperAccessResponse {
  id: string;
  status: string;
  requester_name: string;
  requester_email: string;
  requested_access_level: string;
  requested_surfaces: string[];
  requested_ips: string[];
  expected_rpm: number | null;
  created_at: string;
  message: string;
}

const SURFACE_OPTIONS: Array<{ value: Surface; label: string; detail: string }> = [
  { value: 'api', label: 'REST API', detail: 'Direct HTTPS integrations and server-to-server access.' },
  { value: 'cli', label: 'CLI', detail: 'Operator workflows using `pcx`.' },
  { value: 'python_sdk', label: 'Python SDK', detail: 'Programmatic backend or agent integrations.' },
  { value: 'typescript_sdk', label: 'TypeScript SDK', detail: 'Node.js and browser-based integrations.' },
  { value: 'mcp', label: 'MCP', detail: 'Future hosted MCP access under the same key model.' },
];

const ACCESS_CARDS: Array<{
  value: AccessLevel;
  title: string;
  icon: ComponentType<{ className?: string }>;
  detail: string;
}> = [
  {
    value: 'read',
    title: 'Read',
    icon: KeyRound,
    detail: 'Observability, registry, transparency, and low-risk integration workflows.',
  },
  {
    value: 'write',
    title: 'Write',
    icon: LockKeyhole,
    detail: 'Higher-trust workflows. Strongly recommended to pair with IP allowlists.',
  },
  {
    value: 'custom',
    title: 'Custom',
    icon: Shield,
    detail: 'Use this for special scope, rate, or enterprise policy requirements.',
  },
];

function accessLabel(value: string): string {
  return value.charAt(0).toUpperCase() + value.slice(1);
}

export default function DeveloperAccessPage() {
  const [requesterName, setRequesterName] = useState('');
  const [requesterEmail, setRequesterEmail] = useState('');
  const [organization, setOrganization] = useState('');
  const [useCase, setUseCase] = useState('');
  const [expectedRpm, setExpectedRpm] = useState('');
  const [requestedIps, setRequestedIps] = useState('');
  const [accessLevel, setAccessLevel] = useState<AccessLevel>('read');
  const [selectedSurfaces, setSelectedSurfaces] = useState<Surface[]>(['api', 'cli']);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [result, setResult] = useState<DeveloperAccessResponse | null>(null);

  const parsedIps = useMemo(
    () =>
      requestedIps
        .split('\n')
        .map((line) => line.trim())
        .filter(Boolean),
    [requestedIps]
  );

  const toggleSurface = (surface: Surface) => {
    setSelectedSurfaces((prev) => {
      if (prev.includes(surface)) {
        return prev.filter((item) => item !== surface);
      }
      return [...prev, surface];
    });
  };

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);

    if (selectedSurfaces.length === 0) {
      setError('Select at least one surface: API, CLI, SDK, or MCP.');
      return;
    }

    setIsSubmitting(true);
    try {
      const response = await fetchJson<DeveloperAccessResponse>('/api/developer-access/requests', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          requester_name: requesterName,
          requester_email: requesterEmail,
          organization: organization || null,
          use_case: useCase,
          requested_surfaces: selectedSurfaces,
          requested_access_level: accessLevel,
          requested_ips: parsedIps,
          expected_rpm: expectedRpm ? Number(expectedRpm) : null,
        }),
      });
      setResult(response);
    } catch (submitError) {
      setError(submitError instanceof Error ? submitError.message : 'Failed to submit request.');
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#050505] text-white font-sans">
      <div className="absolute top-0 left-1/4 w-[420px] h-[420px] bg-[#007AFF]/5 blur-[140px] rounded-full -z-10" />
      <div className="absolute bottom-0 right-1/4 w-[420px] h-[420px] bg-blue-500/5 blur-[160px] rounded-full -z-10" />

      <div className="max-w-6xl mx-auto px-6 py-8 sm:py-10">
        <div className="flex items-center justify-between gap-4">
          <Link href="/" className="hover:opacity-80 transition-opacity">
            <PureCortexLogo />
          </Link>
          <Link
            href="/"
            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-gray-500 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Back
          </Link>
        </div>

        <div className="mt-12 grid gap-10 lg:grid-cols-[1.1fr_0.9fr]">
          <section className="space-y-8">
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#007AFF]/20 bg-[#007AFF]/10 px-4 py-2 text-[10px] font-bold uppercase tracking-[0.25em] text-[#007AFF]">
                <TerminalSquare className="w-3.5 h-3.5" /> Developer Access
              </div>
              <h1 className="text-4xl sm:text-6xl font-black tracking-tighter uppercase italic leading-[0.95]">
                Request API,
                <br />
                CLI & SDK Access
              </h1>
              <p className="max-w-2xl text-base sm:text-lg text-gray-400 leading-relaxed">
                One key model will power PURECORTEX API, CLI, Python SDK, TypeScript SDK, and future
                hosted MCP access. Submit your intended usage, requested access level, and optional IP
                allowlist requirements for manual review.
              </p>
            </div>

            <div className="grid gap-4 md:grid-cols-3">
              {ACCESS_CARDS.map((card) => {
                const Icon = card.icon;
                const selected = accessLevel === card.value;
                return (
                  <button
                    key={card.value}
                    type="button"
                    onClick={() => setAccessLevel(card.value)}
                    className={`rounded-2xl border p-5 text-left transition-all ${
                      selected
                        ? 'border-[#007AFF]/40 bg-[#007AFF]/10'
                        : 'border-white/5 bg-white/[0.03] hover:border-white/15'
                    }`}
                  >
                    <div className="flex items-center gap-3">
                      <div className="rounded-xl border border-white/10 bg-black/30 p-2.5">
                        <Icon className="w-5 h-5 text-[#007AFF]" />
                      </div>
                      <div>
                        <div className="text-sm font-black uppercase tracking-wider">{card.title}</div>
                        <div className="text-xs text-gray-500 uppercase tracking-[0.2em]">Access level</div>
                      </div>
                    </div>
                    <p className="mt-4 text-sm text-gray-400 leading-relaxed">{card.detail}</p>
                  </button>
                );
              })}
            </div>

            <form onSubmit={handleSubmit} className="space-y-6 rounded-[28px] border border-white/5 bg-[#121212] p-6 sm:p-8">
              <div className="grid gap-5 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Name</span>
                  <input
                    required
                    value={requesterName}
                    onChange={(event) => setRequesterName(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none transition focus:border-[#007AFF]/40"
                    placeholder="Your name"
                  />
                </label>

                <label className="space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Email</span>
                  <input
                    required
                    type="email"
                    value={requesterEmail}
                    onChange={(event) => setRequesterEmail(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none transition focus:border-[#007AFF]/40"
                    placeholder="you@example.com"
                  />
                </label>

                <label className="space-y-2 md:col-span-2">
                  <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Organization</span>
                  <input
                    value={organization}
                    onChange={(event) => setOrganization(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none transition focus:border-[#007AFF]/40"
                    placeholder="Optional"
                  />
                </label>
              </div>

              <div className="space-y-3">
                <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Intended surfaces</div>
                <div className="grid gap-3 sm:grid-cols-2">
                  {SURFACE_OPTIONS.map((surface) => {
                    const selected = selectedSurfaces.includes(surface.value);
                    return (
                      <button
                        key={surface.value}
                        type="button"
                        onClick={() => toggleSurface(surface.value)}
                        className={`rounded-2xl border p-4 text-left transition-all ${
                          selected
                            ? 'border-[#007AFF]/40 bg-[#007AFF]/10'
                            : 'border-white/10 bg-black/20 hover:border-white/20'
                        }`}
                      >
                        <div className="flex items-center justify-between gap-3">
                          <div className="text-sm font-bold uppercase tracking-wide">{surface.label}</div>
                          {selected && <CheckCircle2 className="w-4 h-4 text-[#007AFF]" />}
                        </div>
                        <div className="mt-2 text-sm text-gray-400 leading-relaxed">{surface.detail}</div>
                      </button>
                    );
                  })}
                </div>
              </div>

              <label className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Use case</span>
                <textarea
                  required
                  rows={5}
                  value={useCase}
                  onChange={(event) => setUseCase(event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none transition focus:border-[#007AFF]/40"
                  placeholder="Describe your integration, intended workloads, and whether you need read, write, or custom policy requirements."
                />
              </label>

              <div className="grid gap-5 md:grid-cols-2">
                <label className="space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Expected requests per minute</span>
                  <input
                    type="number"
                    min={1}
                    max={100000}
                    value={expectedRpm}
                    onChange={(event) => setExpectedRpm(event.target.value)}
                    className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none transition focus:border-[#007AFF]/40"
                    placeholder="Optional"
                  />
                </label>

                <label className="space-y-2">
                  <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Requested access level</span>
                  <div className="rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm text-white">
                    {accessLabel(accessLevel)}
                  </div>
                </label>
              </div>

              <label className="space-y-2">
                <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">IP allowlist entries</span>
                <textarea
                  rows={4}
                  value={requestedIps}
                  onChange={(event) => setRequestedIps(event.target.value)}
                  className="w-full rounded-2xl border border-white/10 bg-black/30 px-4 py-3 text-sm outline-none transition focus:border-[#007AFF]/40"
                  placeholder={`One IP or CIDR per line\n203.0.113.10\n198.51.100.0/24`}
                />
                <p className="text-sm text-gray-500 leading-relaxed">
                  Recommended for fixed servers, CI runners, and office networks. Dynamic home IPs can
                  break CLI and SDK flows unless you update the allowlist.
                </p>
              </label>

              {error && (
                <div className="rounded-2xl border border-red-500/30 bg-red-500/10 px-4 py-3 text-sm text-red-200">
                  {error}
                </div>
              )}

              {result && (
                <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-5 py-4 text-sm text-emerald-100 space-y-2">
                  <div className="font-bold uppercase tracking-[0.2em] text-emerald-300">Request submitted</div>
                  <div>{result.message}</div>
                  <div className="font-mono text-emerald-200">Request ID: {result.id}</div>
                </div>
              )}

              <button
                type="submit"
                disabled={isSubmitting}
                className="inline-flex items-center justify-center rounded-2xl bg-white px-6 py-4 text-sm font-black uppercase tracking-wider text-black transition hover:bg-gray-200 disabled:cursor-not-allowed disabled:opacity-60"
              >
                {isSubmitting ? 'Submitting request...' : 'Request access'}
              </button>
            </form>
          </section>

          <aside className="space-y-6">
            <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6 sm:p-8">
              <div className="flex items-center gap-3">
                <Shield className="w-5 h-5 text-[#007AFF]" />
                <h2 className="text-lg font-black uppercase tracking-tight italic">Security Notes</h2>
              </div>
              <ul className="mt-5 space-y-4 text-sm text-gray-400 leading-relaxed">
                <li>One approved key model will cover API, CLI, Python SDK, and TypeScript SDK usage.</li>
                <li>Write-enabled access is reviewed more strictly and should usually include IP restrictions.</li>
                <li>Hosted MCP access will adopt the same key model once the remote transport is enabled.</li>
                <li>Approval is manual and tied to intended use, traffic profile, and security posture.</li>
              </ul>
            </div>

            <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6 sm:p-8">
              <div className="flex items-center gap-3">
                <KeyRound className="w-5 h-5 text-[#007AFF]" />
                <h2 className="text-lg font-black uppercase tracking-tight italic">What happens next</h2>
              </div>
              <ol className="mt-5 space-y-4 text-sm text-gray-400 leading-relaxed">
                <li>1. Your request is queued for owner review.</li>
                <li>2. Requested surfaces, access level, and IP restrictions are assessed.</li>
                <li>3. Approved keys will be issued with enterprise-grade controls and auditability.</li>
              </ol>
            </div>
          </aside>
        </div>
      </div>
    </div>
  );
}
