/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Ensure path aliases work with Turbopack
  webpack: (config, { defaultLoaders }) => {
    config.resolve.alias.canvas = false;
    return config;
  },
  // TypeScript configuration
  typescript: {
    ignoreBuildErrors: false,
  },
  // Experimental features
  experimental: {
    serverActions: true,
  },
};

export default nextConfig;
