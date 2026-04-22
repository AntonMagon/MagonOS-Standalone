import type {Route} from 'next';

type StorageCounts = Record<string, number>;

export type PlatformStatus = {
  status: string;
  service: string;
  db_label: string;
  storage_counts: StorageCounts;
};

export type PlatformCompany = {
  id: string | number;
  canonical_key: string;
  canonical_name: string;
  city?: string;
  canonical_email?: string;
  website?: string;
};

type FoundationHealth = {
  status: string;
  service?: string;
  database_url?: string;
};

type PublicCompaniesPayload = {
  items: Array<{
    id: string;
    code: string;
    name: string;
    country_code?: string;
    status?: string;
    note?: string | null;
  }>;
};

const DEFAULT_API_BASE_URL = 'http://127.0.0.1:8091';

function apiBaseUrl(): string {
  return (process.env.MAGON_API_BASE_URL || DEFAULT_API_BASE_URL).replace(/\/$/, '');
}

function databaseLabelFromUrl(databaseUrl?: string): string {
  if (!databaseUrl) {
    return 'Не указано';
  }
  if (databaseUrl.startsWith('postgresql')) {
    try {
      const normalized = databaseUrl.replace('+psycopg', '');
      const parsed = new URL(normalized);
      const dbName = parsed.pathname.replace(/^\//, '') || 'magon';
      return `PostgreSQL ${parsed.hostname}:${parsed.port || '5432'}/${dbName}`;
    } catch {
      return 'PostgreSQL';
    }
  }
  if (databaseUrl.startsWith('sqlite+pysqlite:///')) {
    return `SQLite ${databaseUrl.slice('sqlite+pysqlite:///'.length)}`;
  }
  return databaseUrl;
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
  // RU: Public shell берёт online-state только из активного foundation contour, чтобы не держать скрытый fallback в старый runtime.
  const [health, companies] = await Promise.all([
    fetchJson<FoundationHealth>('/health'),
    fetchJson<PublicCompaniesPayload>('/api/v1/public/companies'),
  ]);
  if (!health) {
    return null;
  }
  return {
    status: health.status,
    service: health.service || 'magon-foundation',
    db_label: databaseLabelFromUrl(health.database_url),
    storage_counts: {
      canonical_companies: companies?.items.length ?? 0,
      review_queue: 0,
      feedback_events: 0,
    },
  };
}

export async function getRecentCompanies(limit = 5): Promise<PlatformCompany[]> {
  // RU: Для active standalone shell читаем только foundation company-registry и не прячем старый runtime за fallback-логикой.
  const foundationPayload = await fetchJson<PublicCompaniesPayload>('/api/v1/public/companies');
  if (foundationPayload?.items) {
    return foundationPayload.items.slice(0, limit).map((item) => ({
      id: item.id,
      canonical_key: item.code,
      canonical_name: item.name,
    }));
  }
  return [];
}

export function getOperatorUrl(path = ''): Route {
  const normalized = path.replace(/^\/+/, '');
  if (!normalized) {
    return '/ops' as Route;
  }
  return `/ui/${normalized}` as Route;
}
