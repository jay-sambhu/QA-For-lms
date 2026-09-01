import type { NextConfig } from "next";

const raw = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "http://127.0.0.1:8000").trim();
const apiUrl = (raw.startsWith("http://") || raw.startsWith("https://") ? raw : `http://${raw}`).replace(/\/+$/, "");

const nextConfig: NextConfig = {
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
