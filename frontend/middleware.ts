import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse, type NextRequest, type NextFetchEvent } from 'next/server'
import { candidatePagePolicy, isProfileSurface, isRestrictedSurface, profileContentSecurityPolicy, resolveBackendOrigin, withoutGmtmSession } from './lib/backend-config.cjs'
import { GSH_HEADER, SESSION_COOKIE, clearedSessionCookie, gmtmSessionHash, verifySession } from './lib/sparq-session.cjs'

const isPublicRoute = createRouteMatcher([
  '/', '/sign-in(.*)', '/sign-up(.*)', '/connect', '/demo', '/quick-scan',
  '/athlete/(.*)', '/report/(.*)', '/claim/(.*)', '/enter(.*)',
])
const isClaimRedeemRoute = createRouteMatcher(['/claim/(.*)/redeem'])
const isOnboardingRoute = createRouteMatcher(['/onboarding(.*)'])
const combine = isRestrictedSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
const profile = isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
const backendUrl = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)

// Profile surface (no Clerk): per-request nonce CSP (Next reads it from the request
// headers). GMTM's sessionId cookie is removed before any handler; handlers get only
// its sha256 in x-sparq-gsh (a client-sent value is always dropped).
function profileResponse(request: NextRequest, gsh: string | null) {
  const nonce = btoa(crypto.randomUUID())
  const csp = profileContentSecurityPolicy({ nonce, dev: process.env.NODE_ENV !== 'production' })
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
// Every profile page except the /enter bridge needs a SPARQ session bound to the
// browser's current GMTM session. Otherwise clear it and re-enter (GMTM cookie
// present: a new GMTM user replaces the old one) or go back to GMTM.
async function profileMiddleware(request: NextRequest, policy: string) {
  const gsh = await gmtmSessionHash(request.headers.get('cookie'))
  if (policy === 'page' && !/^\/enter(?:\/|$)/.test(request.nextUrl.pathname)) {
    const token = request.cookies.get(SESSION_COOKIE)?.value
    if (!await verifySession(token, process.env.SPARQ_SESSION_SECRET, gsh)) {
      const target = gsh ? new URL('/enter', request.url) : new URL('/', process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com')
      const response = NextResponse.redirect(target)
      response.headers.set('Cache-Control', 'no-store')
      if (token !== undefined) response.cookies.set(clearedSessionCookie())
      return response
    }
  }
  return profileResponse(request, gsh)
}

// Clerk serves the legacy and combine surfaces only; it is never built on profile.
const authenticatedMiddleware = profile ? null : clerkMiddleware(async (auth, request) => {
  if (isClaimRedeemRoute(request) || !isPublicRoute(request)) {
    const { userId, getToken } = await auth()
    if (!userId) {
      const signInUrl = new URL('/sign-in', request.url)
      signInUrl.searchParams.set('redirect_url', request.url)
      return NextResponse.redirect(signInUrl)
    }
    if (!combine && isOnboardingRoute(request)) {
      try {
        const token = await getToken()
        const res = await fetch(`${backendUrl}/api/profile/by-clerk/${userId}`, {
          method: 'GET', redirect: 'error',
          headers: { Accept: 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}) },
        })
        if (res.ok && (await res.json())?.found) return NextResponse.redirect(new URL('/home', request.url))
      } catch { /* Unknown recovery does not prevent ordinary onboarding. */ }
    }
  }
})

export default function middleware(request: NextRequest, event: NextFetchEvent) {
  const pathname = request.nextUrl.pathname
  if (combine) {
    const policy = candidatePagePolicy(pathname, request.method, process.env.NEXT_PUBLIC_APP_SURFACE)
    // This runs before Clerk, all page handlers and same-origin API routes.
    if (policy === 'deny') return new NextResponse('Not found', { status: 404, headers: { 'Cache-Control': 'no-store' } })
    if (policy === 'asset') return NextResponse.next()
    if (policy === 'home') {
      const home = new URL('/home', request.url)
      home.search = request.nextUrl.search
      return NextResponse.redirect(home)
    }
    if (profile) return profileMiddleware(request, policy)
  } else if (!/^\/(api|trpc)(?:\/|$)/.test(pathname) && (
    pathname.startsWith('/_next') || /\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)$/.test(pathname)
  )) {
    // Preserve the normal app's historical static-file authentication exemption.
    return NextResponse.next()
  }
  return authenticatedMiddleware!(request, event)
}

// Include static-looking dynamic URLs and API handlers in the candidate boundary.
export const config = { matcher: ['/:path*'] }
