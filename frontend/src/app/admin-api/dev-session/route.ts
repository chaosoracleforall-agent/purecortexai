import { NextResponse } from 'next/server';

import {
  LOCAL_ADMIN_SESSION_COOKIE,
  createLocalAdminSessionValue,
  isAllowedAdminEmail,
} from '@/lib/admin';

export async function POST(request: Request) {
  const body = await request.json().catch(() => ({}));
  const email = String(body?.email || '').trim().toLowerCase();

  if (!email || !isAllowedAdminEmail(email)) {
    return NextResponse.json({ detail: 'Allowed admin email required' }, { status: 403 });
  }

  const sessionValue = createLocalAdminSessionValue(email);
  if (!sessionValue) {
    return NextResponse.json(
      { detail: 'Local admin dev session is unavailable in this environment' },
      { status: 503 }
    );
  }

  const response = NextResponse.json({ status: 'ok', email });
  response.cookies.set({
    name: LOCAL_ADMIN_SESSION_COOKIE,
    value: sessionValue,
    httpOnly: true,
    sameSite: 'lax',
    secure: false,
    path: '/',
    maxAge: 60 * 60 * 8,
  });
  return response;
}

export async function DELETE() {
  const response = NextResponse.json({ status: 'cleared' });
  response.cookies.set({
    name: LOCAL_ADMIN_SESSION_COOKIE,
    value: '',
    httpOnly: true,
    sameSite: 'lax',
    secure: false,
    path: '/',
    maxAge: 0,
  });
  return response;
}
