// GET /enter: start the GMTM sign-in bridge. Binds a random state to this browser.
import { randomBytes } from 'node:crypto'
import { NextResponse } from 'next/server'
import { ENTRY_HEADERS, TX_COOKIE, entryRedirect } from './entry'

export const dynamic = 'force-dynamic'

export function GET() {
  const gmtm = process.env.NEXT_PUBLIC_GMTM_WEB_URL
  if (!gmtm) return new NextResponse('SPARQ sign-in is not configured.', { status: 503, headers: ENTRY_HEADERS })
  const state = randomBytes(32).toString('base64url')
  const target = new URL('/sparq/authorize', gmtm)
  target.searchParams.set('state', state)
  const response = entryRedirect(target)
  response.cookies.set(TX_COOKIE, state, { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 300 })
  return response
}
