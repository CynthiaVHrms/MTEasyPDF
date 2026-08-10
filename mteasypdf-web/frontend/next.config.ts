import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/mia",

  allowedDevOrigins: [
    "http://10.241.1.8:3000",
    "10.241.1.8",
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
};

export default nextConfig;