import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  reactStrictMode: true,
  // Windows local builds can flake on 500.html rename; Vercel Linux is the deploy target.
  typescript: { ignoreBuildErrors: false },
};

export default nextConfig;
