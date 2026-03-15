'use client';

import { PUBLIC_API_URL, PUBLIC_WS_URL } from './protocolConfig';

function trimTrailingSlash(value: string): string {
  return value.endsWith('/') ? value.slice(0, -1) : value;
}

export function getApiBaseUrl(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return trimTrailingSlash(process.env.NEXT_PUBLIC_API_URL);
  }

  if (typeof window !== 'undefined') {
    const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    if (isLocal) {
      return 'http://127.0.0.1:8000';
    }
    return trimTrailingSlash(window.location.origin);
  }

  return trimTrailingSlash(PUBLIC_API_URL);
}

export function getWsUrl(path = '/ws/chat'): string {
  if (process.env.NEXT_PUBLIC_WS_URL) {
    return process.env.NEXT_PUBLIC_WS_URL;
  }

  if (typeof window !== 'undefined') {
    const isLocal = ['localhost', '127.0.0.1'].includes(window.location.hostname);
    if (isLocal) {
      return `ws://127.0.0.1:8000${path}`;
    }
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
    return `${protocol}//${window.location.host}${path}`;
  }

  return PUBLIC_WS_URL;
}

export function apiUrl(path: string): string {
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  return `${getApiBaseUrl()}${path.startsWith('/') ? path : `/${path}`}`;
}

export async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(apiUrl(path), {
    ...init,
    headers: {
      Accept: 'application/json',
      ...(init?.headers || {}),
    },
  });

  if (!response.ok) {
    let detail = `${response.status} ${response.statusText}`;
    try {
      const body = await response.json();
      if (typeof body?.detail === 'string') {
        detail = body.detail;
      }
    } catch {
      // Keep the fallback status text.
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}
