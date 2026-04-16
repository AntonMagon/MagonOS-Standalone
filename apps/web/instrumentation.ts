export async function register() {
  if (process.env.NEXT_RUNTIME === 'nodejs') {
    // RU: Server config подключаем через instrumentation hook, чтобы observability включалась одинаково в build/runtime path без ручного импорта по страницам.
    await import('./sentry.server.config');
  }

  if (process.env.NEXT_RUNTIME === 'edge') {
    await import('./sentry.edge.config');
  }
}
