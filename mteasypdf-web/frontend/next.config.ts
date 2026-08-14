import type { NextConfig } from "next";

const backendProxyTarget =
  process.env.BACKEND_PROXY_TARGET?.replace(/\/$/, "") ??
  "http://10.241.1.8:8001";

const nextConfig: NextConfig = {
  basePath: "/mia",

  allowedDevOrigins: [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://172.16.250.1:3000",
    "http://10.241.1.8:3000",
    "http://10.241.1.8:3004",
    "10.241.1.8",
    "http://187.188.143.249",
    "http://187.188.143.249:3004",
    "187.188.143.249",
  ],

  experimental: {
    serverActions: {
      allowedOrigins: [
        "10.241.1.8:3000",
        "localhost:3000",
        "127.0.0.1:3000",
      ],
    },
  },

  async rewrites() {
    return [
      {
        source: "/mia-api/:path*",
        destination: `${backendProxyTarget}/:path*`,
      },
    ];
  },
};

export default nextConfig;