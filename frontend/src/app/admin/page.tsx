'use client';

import Link from 'next/link';
import { useEffect, useState } from 'react';
import { ArrowLeft, Database, KeyRound, ShieldCheck, UserCog } from 'lucide-react';

import { PureCortexLogo } from '@/components/Logo';


interface ControlPlaneHealth {
  status: string;
  surface: string;
  owner_emails: string[];
  database_configured: boolean;
  oauth_configured: boolean;
  ip_trust_configured: boolean;
}

interface AccessRequestSummary {
  id: string;
  requester_name: string;
  requester_email: string;
  requested_access_level: string;
  requested_surfaces: string[];
  status: string;
  created_at: string;
}

export default function AdminPage() {
  const [health, setHealth] = useState<ControlPlaneHealth | null>(null);
  const [requests, setRequests] = useState<AccessRequestSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [healthResp, requestsResp] = await Promise.all([
          fetch('/admin-api/control-plane', { cache: 'no-store' }),
          fetch('/admin-api/requests?limit=10', { cache: 'no-store' }),
        ]);

        const healthBody = await healthResp.json();
        const requestsBody = await requestsResp.json();

        if (!active) {
          return;
        }

        if (!healthResp.ok) {
          setError(healthBody?.detail || 'Admin dashboard unavailable');
          return;
        }

        setHealth(healthBody);
        setRequests(Array.isArray(requestsBody?.requests) ? requestsBody.requests : []);
        setError(null);
      } catch (loadError) {
        if (!active) {
          return;
        }
        setError(loadError instanceof Error ? loadError.message : 'Admin dashboard unavailable');
      } finally {
        if (active) {
          setLoading(false);
        }
      }
    }

    void load();
    return () => {
      active = false;
    };
  }, []);

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
            href="/developers/access"
            className="inline-flex items-center gap-2 text-xs font-bold uppercase tracking-[0.2em] text-gray-500 hover:text-white transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Developer Access
          </Link>
        </div>

        <div className="mt-12 space-y-8">
          <div className="space-y-4">
            <div className="inline-flex items-center gap-2 rounded-full border border-[#007AFF]/20 bg-[#007AFF]/10 px-4 py-2 text-[10px] font-bold uppercase tracking-[0.25em] text-[#007AFF]">
              <UserCog className="w-3.5 h-3.5" /> Admin Control Plane
            </div>
            <h1 className="text-4xl sm:text-6xl font-black tracking-tighter uppercase italic leading-[0.95]">
              Owner Dashboard
            </h1>
            <p className="max-w-3xl text-base sm:text-lg text-gray-400 leading-relaxed">
              This route is designed for owner-only Google SSO access. Until the proxy-side SSO boundary
              is fully enabled, the dashboard only reveals internal control-plane data when the trusted
              admin identity header and server-side admin token are present.
            </p>
          </div>

          {loading ? (
            <div className="rounded-[28px] border border-white/5 bg-[#121212] p-8 text-sm text-gray-400">
              Loading admin control plane...
            </div>
          ) : error ? (
            <div className="rounded-[28px] border border-yellow-500/30 bg-yellow-500/10 p-8 text-sm text-yellow-100 space-y-3">
              <div className="font-bold uppercase tracking-[0.2em] text-yellow-300">Protected Surface</div>
              <p>{error}</p>
              <p className="text-yellow-50/80">
                Expected production path: Nginx strips any spoofed admin header, oauth2-proxy authenticates
                the owner, then the trusted email is forwarded to the frontend.
              </p>
            </div>
          ) : (
            <>
              <div className="grid gap-4 md:grid-cols-3">
                <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6">
                  <div className="flex items-center gap-3">
                    <Database className="w-5 h-5 text-[#007AFF]" />
                    <div className="text-sm font-black uppercase tracking-wide">Database</div>
                  </div>
                  <div className="mt-4 text-2xl font-black tracking-tight">
                    {health?.database_configured ? 'Ready' : 'Pending'}
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6">
                  <div className="flex items-center gap-3">
                    <ShieldCheck className="w-5 h-5 text-[#007AFF]" />
                    <div className="text-sm font-black uppercase tracking-wide">SSO</div>
                  </div>
                  <div className="mt-4 text-2xl font-black tracking-tight">
                    {health?.oauth_configured ? 'Ready' : 'Pending'}
                  </div>
                </div>

                <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6">
                  <div className="flex items-center gap-3">
                    <KeyRound className="w-5 h-5 text-[#007AFF]" />
                    <div className="text-sm font-black uppercase tracking-wide">Requests</div>
                  </div>
                  <div className="mt-4 text-2xl font-black tracking-tight">{requests.length}</div>
                </div>
              </div>

              <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6 sm:p-8">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-black uppercase tracking-tight italic">Recent Requests</h2>
                    <p className="mt-2 text-sm text-gray-500">
                      This is the first backend-backed admin view. Approval, issuance, allowlist editing,
                      revoke, and rotate flows will sit on top of this surface next.
                    </p>
                  </div>
                </div>

                <div className="mt-6 space-y-3">
                  {requests.length === 0 ? (
                    <div className="rounded-2xl border border-white/5 bg-black/20 px-4 py-5 text-sm text-gray-500">
                      No requests recorded yet, or the enterprise database has not been seeded.
                    </div>
                  ) : (
                    requests.map((request) => (
                      <div
                        key={request.id}
                        className="rounded-2xl border border-white/5 bg-black/20 px-4 py-4 flex flex-col gap-2 sm:flex-row sm:items-center sm:justify-between"
                      >
                        <div>
                          <div className="text-sm font-bold text-white">{request.requester_name}</div>
                          <div className="text-xs text-gray-500">{request.requester_email}</div>
                        </div>
                        <div className="text-xs uppercase tracking-[0.2em] text-gray-500">
                          {request.requested_access_level} · {request.requested_surfaces.join(', ')}
                        </div>
                        <div className="text-xs uppercase tracking-[0.2em] text-[#007AFF]">{request.status}</div>
                      </div>
                    ))
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
