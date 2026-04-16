import createNextIntlPlugin from 'next-intl/plugin';

const withNextIntl = createNextIntlPlugin('./i18n/request.ts');
const backendBaseUrl = (process.env.MAGON_API_BASE_URL || 'http://127.0.0.1:8091').replace(/\/$/, '');

/** @type {import('next').NextConfig} */
const nextConfig = {
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
