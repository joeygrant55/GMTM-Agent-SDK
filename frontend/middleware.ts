import { NextResponse, type NextRequest } from 'next/server'
import { candidatePagePolicy, isProfileSurface, isRestrictedSurface, profileContentSecurityPolicy, resolveBackendOrigin, withoutGmtmSession } from './lib/backend-config.cjs'
import { GSH_HEADER, SESSION_COOKIE, clearedSessionCookie, gmtmSessionHash, verifySession } from './lib/sparq-session.cjs'

// GMTM is the only sign-in on every surface (Joey, 2026-10-01).
const surface = process.env.NEXT_PUBLIC_APP_SURFACE
const restricted = isRestrictedSurface(surface)
const profile = isProfileSurface(surface)
// Legacy public pages read the backend directly (athlete, report); restricted surfaces never do.
const connect = restricted ? '' : resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
// Legacy pages that render without a SPARQ session.
const LEGACY_PUBLIC = /^\/(?:$|demo$|quick-scan$|athlete\/|report\/|enter(?:\/|$)|api\/(?:sparq|demo-chat|og|waitlist)(?:\/|$))/

// Per-request nonce CSP (Next reads it from the request headers). GMTM's sessionId
// cookie is removed before any handler; handlers get only its sha256 in x-sparq-gsh
// (a client-sent value is always dropped).
function sessionResponse(request: NextRequest, gsh: string | null) {
  const nonce = btoa(crypto.randomUUID())
  const csp = profileContentSecurityPolicy({ nonce, dev: process.env.NODE_ENV !== 'production', connect, profile })
  const headers = new Headers(request.headers)
  const cookie = withoutGmtmSession(headers.get('cookie'))
  if (cookie) headers.set('cookie', cookie)
  else headers.delete('cookie')
  headers.delete(GSH_HEADER)
  if (gsh) headers.set(GSH_HEADER, gsh)
  headers.set('x-nonce', nonce)
  headers.set('content-security-policy', csp)
  const response = NextResponse.next({ request: { headers } })
  response.headers.set('Content-Security-Policy', csp)
  return response
}

// Every protected page needs a SPARQ session bound to the browser's current GMTM
// session. Otherwise clear it and re-enter (GMTM cookie present: a new GMTM user
// replaces the old one) or go back to GMTM.
async function sessionMiddleware(request: NextRequest, needsSession: boolean) {
  const gsh = await gmtmSessionHash(request.headers.get('cookie'))
  if (needsSession) {
    const token = request.cookies.get(SESSION_COOKIE)?.value
    if (!await verifySession(token, process.env.SPARQ_SESSION_SECRET, gsh)) {
      const target = gsh ? new URL('/enter', request.url) : new URL('/', process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com')
      const response = NextResponse.redirect(target)
      response.headers.set('Cache-Control', 'no-store')
      if (token !== undefined) response.cookies.set(clearedSessionCookie())
      return response
    }
  }
  return sessionResponse(request, gsh)
}

export default function middleware(request: NextRequest) {
  const pathname = request.nextUrl.pathname
  if (restricted) {
    const policy = candidatePagePolicy(pathname, request.method, surface)
    // This runs before all page handlers and same-origin API routes.
    if (policy === 'deny') return new NextResponse('Not found', { status: 404, headers: { 'Cache-Control': 'no-store' } })
    if (policy === 'asset') return NextResponse.next()
    if (policy === 'home') {
      const home = new URL('/home', request.url)
      home.search = request.nextUrl.search
      return NextResponse.redirect(home)
    }
    return sessionMiddleware(request, policy === 'page' && !/^\/enter(?:\/|$)/.test(pathname))
  }
  if (!/^\/(api|trpc)(?:\/|$)/.test(pathname) && (
    pathname.startsWith('/_next') || /\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)$/.test(pathname)
  )) {
    // Preserve the normal app's historical static-file exemption.
    return NextResponse.next()
  }
  // Same-origin API routes check their own session (/api/sparq/*) or are public.
  const needsSession = !LEGACY_PUBLIC.test(pathname) && !/^\/(api|trpc)(?:\/|$)/.test(pathname)
  return sessionMiddleware(request, needsSession)
}

// Include static-looking dynamic URLs and API handlers in the boundary.
export const config = { matcher: ['/:path*'] }
