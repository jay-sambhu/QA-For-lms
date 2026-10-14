import type { NextConfig } from "next";

// Backend origin for the /api/* proxy rewrite.
// NOTE: rewrites are evaluated during `next build` and serialized into the
// standalone server, so API_URL (or NEXT_PUBLIC_API_URL) must be set at BUILD
// time, e.g. `API_URL=http://api:8000 npm run build` in Docker.
const raw = (
  process.env.API_URL ||
  process.env.NEXT_PUBLIC_API_URL ||
  "http://localhost:8000"
).trim();
const apiUrl = (raw.startsWith("http://") || raw.startsWith("https://") ? raw : `http://${raw}`).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  // Emits .next/standalone/server.js — a minimal `node server.js` production
  // server without the full node_modules (small RAM/disk footprint).
  output: "standalone",
  // Pin the tracing root to this folder so server.js lands directly in
  // .next/standalone/ (not .next/standalone/web/) even if a lockfile exists higher up.
  outputFileTracingRoot: __dirname,
  turbopack: { root: __dirname },
  poweredByHeader: false,
  allowedDevOrigins: ["127.0.0.1", "localhost", "jasuss.tech", "www.jasuss.tech", "*.vercel.app"],
  experimental: {
    // Report downloads can trigger server-side PDF/XLSX generation; the default
    // 30s proxy timeout of the rewrite is too short for that on a small droplet.
    proxyTimeout: 120_000,
  },
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUrl}/api/:path*`,
      },
    ];
  },
};

export default nextConfig;
