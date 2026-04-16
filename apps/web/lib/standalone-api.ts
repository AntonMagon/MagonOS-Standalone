import type {Route} from 'next';

type StorageCounts = Record<string, number>;

export type PlatformStatus = {
  status: string;
  service: string;
  db_path: string;
  storage_counts: StorageCounts;
};

export type PlatformCompany = {
  id: number;
  canonical_key: string;
  canonical_name: string;
  city?: string;
  canonical_email?: string;
  website?: string;
};

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8091';

function apiBaseUrl(): string {
  return (process.env.MAGON_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

async function fetchJson<T>(path: string): Promise<T | null> {
  try {
    const response = await fetch(`${apiBaseUrl()}${path}`, {
      cache: 'no-store'
    });
    if (!response.ok) {
      return null;
    }
    return (await response.json()) as T;
  } catch {
    return null;
  }
}

export async function getPlatformStatus(): Promise<PlatformStatus | null> {
  return fetchJson<PlatformStatus>('/status');
}

export async function getRecentCompanies(limit = 5): Promise<PlatformCompany[]> {
  const payload = await fetchJson<{items: PlatformCompany[]}>(
    `/companies?limit=${encodeURIComponent(String(limit))}&offset=0`
  );
  return payload?.items || [];
}

export function getOperatorUrl(path = ''): Route {
  const normalized = path.replace(/^\/+/, '');
  if (!normalized) {
    return '/ops' as Route;
  }
  return `/ui/${normalized}` as Route;
}
