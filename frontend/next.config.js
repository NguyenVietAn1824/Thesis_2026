/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: '/proxy/:path*',
        destination: 'http://localhost:3334/:path*',
      },
    ];
  },
};

module.exports = nextConfig;
