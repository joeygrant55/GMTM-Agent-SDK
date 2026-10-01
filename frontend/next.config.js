/** @type {import('next').NextConfig} */
const { resolveBackendOrigin, isRestrictedSurface } = require('./lib/backend-config.cjs')
// Fail the build on a missing or invalid backend origin. No /api rewrite: browser
// calls reach the backend only through /api/sparq/proxy, which adds the session.
resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
const combine = isRestrictedSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
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
}
