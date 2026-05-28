/** @type {import('next').NextConfig} */
//
// Local-dev convenience: rewrites /api/* → http://localhost:8000/* so
// frontend code can use a relative "/api" base. This rewrite is ONLY
// active when NEXT_PUBLIC_API_BASE is unset, which is the local-dev case.
//
// In production (Vercel), you MUST set NEXT_PUBLIC_API_BASE to the public
// backend URL (e.g. https://signalscout-backend.onrender.com). When that
// env var is set, frontend bypasses the rewrite and calls the real URL.
//
const useDevRewrite = !process.env.NEXT_PUBLIC_API_BASE;
const devTarget = process.env.NEXT_PUBLIC_DEV_BACKEND || "http://localhost:8000";

const nextConfig = {
  reactStrictMode: true,
  turbopack: {
    root: __dirname,
  },
  async rewrites() {
    if (!useDevRewrite) {
      // Vercel/prod: api.ts already uses the full NEXT_PUBLIC_API_BASE URL.
      // Adding a rewrite that points at localhost would break the deployed app.
      return [];
    }
    return [
      { source: "/api/:path*", destination: `${devTarget}/:path*` },
    ];
  },
};

module.exports = nextConfig;
