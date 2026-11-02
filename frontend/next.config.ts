import type { NextConfig } from "next";

/**
 * The sandbox preview proxies this app under https://{port}-{id}.e2b.app, so
 * the dev server has to accept that Origin for server actions and HMR.
 */
const previewOrigins = ["*.e2b.app", "*.e2b.dev", "localhost:3000"];

const nextConfig: NextConfig = {
  reactStrictMode: true,

  // Django's URLs end in "/". Next's default 308s "/api/v1/auth/me/" to the
  // slashless form before the proxy route runs, and Django cannot redirect a
  // POST back - so every browser API call would fail.
  skipTrailingSlashRedirect: true,

  // Browser code calls relative /api/v1/... paths, served by the proxy route
  // in app/api/v1/[...path] (which attaches the session). Media is public and
  // needs no session, so a plain rewrite suffices. Either way "localhost:8000"
  // never reaches the client bundle, where it would mean the user's machine.
  async rewrites() {
    const backend = process.env.BACKEND_INTERNAL_URL ?? "http://localhost:8000";
    return [{ source: "/media/:path*", destination: `${backend}/media/:path*` }];
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
