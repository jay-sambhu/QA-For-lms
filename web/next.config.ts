import type { NextConfig } from "next";

const raw = (process.env.API_URL || process.env.NEXT_PUBLIC_API_URL || "https://qa-for-lms.onrender.com").trim();
const apiUrl = (raw.startsWith("http://") || raw.startsWith("https://") ? raw : `http://${raw}`).replace(/\/+$/, "");

const nextConfig: NextConfig = {
  allowedDevOrigins: ["127.0.0.1", "localhost"],
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
