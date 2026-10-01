// Server-only helpers for the profile surface's same-origin SPARQ routes. The
// session token stays in its HttpOnly cookie; browser JS never sees it.
import { NextResponse, type NextRequest } from 'next/server'
import { isProfileSurface } from '@/lib/backend-config.cjs'
import { GSH_HEADER, SESSION_COOKIE, clearedSessionCookie, verifySession } from '@/lib/sparq-session.cjs'

export const NO_STORE = { 'Cache-Control': 'private, no-store' } as const

export function json(body: unknown, status = 200): NextResponse {
  return NextResponse.json(body, { status, headers: NO_STORE })
}

// The session token, only when it is valid AND bound to this browser's current GMTM
// session (x-sparq-gsh is set by the middleware from the sessionId cookie).
export async function currentSession(request: NextRequest): Promise<{ token: string; sub: string } | null> {
  if (!isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return null
  const token = request.cookies.get(SESSION_COOKIE)?.value
  const claims = token ? await verifySession(token, process.env.SPARQ_SESSION_SECRET, request.headers.get(GSH_HEADER)) : null
  return token && claims ? { token, sub: claims.sub } : null
}

// Writes must come from this exact origin. SameSite=Lax still sends the cookie on
// same-site requests from another gmtm.com subdomain, so check the fetch metadata.
export function sameOriginWrite(request: NextRequest): boolean {
  if (request.method === 'GET' || request.method === 'HEAD') return true
  return request.headers.get('sec-fetch-site') === 'same-origin' || request.headers.get('origin') === request.nextUrl.origin
}

export function signedOut(): NextResponse {
  const response = json({ detail: 'Your SPARQ session ended. Open SPARQ from GMTM again.' }, 401)
  response.cookies.set(clearedSessionCookie())
  return response
}
