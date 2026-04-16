import * as Sentry from '@sentry/nextjs';

const dsn = process.env.NEXT_PUBLIC_MAGON_SENTRY_DSN;

if (dsn) {
  // RU: Browser Sentry включается только через NEXT_PUBLIC_MAGON_SENTRY_DSN, чтобы storefront не тащил внешнюю телеметрию без явного решения.
  Sentry.init({
    dsn,
    environment: process.env.NEXT_PUBLIC_MAGON_SENTRY_ENV || 'local',
    release: process.env.NEXT_PUBLIC_MAGON_SENTRY_RELEASE,
    tracesSampleRate: Number(process.env.NEXT_PUBLIC_MAGON_SENTRY_TRACES_SAMPLE_RATE || '0'),
    replaysSessionSampleRate: Number(process.env.NEXT_PUBLIC_MAGON_SENTRY_REPLAYS_SESSION_SAMPLE_RATE || '0'),
    replaysOnErrorSampleRate: Number(process.env.NEXT_PUBLIC_MAGON_SENTRY_REPLAYS_ON_ERROR_SAMPLE_RATE || '0')
  });
}
