import type { NextConfig } from "next";

/**
 * The sandbox preview proxies this app under https://{port}-{id}.e2b.app, so
 * the dev server has to accept that Origin for server actions and HMR.
 */
const previewOrigins = ["*.e2b.app", "*.e2b.dev", "localhost:3000"];

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Browser code calls relative /api/... paths; Next proxies them to Django
  // server-side. This is what keeps "localhost:8000" out of the client bundle,
  // where it would resolve to the user's own machine rather than the API.
  async rewrites() {
    const backend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
    return [
      { source: "/api/v1/:path*", destination: `${backend}/api/v1/:path*` },
      { source: "/media/:path*", destination: `${backend}/media/:path*` },
    ];
  },

  allowedDevOrigins: previewOrigins,

  images: {
    formats: ["image/avif", "image/webp"],
    remotePatterns: [
      { protocol: "http", hostname: "localhost", port: "8000", pathname: "/media/**" },
    ],
  },

  eslint: { ignoreDuringBuilds: true },
};

export default nextConfig;
