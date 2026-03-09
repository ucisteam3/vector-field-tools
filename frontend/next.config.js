/** @type {import('next').NextConfig} */
const nextConfig = {
  rewrites: async () => [
    { source: "/api/:path*", destination: "http://127.0.0.1:8001/:path*" },
  ],
};

module.exports = nextConfig;
