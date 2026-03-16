import { NextResponse } from 'next/server';

import { getInternalBackendUrl, getTrustedAdminEmail, isAllowedAdminEmail } from '@/lib/admin';


export async function GET(request: Request) {
  const email = getTrustedAdminEmail(request.headers);
  if (!isAllowedAdminEmail(email)) {
    return NextResponse.json(
      { detail: 'Admin SSO required' },
      { status: 403 }
    );
  }

  const internalAdminToken = process.env.PURECORTEX_INTERNAL_ADMIN_TOKEN;
  if (!internalAdminToken) {
    return NextResponse.json(
      { detail: 'Internal admin token not configured' },
      { status: 503 }
    );
  }

  const response = await fetch(`${getInternalBackendUrl()}/internal/admin/health`, {
    headers: {
      'X-Internal-Admin-Token': internalAdminToken,
      Accept: 'application/json',
    },
    cache: 'no-store',
  });

  const payload = await response.json();
  return NextResponse.json(payload, { status: response.status });
}
