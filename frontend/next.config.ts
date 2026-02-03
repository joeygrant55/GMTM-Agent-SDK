import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: 'http://localhost:8000/api/:path*',
      },
    ]
  },
  // Increase timeout for long-running agent operations
  experimental: {
    proxyTimeout: 120000, // 2 minutes
  },
};

export default nextConfig;
