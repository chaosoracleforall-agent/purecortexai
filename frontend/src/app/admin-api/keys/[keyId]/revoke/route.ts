import { NextResponse } from 'next/server';

import { adminJson, backendAdminUrl, requireAdminProxyContext } from '@/app/admin-api/_lib/proxy';


export async function POST(
  request: Request,
  { params }: { params: Promise<{ keyId: string }> }
) {
  const context = requireAdminProxyContext(request);
  if (context instanceof NextResponse) {
    return context;
  }

  const { keyId } = await params;
  const body = await request.json().catch(() => ({}));
  const response = await fetch(backendAdminUrl(`/internal/admin/api-keys/${keyId}/revoke`), {
    method: 'POST',
    headers: {
      'X-Internal-Admin-Token': context.internalAdminToken,
      'Content-Type': 'application/json',
      Accept: 'application/json',
    },
    body: JSON.stringify({
      ...body,
      actor_email: context.actorEmail,
    }),
    cache: 'no-store',
  });

  const payload = await response.json().catch(() => ({}));
  return adminJson(payload, { status: response.status });
}
