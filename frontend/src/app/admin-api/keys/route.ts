import { NextResponse } from 'next/server';

import { adminJson, backendAdminUrl, requireAdminProxyContext } from '../_lib/proxy';


export async function GET(request: Request) {
  const context = requireAdminProxyContext(request);
  if (context instanceof NextResponse) {
    return context;
  }

  const url = new URL(request.url);
  const limit = url.searchParams.get('limit') || '50';
  const response = await fetch(`${backendAdminUrl('/internal/admin/api-keys')}?limit=${encodeURIComponent(limit)}`, {
    headers: {
      'X-Internal-Admin-Token': context.internalAdminToken,
      Accept: 'application/json',
    },
    cache: 'no-store',
  });

  const payload = await response.json().catch(() => ({}));
  return adminJson(payload, { status: response.status });
}
