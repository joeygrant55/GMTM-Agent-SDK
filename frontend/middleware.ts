import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse, type NextRequest, type NextFetchEvent } from 'next/server'
import { candidatePagePolicy, isRestrictedSurface, resolveBackendOrigin } from './lib/backend-config.cjs'

const isPublicRoute = createRouteMatcher([
  '/', '/sign-in(.*)', '/sign-up(.*)', '/connect', '/demo', '/quick-scan',
  '/athlete/(.*)', '/report/(.*)', '/claim/(.*)',
])
const isClaimRedeemRoute = createRouteMatcher(['/claim/(.*)/redeem'])
const isOnboardingRoute = createRouteMatcher(['/onboarding(.*)'])
const combine = isRestrictedSurface(process.env.NEXT_PUBLIC_APP_SURFACE)
const backendUrl = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
const authenticatedMiddleware = clerkMiddleware(async (auth, request) => {
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
    const policy = candidatePagePolicy(pathname, request.method)
    // This runs before Clerk, all page handlers and same-origin API routes.
    if (policy === 'deny') return new NextResponse('Not found', { status: 404, headers: { 'Cache-Control': 'no-store' } })
    if (policy === 'asset') return NextResponse.next()
    if (policy === 'home') {
      const home = new URL('/home', request.url)
      home.search = request.nextUrl.search
      return NextResponse.redirect(home)
    }
  } else if (!/^\/(api|trpc)(?:\/|$)/.test(pathname) && (
    pathname.startsWith('/_next') || /\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)$/.test(pathname)
  )) {
    // Preserve the normal app's historical static-file authentication exemption.
    return NextResponse.next()
  }
  return authenticatedMiddleware(request, event)
}

// Include static-looking dynamic URLs and API handlers in the candidate boundary.
export const config = { matcher: ['/:path*'] }
