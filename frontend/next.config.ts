import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Vercel deployment optimizations
  output: "standalone",
  productionBrowserSourceMaps: false,
  compress: true,

  // Experimental features for better performance
  experimental: {
    optimizePackageImports: ["@xyflow/react"],
  },

  // Environment variables exposed to browser
  env: {
    NEXT_PUBLIC_API_URL:
      process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    NEXT_PUBLIC_APP_NAME: process.env.NEXT_PUBLIC_APP_NAME || "KOSMO",
    NEXT_PUBLIC_APP_ENV: process.env.NEXT_PUBLIC_APP_ENV || "development",
  },
};

export default nextConfig;
