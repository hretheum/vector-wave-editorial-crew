import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  /* config options here */
  async rewrites() {
    return [
      // AI Assistant chat endpoints
      {
        source: '/api/chat',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/chat`,
      },
      {
        source: '/api/chat/stream',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/chat/stream`,
      },
      // Nowe endpointy CrewAI
      {
        source: '/api/crewai/:path*',
        destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8003'}/api/:path*`,
      },
      // Stare endpointy (tymczasowo)
      {
        source: '/api/:path*',
        destination: `${process.env.NEXT_PUBLIC_OLD_API_URL || 'http://localhost:8001'}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
