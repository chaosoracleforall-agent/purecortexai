import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
  transpilePackages: ['algosdk'],
  async headers() {
    return [{
      source: '/(.*)',
      headers: [
        { key: 'X-Frame-Options', value: 'DENY' },
        { key: 'X-Content-Type-Options', value: 'nosniff' },
        { key: 'Referrer-Policy', value: 'strict-origin-when-cross-origin' },
        { key: 'Permissions-Policy', value: 'camera=(), microphone=(), geolocation=()' },
        { key: 'Strict-Transport-Security', value: 'max-age=63072000; includeSubDomains; preload' },
      ],
    }];
  },
  async redirects() {
    return [
      { source: '/docs/API.md', destination: '/docs/api', permanent: true },
      { source: '/docs/MCP.md', destination: '/docs/mcp', permanent: true },
      { source: '/docs/CLI.md', destination: '/docs/cli', permanent: true },
      { source: '/TERMS.md', destination: '/docs/terms', permanent: true },
      { source: '/PRIVACY.md', destination: '/docs/privacy', permanent: true },
    ];
  },
};

export default nextConfig;
