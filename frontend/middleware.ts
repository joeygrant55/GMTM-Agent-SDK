import { clerkMiddleware, createRouteMatcher } from '@clerk/nextjs/server'
import { NextResponse } from 'next/server'

const isPublicRoute = createRouteMatcher([
  '/',
  '/sign-in(.*)',
  '/sign-up(.*)',
  '/connect',
  '/demo',
  '/quick-scan',
  '/athlete/(.*)',
  '/report/(.*)',
  '/claim/(.*)',
])
// The claim landing is public, but its /redeem leaf must run with a Clerk session.
// Checked before isPublicRoute so it wins over the '/claim/(.*)' entry above.
const isClaimRedeemRoute = createRouteMatcher(['/claim/(.*)/redeem'])
const isOnboardingRoute = createRouteMatcher(['/onboarding(.*)'])
const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export default clerkMiddleware(async (auth, request) => {
  if (isClaimRedeemRoute(request) || !isPublicRoute(request)) {
    const { userId, getToken } = await auth()
    if (!userId) {
      const signInUrl = new URL('/sign-in', request.url)
      signInUrl.searchParams.set('redirect_url', request.url)
      return NextResponse.redirect(signInUrl)
    }

    if (isOnboardingRoute(request)) {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
      try {
        const token = await getToken()
        const res = await fetch(`${backendUrl}/api/profile/by-clerk/${userId}`, {
          method: 'GET',
          headers: {
            Accept: 'application/json',
            ...(token ? { Authorization: `Bearer ${token}` } : {}),
          },
        })

        if (res.ok) {
          const data = await res.json()
          if (data?.found) {
            return NextResponse.redirect(new URL('/home', request.url))
          }
        }
      } catch {
        // If the backend check fails, allow onboarding to proceed.
      }
    }
  }
})

export const config = {
  matcher: [
    '/((?!_next|[^?]*\\.(?:html?|css|js(?!on)|jpe?g|webp|png|gif|svg|ttf|woff2?|ico|csv|docx?|xlsx?|zip|webmanifest)).*)',
    '/(api|trpc)(.*)',
  ],
}
