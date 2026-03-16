import crypto from 'node:crypto';

export const TRUSTED_ADMIN_EMAIL_HEADER = 'x-purecortex-auth-email';
export const LOCAL_ADMIN_SESSION_COOKIE = 'purecortex_admin_session';

export function getAllowedAdminEmails(): string[] {
  return (process.env.PURECORTEX_ADMIN_ALLOWED_EMAILS || 'chaosoracleforall@gmail.com')
    .split(',')
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
}

function shouldTrustAdminEmailHeader(): boolean {
  return process.env.PURECORTEX_TRUST_ADMIN_EMAIL_HEADER === '1';
}

export function getTrustedAdminEmail(headers: Headers): string | null {
  const localSessionEmail = getLocalAdminSessionEmail(headers);
  if (localSessionEmail) {
    return localSessionEmail;
  }

  if (!shouldTrustAdminEmailHeader()) {
    return null;
  }

  const value = headers.get(TRUSTED_ADMIN_EMAIL_HEADER);
  const normalized = value?.trim().toLowerCase() || '';
  return normalized || null;
}

export function isAllowedAdminEmail(email: string | null): boolean {
  if (!email) {
    return false;
  }
  return getAllowedAdminEmails().includes(email);
}

export function getInternalBackendUrl(): string {
  return process.env.PURECORTEX_INTERNAL_BACKEND_URL || 'http://backend:8000';
}

function getLocalAdminSessionSecret(): string | null {
  if (process.env.NODE_ENV === 'production') {
    return null;
  }
  return process.env.PURECORTEX_ADMIN_DEV_SESSION_SECRET || process.env.PURECORTEX_INTERNAL_ADMIN_TOKEN || null;
}

function signAdminEmail(email: string, secret: string): string {
  return crypto.createHmac('sha256', secret).update(email).digest('hex');
}

function parseCookieHeader(headers: Headers): Record<string, string> {
  const raw = headers.get('cookie');
  if (!raw) {
    return {};
  }

  const entries = raw.split(';').map((part) => part.trim()).filter(Boolean);
  return Object.fromEntries(
    entries.map((entry) => {
      const index = entry.indexOf('=');
      if (index === -1) {
        return [entry, ''];
      }
      return [entry.slice(0, index), decodeURIComponent(entry.slice(index + 1))];
    })
  );
}

export function createLocalAdminSessionValue(email: string): string | null {
  const normalized = email.trim().toLowerCase();
  const secret = getLocalAdminSessionSecret();
  if (!normalized || !secret || !isAllowedAdminEmail(normalized)) {
    return null;
  }
  return `${normalized}.${signAdminEmail(normalized, secret)}`;
}

export function getLocalAdminSessionEmail(headers: Headers): string | null {
  const secret = getLocalAdminSessionSecret();
  if (!secret) {
    return null;
  }

  const sessionValue = parseCookieHeader(headers)[LOCAL_ADMIN_SESSION_COOKIE];
  if (!sessionValue) {
    return null;
  }

  const index = sessionValue.lastIndexOf('.');
  if (index <= 0) {
    return null;
  }

  const email = sessionValue.slice(0, index).trim().toLowerCase();
  const signature = sessionValue.slice(index + 1);
  const expected = signAdminEmail(email, secret);
  if (!email || !signature || signature.length !== expected.length) {
    return null;
  }
  if (!crypto.timingSafeEqual(Buffer.from(signature), Buffer.from(expected))) {
    return null;
  }
  return isAllowedAdminEmail(email) ? email : null;
}
