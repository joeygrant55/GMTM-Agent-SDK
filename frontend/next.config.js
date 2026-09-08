/** @type {import('next').NextConfig} */
const { resolveBackendOrigin, isCombineSurface } = require('./lib/backend-config.cjs')
const backendUrl = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
const combine = isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
if (combine && !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
  throw new Error('The combine surface requires NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY')
}
module.exports = {
  // Next handles the optimizer before page middleware. The focused surface
  // uses ordinary static images and exposes no server-side image-fetch proxy.
  ...(combine ? { images: { unoptimized: true } } : {}),
  async rewrites() {
    return combine ? [] : [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }]
  },
}
