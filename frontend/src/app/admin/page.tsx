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
  organization: string | null;
  requested_access_level: string;
  requested_surfaces: string[];
  requested_ips: string[];
  use_case: string;
  status: string;
  review_notes: string | null;
  issued_key_id: string | null;
  created_at: string;
}

interface APIKeySummary {
  id: string;
  key_id: string;
  key_prefix: string;
  label: string | null;
  owner_name: string;
  owner_email: string;
  status: string;
  access_level: string;
  scopes: string[];
  intended_surfaces: string[];
  rate_limit_profile: string;
  expires_at: string | null;
  last_used_at: string | null;
  last_used_ip: string | null;
  override_no_ip_allowlist: boolean;
  notes: string | null;
  ip_allowlists: Array<{ cidr: string; label: string | null }>;
}

function parseAllowlistText(value: string): Array<{ cidr: string; label: string | null }> {
  return value
    .split('\n')
    .map((line) => line.trim())
    .filter(Boolean)
    .map((cidr) => ({ cidr, label: null }));
}

function parseScopes(value: string): string[] {
  return value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean);
}

function stringifyAllowlists(entries: Array<{ cidr: string }>): string {
  return entries.map((entry) => entry.cidr).join('\n');
}

export default function AdminPage() {
  const [health, setHealth] = useState<ControlPlaneHealth | null>(null);
  const [requests, setRequests] = useState<AccessRequestSummary[]>([]);
  const [apiKeys, setApiKeys] = useState<APIKeySummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [operationError, setOperationError] = useState<string | null>(null);
  const [flash, setFlash] = useState<string | null>(null);
  const [revealedSecrets, setRevealedSecrets] = useState<Record<string, string>>({});
  const [requestReviewNotes, setRequestReviewNotes] = useState<Record<string, string>>({});
  const [requestLabels, setRequestLabels] = useState<Record<string, string>>({});
  const [requestAllowlists, setRequestAllowlists] = useState<Record<string, string>>({});
  const [requestExpiryDays, setRequestExpiryDays] = useState<Record<string, string>>({});
  const [requestActionState, setRequestActionState] = useState<Record<string, string>>({});
  const [keyScopes, setKeyScopes] = useState<Record<string, string>>({});
  const [keyAllowlists, setKeyAllowlists] = useState<Record<string, string>>({});
  const [keyNotes, setKeyNotes] = useState<Record<string, string>>({});
  const [keyReasons, setKeyReasons] = useState<Record<string, string>>({});
  const [keyLabels, setKeyLabels] = useState<Record<string, string>>({});
  const [keyOverrideIp, setKeyOverrideIp] = useState<Record<string, boolean>>({});
  const [keyActionState, setKeyActionState] = useState<Record<string, string>>({});

  useEffect(() => {
    let active = true;

    async function load() {
      try {
        const [healthResp, requestsResp, keysResp] = await Promise.all([
          fetch('/admin-api/control-plane', { cache: 'no-store' }),
          fetch('/admin-api/requests?limit=10', { cache: 'no-store' }),
          fetch('/admin-api/keys?limit=50', { cache: 'no-store' }),
        ]);

        const healthBody = await healthResp.json();
        const requestsBody = await requestsResp.json();
        const keysBody = await keysResp.json();

        if (!active) {
          return;
        }

        if (!healthResp.ok) {
          setError(healthBody?.detail || 'Admin dashboard unavailable');
          return;
        }

        setHealth(healthBody);
        const nextRequests = Array.isArray(requestsBody?.requests) ? requestsBody.requests : [];
        const nextKeys = Array.isArray(keysBody?.api_keys) ? keysBody.api_keys : [];
        setRequests(nextRequests);
        setApiKeys(nextKeys);
        setRequestAllowlists((prev) => ({
          ...Object.fromEntries(nextRequests.map((request: AccessRequestSummary) => [request.id, request.requested_ips.join('\n')])),
          ...prev,
        }));
        setRequestLabels((prev) => ({
          ...Object.fromEntries(nextRequests.map((request: AccessRequestSummary) => [request.id, `${request.requester_name} primary key`])),
          ...prev,
        }));
        setKeyScopes((prev) => ({
          ...Object.fromEntries(nextKeys.map((key: APIKeySummary) => [key.key_id, key.scopes.join(', ')])),
          ...prev,
        }));
        setKeyAllowlists((prev) => ({
          ...Object.fromEntries(nextKeys.map((key: APIKeySummary) => [key.key_id, stringifyAllowlists(key.ip_allowlists)])),
          ...prev,
        }));
        setKeyNotes((prev) => ({
          ...Object.fromEntries(nextKeys.map((key: APIKeySummary) => [key.key_id, key.notes || ''])),
          ...prev,
        }));
        setKeyLabels((prev) => ({
          ...Object.fromEntries(nextKeys.map((key: APIKeySummary) => [key.key_id, key.label || ''])),
          ...prev,
        }));
        setKeyOverrideIp((prev) => ({
          ...Object.fromEntries(nextKeys.map((key: APIKeySummary) => [key.key_id, key.override_no_ip_allowlist])),
          ...prev,
        }));
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

  useEffect(() => {
    setRequestAllowlists((prev) => ({
      ...Object.fromEntries(requests.map((request) => [request.id, request.requested_ips.join('\n')])),
      ...prev,
    }));
    setRequestLabels((prev) => ({
      ...Object.fromEntries(requests.map((request) => [request.id, `${request.requester_name} primary key`])),
      ...prev,
    }));
  }, [requests]);

  useEffect(() => {
    setKeyScopes((prev) => ({
      ...Object.fromEntries(apiKeys.map((key) => [key.key_id, key.scopes.join(', ')])),
      ...prev,
    }));
    setKeyAllowlists((prev) => ({
      ...Object.fromEntries(apiKeys.map((key) => [key.key_id, stringifyAllowlists(key.ip_allowlists)])),
      ...prev,
    }));
    setKeyNotes((prev) => ({
      ...Object.fromEntries(apiKeys.map((key) => [key.key_id, key.notes || ''])),
      ...prev,
    }));
    setKeyLabels((prev) => ({
      ...Object.fromEntries(apiKeys.map((key) => [key.key_id, key.label || ''])),
      ...prev,
    }));
    setKeyOverrideIp((prev) => ({
      ...Object.fromEntries(apiKeys.map((key) => [key.key_id, key.override_no_ip_allowlist])),
      ...prev,
    }));
  }, [apiKeys]);

  const pendingRequests = requests.filter((request) => request.status === 'pending');
  const activeKeys = apiKeys.filter((key) => key.status === 'active');

  async function reloadData() {
    setLoading(true);
    setError(null);
    try {
      const [healthResp, requestsResp, keysResp] = await Promise.all([
        fetch('/admin-api/control-plane', { cache: 'no-store' }),
        fetch('/admin-api/requests?limit=50', { cache: 'no-store' }),
        fetch('/admin-api/keys?limit=50', { cache: 'no-store' }),
      ]);
      const healthBody = await healthResp.json();
      const requestsBody = await requestsResp.json();
      const keysBody = await keysResp.json();
      if (!healthResp.ok) {
        throw new Error(healthBody?.detail || 'Admin dashboard unavailable');
      }
      setHealth(healthBody);
      setRequests(Array.isArray(requestsBody?.requests) ? requestsBody.requests : []);
      setApiKeys(Array.isArray(keysBody?.api_keys) ? keysBody.api_keys : []);
    } catch (reloadError) {
      setError(reloadError instanceof Error ? reloadError.message : 'Admin dashboard unavailable');
    } finally {
      setLoading(false);
    }
  }

  async function approveRequest(request: AccessRequestSummary) {
    setRequestActionState((prev) => ({ ...prev, [request.id]: 'approve' }));
    try {
      const response = await fetch(`/admin-api/requests/${request.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          review_notes: requestReviewNotes[request.id] || null,
          label: requestLabels[request.id] || null,
          ip_allowlists: parseAllowlistText(requestAllowlists[request.id] || ''),
          expires_in_days: requestExpiryDays[request.id] ? Number(requestExpiryDays[request.id]) : null,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || 'Failed to approve request');
      }
      const issuedKeyId = payload?.api_key?.key_id;
      const secret = payload?.secret;
      if (issuedKeyId && secret) {
        setRevealedSecrets((prev) => ({ ...prev, [issuedKeyId]: secret }));
      }
      setFlash(`Approved ${request.requester_email} and issued a new API key.`);
      setOperationError(null);
      await reloadData();
    } catch (approveError) {
      setOperationError(approveError instanceof Error ? approveError.message : 'Failed to approve request');
    } finally {
      setRequestActionState((prev) => ({ ...prev, [request.id]: '' }));
    }
  }

  async function rejectRequest(request: AccessRequestSummary) {
    setRequestActionState((prev) => ({ ...prev, [request.id]: 'reject' }));
    try {
      const response = await fetch(`/admin-api/requests/${request.id}/reject`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          review_notes: requestReviewNotes[request.id] || 'Rejected by owner review.',
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || 'Failed to reject request');
      }
      setFlash(`Rejected ${request.requester_email}.`);
      setOperationError(null);
      await reloadData();
    } catch (rejectError) {
      setOperationError(rejectError instanceof Error ? rejectError.message : 'Failed to reject request');
    } finally {
      setRequestActionState((prev) => ({ ...prev, [request.id]: '' }));
    }
  }

  async function saveKeyPolicy(key: APIKeySummary) {
    setKeyActionState((prev) => ({ ...prev, [key.key_id]: 'save' }));
    try {
      const response = await fetch(`/admin-api/keys/${key.key_id}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          label: keyLabels[key.key_id] || null,
          scopes: parseScopes(keyScopes[key.key_id] || ''),
          ip_allowlists: parseAllowlistText(keyAllowlists[key.key_id] || ''),
          notes: keyNotes[key.key_id] || null,
          override_no_ip_allowlist: keyOverrideIp[key.key_id] ?? false,
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || 'Failed to update API key policy');
      }
      setFlash(`Updated policy for ${key.key_id}.`);
      setOperationError(null);
      await reloadData();
    } catch (updateError) {
      setOperationError(updateError instanceof Error ? updateError.message : 'Failed to update API key policy');
    } finally {
      setKeyActionState((prev) => ({ ...prev, [key.key_id]: '' }));
    }
  }

  async function rotateKey(key: APIKeySummary) {
    setKeyActionState((prev) => ({ ...prev, [key.key_id]: 'rotate' }));
    try {
      const response = await fetch(`/admin-api/keys/${key.key_id}/rotate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason: keyReasons[key.key_id] || 'Routine rotation',
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || 'Failed to rotate API key');
      }
      const replacementKeyId = payload?.api_key?.key_id;
      const secret = payload?.secret;
      if (replacementKeyId && secret) {
        setRevealedSecrets((prev) => ({ ...prev, [replacementKeyId]: secret }));
      }
      setFlash(`Rotated ${key.key_id}. A new secret has been issued below.`);
      setOperationError(null);
      await reloadData();
    } catch (rotateError) {
      setOperationError(rotateError instanceof Error ? rotateError.message : 'Failed to rotate API key');
    } finally {
      setKeyActionState((prev) => ({ ...prev, [key.key_id]: '' }));
    }
  }

  async function revokeKey(key: APIKeySummary) {
    setKeyActionState((prev) => ({ ...prev, [key.key_id]: 'revoke' }));
    try {
      const response = await fetch(`/admin-api/keys/${key.key_id}/revoke`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          reason: keyReasons[key.key_id] || 'Owner revocation',
        }),
      });
      const payload = await response.json();
      if (!response.ok) {
        throw new Error(payload?.detail || 'Failed to revoke API key');
      }
      setFlash(`Revoked ${key.key_id}.`);
      setOperationError(null);
      await reloadData();
    } catch (revokeError) {
      setOperationError(revokeError instanceof Error ? revokeError.message : 'Failed to revoke API key');
    } finally {
      setKeyActionState((prev) => ({ ...prev, [key.key_id]: '' }));
    }
  }

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
              {error === 'Admin SSO required' && (
                <p className="text-yellow-50/90">
                  Local development path:{' '}
                  <Link href="/admin/login" className="underline underline-offset-4 hover:text-white">
                    sign in with the dev-only admin session
                  </Link>
                  .
                </p>
              )}
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
                    <div className="text-sm font-black uppercase tracking-wide">Active Keys</div>
                  </div>
                  <div className="mt-4 text-2xl font-black tracking-tight">{activeKeys.length}</div>
                </div>
              </div>

              {flash && (
                <div className="rounded-[28px] border border-emerald-500/30 bg-emerald-500/10 p-6 text-sm text-emerald-100">
                  {flash}
                </div>
              )}

              {operationError && (
                <div className="rounded-[28px] border border-red-500/30 bg-red-500/10 p-6 text-sm text-red-100">
                  {operationError}
                </div>
              )}

              <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6 sm:p-8">
                <div className="flex items-center justify-between gap-4">
                  <div>
                    <h2 className="text-xl font-black uppercase tracking-tight italic">Pending Requests</h2>
                    <p className="mt-2 text-sm text-gray-500">
                      Review developer requests, confirm allowlists, and issue one-time secrets directly from this dashboard.
                    </p>
                  </div>
                </div>

                <div className="mt-6 space-y-3">
                  {pendingRequests.length === 0 ? (
                    <div className="rounded-2xl border border-white/5 bg-black/20 px-4 py-5 text-sm text-gray-500">
                      No pending requests.
                    </div>
                  ) : (
                    pendingRequests.map((request) => (
                      <div
                        key={request.id}
                        className="rounded-2xl border border-white/5 bg-black/20 p-5 space-y-4"
                      >
                        <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                          <div className="space-y-1">
                            <div className="text-sm font-bold text-white">{request.requester_name}</div>
                            <div className="text-xs text-gray-500">{request.requester_email}</div>
                            <div className="text-xs text-gray-500">{request.organization || 'Independent developer'}</div>
                          </div>
                          <div className="text-xs uppercase tracking-[0.2em] text-[#007AFF]">
                            {request.requested_access_level} · {request.requested_surfaces.join(', ')}
                          </div>
                        </div>
                        <p className="text-sm text-gray-400 leading-relaxed">{request.use_case}</p>
                        <div className="grid gap-4 lg:grid-cols-2">
                          <label className="space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Label</span>
                            <input
                              value={requestLabels[request.id] ?? `${request.requester_name} primary key`}
                              onChange={(event) => setRequestLabels((prev) => ({ ...prev, [request.id]: event.target.value }))}
                              className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                            />
                          </label>
                          <label className="space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Expiry Days</span>
                            <input
                              type="number"
                              min={1}
                              max={3650}
                              value={requestExpiryDays[request.id] ?? ''}
                              onChange={(event) => setRequestExpiryDays((prev) => ({ ...prev, [request.id]: event.target.value }))}
                              className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                              placeholder="Optional"
                            />
                          </label>
                        </div>
                        <label className="space-y-2 block">
                          <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Approved IP Allowlists</span>
                          <textarea
                            rows={3}
                            value={requestAllowlists[request.id] ?? request.requested_ips.join('\n')}
                            onChange={(event) => setRequestAllowlists((prev) => ({ ...prev, [request.id]: event.target.value }))}
                            className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                          />
                        </label>
                        <label className="space-y-2 block">
                          <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Review Notes</span>
                          <textarea
                            rows={3}
                            value={requestReviewNotes[request.id] ?? ''}
                            onChange={(event) => setRequestReviewNotes((prev) => ({ ...prev, [request.id]: event.target.value }))}
                            className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                          />
                        </label>
                        <div className="flex flex-wrap gap-3">
                          <button
                            onClick={() => void approveRequest(request)}
                            disabled={Boolean(requestActionState[request.id])}
                            className="rounded-2xl bg-white px-5 py-3 text-xs font-black uppercase tracking-wider text-black transition hover:bg-gray-200 disabled:opacity-50"
                          >
                            {requestActionState[request.id] === 'approve' ? 'Approving...' : 'Approve & Issue Key'}
                          </button>
                          <button
                            onClick={() => void rejectRequest(request)}
                            disabled={Boolean(requestActionState[request.id])}
                            className="rounded-2xl border border-white/10 px-5 py-3 text-xs font-black uppercase tracking-wider text-white transition hover:border-red-400/50 hover:text-red-200 disabled:opacity-50"
                          >
                            {requestActionState[request.id] === 'reject' ? 'Rejecting...' : 'Reject'}
                          </button>
                        </div>
                      </div>
                    ))
                  )}
                </div>
              </div>

              <div className="rounded-[28px] border border-white/5 bg-[#121212] p-6 sm:p-8">
                <div>
                  <h2 className="text-xl font-black uppercase tracking-tight italic">Issued Keys</h2>
                  <p className="mt-2 text-sm text-gray-500">
                    Edit scopes and allowlists, then rotate or revoke keys without leaving the owner console.
                  </p>
                </div>

                <div className="mt-6 space-y-4">
                  {apiKeys.length === 0 ? (
                    <div className="rounded-2xl border border-white/5 bg-black/20 px-4 py-5 text-sm text-gray-500">
                      No API keys issued yet.
                    </div>
                  ) : (
                    apiKeys.map((key) => (
                      <div key={key.key_id} className="rounded-2xl border border-white/5 bg-black/20 p-5 space-y-4">
                        <div className="flex flex-col gap-2 lg:flex-row lg:items-start lg:justify-between">
                          <div className="space-y-1">
                            <div className="text-sm font-bold text-white">{key.label || key.owner_name}</div>
                            <div className="text-xs text-gray-500">{key.owner_email}</div>
                            <div className="text-xs font-mono text-[#007AFF]">{key.key_id}</div>
                          </div>
                          <div className="text-xs uppercase tracking-[0.2em] text-gray-500">
                            {key.status} · {key.access_level} · {key.intended_surfaces.join(', ')}
                          </div>
                        </div>

                        {revealedSecrets[key.key_id] && (
                          <div className="rounded-2xl border border-emerald-500/30 bg-emerald-500/10 px-4 py-4 space-y-2">
                            <div className="text-[11px] font-bold uppercase tracking-[0.22em] text-emerald-300">One-time Secret Reveal</div>
                            <div className="break-all font-mono text-sm text-emerald-100">{revealedSecrets[key.key_id]}</div>
                          </div>
                        )}

                        <div className="grid gap-4 lg:grid-cols-2">
                          <label className="space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Label</span>
                            <input
                              value={keyLabels[key.key_id] ?? key.label ?? ''}
                              onChange={(event) => setKeyLabels((prev) => ({ ...prev, [key.key_id]: event.target.value }))}
                              className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                            />
                          </label>
                          <label className="space-y-2">
                            <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Scopes</span>
                            <input
                              value={keyScopes[key.key_id] ?? key.scopes.join(', ')}
                              onChange={(event) => setKeyScopes((prev) => ({ ...prev, [key.key_id]: event.target.value }))}
                              className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                            />
                          </label>
                        </div>

                        <label className="space-y-2 block">
                          <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">IP Allowlists</span>
                          <textarea
                            rows={3}
                            value={keyAllowlists[key.key_id] ?? stringifyAllowlists(key.ip_allowlists)}
                            onChange={(event) => setKeyAllowlists((prev) => ({ ...prev, [key.key_id]: event.target.value }))}
                            className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                          />
                        </label>

                        <label className="space-y-2 block">
                          <span className="text-[11px] font-bold uppercase tracking-[0.22em] text-gray-500">Notes / Rotation Reason</span>
                          <textarea
                            rows={2}
                            value={keyNotes[key.key_id] ?? key.notes ?? ''}
                            onChange={(event) => {
                              const nextValue = event.target.value;
                              setKeyNotes((prev) => ({ ...prev, [key.key_id]: nextValue }));
                              setKeyReasons((prev) => ({ ...prev, [key.key_id]: nextValue }));
                            }}
                            className="w-full rounded-2xl border border-white/10 bg-[#050505] px-4 py-3 text-sm outline-none focus:border-[#007AFF]/40"
                          />
                        </label>

                        <label className="inline-flex items-center gap-3 text-sm text-gray-400">
                          <input
                            type="checkbox"
                            checked={keyOverrideIp[key.key_id] ?? key.override_no_ip_allowlist}
                            onChange={(event) => setKeyOverrideIp((prev) => ({ ...prev, [key.key_id]: event.target.checked }))}
                          />
                          Allow empty IP allowlist for this key
                        </label>

                        <div className="text-xs text-gray-500">
                          Last used: {key.last_used_at ? `${new Date(key.last_used_at).toLocaleString()}${key.last_used_ip ? ` from ${key.last_used_ip}` : ''}` : 'Never'}
                        </div>

                        <div className="flex flex-wrap gap-3">
                          <button
                            onClick={() => void saveKeyPolicy(key)}
                            disabled={Boolean(keyActionState[key.key_id])}
                            className="rounded-2xl bg-white px-5 py-3 text-xs font-black uppercase tracking-wider text-black transition hover:bg-gray-200 disabled:opacity-50"
                          >
                            {keyActionState[key.key_id] === 'save' ? 'Saving...' : 'Save Policy'}
                          </button>
                          <button
                            onClick={() => void rotateKey(key)}
                            disabled={Boolean(keyActionState[key.key_id])}
                            className="rounded-2xl border border-white/10 px-5 py-3 text-xs font-black uppercase tracking-wider text-white transition hover:border-[#007AFF]/40 disabled:opacity-50"
                          >
                            {keyActionState[key.key_id] === 'rotate' ? 'Rotating...' : 'Rotate'}
                          </button>
                          <button
                            onClick={() => void revokeKey(key)}
                            disabled={Boolean(keyActionState[key.key_id])}
                            className="rounded-2xl border border-white/10 px-5 py-3 text-xs font-black uppercase tracking-wider text-white transition hover:border-red-400/50 hover:text-red-200 disabled:opacity-50"
                          >
                            {keyActionState[key.key_id] === 'revoke' ? 'Revoking...' : 'Revoke'}
                          </button>
                        </div>
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
