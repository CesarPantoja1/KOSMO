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
};

export default nextConfig;
