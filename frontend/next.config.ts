import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  output: 'standalone',
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
