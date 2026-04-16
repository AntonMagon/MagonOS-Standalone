import * as Sentry from '@sentry/nextjs';

const dsn = process.env.MAGON_SENTRY_DSN || process.env.NEXT_PUBLIC_MAGON_SENTRY_DSN;

if (dsn) {
  // RU: Edge-конфиг оставляем тем же env-gated, чтобы будущие edge-routes не выпадали из observability-контракта.
  Sentry.init({
    dsn,
    environment: process.env.MAGON_SENTRY_ENV || process.env.NEXT_PUBLIC_MAGON_SENTRY_ENV || 'local',
    release: process.env.MAGON_SENTRY_RELEASE || process.env.NEXT_PUBLIC_MAGON_SENTRY_RELEASE,
    tracesSampleRate: Number(process.env.MAGON_SENTRY_TRACES_SAMPLE_RATE || '0')
  });
}
