import * as Sentry from '@sentry/nextjs';

const dsn = process.env.MAGON_SENTRY_DSN || process.env.NEXT_PUBLIC_MAGON_SENTRY_DSN;

if (dsn) {
  // RU: Server-side Next telemetry отделяем от browser env, но разрешаем fallback на публичный DSN для простого локального prep-контура.
  Sentry.init({
    dsn,
    environment: process.env.MAGON_SENTRY_ENV || process.env.NEXT_PUBLIC_MAGON_SENTRY_ENV || 'local',
    release: process.env.MAGON_SENTRY_RELEASE || process.env.NEXT_PUBLIC_MAGON_SENTRY_RELEASE,
    tracesSampleRate: Number(process.env.MAGON_SENTRY_TRACES_SAMPLE_RATE || '0'),
    integrations(defaultIntegrations) {
      // RU: Prisma instrumentation в этом repo не используется, а в Next dev она только создаёт шумные bundler warnings без пользы.
      return defaultIntegrations.filter((integration) => integration.name !== 'Prisma');
    }
  });
}
