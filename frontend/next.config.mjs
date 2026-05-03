/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Server Actions are enabled by default in Next.js 16
  // No need to configure explicitly
  output: "standalone", // Required for Docker deployment
  typescript: {
    ignoreBuildErrors: false,
  },
};

export default nextConfig;
