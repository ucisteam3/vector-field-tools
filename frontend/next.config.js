/** @type {import('next').NextConfig} */
const apiPort = process.env.NEXT_PUBLIC_API_PORT || "8001";
const nextConfig = {
  rewrites: async () => [
    { source: "/api/:path*", destination: `http://127.0.0.1:${apiPort}/:path*` },
  ],
};

module.exports = nextConfig;
