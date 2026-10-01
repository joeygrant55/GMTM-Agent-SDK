// GET /enter/callback?code&state: check the browser-bound state, then exchange the
// one-use GMTM code server to server. The backend returns a 24 h SPARQ session token
// bound to the browser's GMTM session (gsh = sha256 of sessionId, computed by the
// middleware; the raw value never leaves it). The token goes only into an HttpOnly
// cookie, never a URL. No Clerk on this surface.
import { type NextRequest } from 'next/server'
import { resolveBackendOrigin } from '@/lib/backend-config.cjs'
import { GSH_HEADER, sessionCookie } from '@/lib/sparq-session.cjs'
import { TX_COOKIE, entryRedirect, statesMatch } from '../entry'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get('code')
  const state = request.nextUrl.searchParams.get('state')
  const gsh = request.headers.get(GSH_HEADER)
  const go = (path: string) => {
    const response = entryRedirect(new URL(path, request.url))
    response.cookies.set(TX_COOKIE, '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 0 })
    return response
  }
  if (!code || !statesMatch(request.cookies.get(TX_COOKIE)?.value, state)) return go('/enter/unavailable?reason=retry')
  const secret = process.env.SPARQ_ENTRY_SECRET
  if (!secret || !gsh || !/^[0-9a-f]{64}$/.test(gsh)) return go('/enter/unavailable?reason=retry')
  try {
    const backend = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
    const res = await fetch(`${backend}/gmtm-entry/exchange`, {
      method: 'POST', cache: 'no-store', redirect: 'error',
      headers: { 'Content-Type': 'application/json', 'x-sparq-entry-secret': secret },
      body: JSON.stringify({ code, state, gsh }),
    })
    if (res.status === 409) return go('/enter/unavailable?reason=linked')
    const data = res.ok ? await res.json() : null
    if (data?.eligible === false) return go('/enter/unavailable')
    if (data?.eligible === true && typeof data.token === 'string' && data.token) {
      const response = go('/home')
      response.cookies.set(sessionCookie(data.token))
      return response
    }
  } catch { /* fall through: never echo backend errors */ }
  return go('/enter/unavailable?reason=retry')
}
