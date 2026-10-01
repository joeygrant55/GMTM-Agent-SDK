/** @type {import('next').NextConfig} */
const { resolveBackendOrigin, isRestrictedSurface, isCombineSurface } = require('./lib/backend-config.cjs')
const backendUrl = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
const combine = isRestrictedSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
// Profile has no Clerk (GMTM sign-in + SPARQ session); combine still needs it.
if (isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE) && !process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY) {
  throw new Error('The selected surface requires NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY')
}
module.exports = {
  // Next handles the optimizer before page middleware. The focused surface
  // uses ordinary static images and exposes no server-side image-fetch proxy.
  // Keep browser font stylesheets, but make candidate builds independent of a
  // compile-time Google Fonts download.
  ...(combine ? { images: { unoptimized: true }, optimizeFonts: false } : {}),
  async headers() {
    // GMTM entry routes carry one-use codes: never cache or leak a referrer.
    const entry = [{ key: 'Referrer-Policy', value: 'no-referrer' }, { key: 'Cache-Control', value: 'no-store' }]
    return [{ source: '/enter', headers: entry }, { source: '/enter/:path*', headers: entry }]
  },
  async rewrites() {
    return combine ? [] : [{ source: '/api/:path*', destination: `${backendUrl}/api/:path*` }]
  },
}
