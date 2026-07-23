import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  basePath: "/mia",

  allowedDevOrigins: [
    "http://10.241.1.8:3000",
    "10.241.1.8",
  ],
};

export default nextConfig;