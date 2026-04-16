import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');
const backendBaseUrl = (process.env.MAGON_API_BASE_URL || 'http://127.0.0.1:8091').replace(/\/$/, '');
const distDir = process.env.MAGON_WEB_DIST_DIR || '.next';

/** @type {import('next').NextConfig} */
const nextConfig = {
  // RU: Dev shell и production build не должны делить один .next каталог, иначе живой next dev может развалиться после соседнего next build.
  distDir,
  typedRoutes: true,
  async rewrites() {
    return [
      {
        source: '/ops',
        destination: `${backendBaseUrl}/`
      },
      {
        source: '/ops/:path*',
        destination: `${backendBaseUrl}/ui/:path*`
      },
      {
        source: '/ui',
        destination: `${backendBaseUrl}/ui/companies`
      },
      {
        source: '/ui/:path*',
        destination: `${backendBaseUrl}/ui/:path*`
      },
      {
        source: '/platform-api/:path*',
        destination: `${backendBaseUrl}/:path*`
      }
    ];
  }
};

export default withNextIntl(nextConfig);
