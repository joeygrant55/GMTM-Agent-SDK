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
  '/privacy',
  '/terms',
])
const isOnboardingRoute = createRouteMatcher(['/onboarding(.*)'])
const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export default clerkMiddleware(async (auth, request) => {
  if (!isPublicRoute(request)) {
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
          // Only skip onboarding for users who completed SPARQ onboarding.
          // Legacy GMTM-linked users (found=true, has_sparq_profile=false) must be
          // allowed through — redirecting them to /home caused an infinite loop
          // (HomeClient sends profile-less users right back to /onboarding/search).
          if (data?.has_sparq_profile) {
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
