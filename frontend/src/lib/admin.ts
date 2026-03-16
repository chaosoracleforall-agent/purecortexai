export const TRUSTED_ADMIN_EMAIL_HEADER = 'x-purecortex-auth-email';

export function getAllowedAdminEmails(): string[] {
  return (process.env.PURECORTEX_ADMIN_ALLOWED_EMAILS || 'chaosoracleforall@gmail.com')
    .split(',')
    .map((value) => value.trim().toLowerCase())
    .filter(Boolean);
}

export function getTrustedAdminEmail(headers: Headers): string | null {
  const value = headers.get(TRUSTED_ADMIN_EMAIL_HEADER);
  if (!value) {
    return null;
  }
  const normalized = value.trim().toLowerCase();
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
