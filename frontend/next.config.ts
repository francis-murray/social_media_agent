import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    // This runs on the server at build/start time (not in the browser)
    const dest = process.env.API_BASE || "http://localhost:8000";
    return [
      // e.g. /api/generate/stream -> http://localhost:8000/generate/stream (dev)
      // or -> https://your-backend.vercel.app/generate/stream (prod)
      { source: "/api/:path*", destination: `${dest}/:path*` },
    ];
  },
};

export default nextConfig;
