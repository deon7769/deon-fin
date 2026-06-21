/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,

  // Production same-origin/proxy wiring is handled in F3.1.
  // basePath: process.env.NEXT_BASE_PATH || undefined,
  // async rewrites() {
  //   const api = process.env.API_PROXY_TARGET;
  //   return api ? [{ source: "/api/:path*", destination: `${api}/api/:path*` }] : [];
  // },
};

export default nextConfig;
