import { NextResponse } from 'next/server';

import { getInternalBackendUrl, getTrustedAdminEmail, isAllowedAdminEmail } from '@/lib/admin';

const NO_STORE_HEADERS = {
  'Cache-Control': 'no-store, private, max-age=0',
  Pragma: 'no-cache',
  Expires: '0',
} as const;

export function adminJson(body: unknown, init?: ResponseInit): NextResponse {
  const response = NextResponse.json(body, init);
  for (const [key, value] of Object.entries(NO_STORE_HEADERS)) {
    response.headers.set(key, value);
  }
  return response;
}

export function requireAdminProxyContext(request: Request):
  | { actorEmail: string; internalAdminToken: string }
  | NextResponse {
  const actorEmail = getTrustedAdminEmail(request.headers);
  if (!actorEmail || !isAllowedAdminEmail(actorEmail)) {
    return adminJson(
      { detail: 'Admin SSO required' },
      { status: 403 }
    );
  }

  const internalAdminToken = process.env.PURECORTEX_INTERNAL_ADMIN_TOKEN;
  if (!internalAdminToken) {
    return adminJson(
      { detail: 'Internal admin token not configured' },
      { status: 503 }
    );
  }

  return { actorEmail, internalAdminToken };
}

export function backendAdminUrl(path: string): string {
  return `${getInternalBackendUrl()}${path}`;
}
