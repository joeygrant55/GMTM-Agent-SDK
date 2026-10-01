// GET /enter/callback?code&state: check the browser-bound state, then exchange the
// one-use GMTM code server to server. The ticket goes to a 60 s HttpOnly cookie,
// never into a URL; /enter/finish completes the Clerk sign-in.
import { type NextRequest } from 'next/server'
import { resolveBackendOrigin } from '@/lib/backend-config.cjs'
import { TICKET_COOKIE, TX_COOKIE, entryRedirect, statesMatch } from '../entry'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const code = request.nextUrl.searchParams.get('code')
  const state = request.nextUrl.searchParams.get('state')
  const go = (path: string) => {
    const response = entryRedirect(new URL(path, request.url))
    response.cookies.set(TX_COOKIE, '', { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 0 })
    return response
  }
  if (!code || !statesMatch(request.cookies.get(TX_COOKIE)?.value, state)) return go('/enter/unavailable?reason=retry')
  const secret = process.env.SPARQ_ENTRY_SECRET
  if (!secret) return go('/enter/unavailable?reason=retry')
  try {
    const backend = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)
    const res = await fetch(`${backend}/gmtm-entry/exchange`, {
      method: 'POST', cache: 'no-store', redirect: 'error',
      headers: { 'Content-Type': 'application/json', 'x-sparq-entry-secret': secret },
      body: JSON.stringify({ code, state }),
    })
    if (res.status === 409) return go('/enter/unavailable?reason=linked')
    const data = res.ok ? await res.json() : null
    if (data?.eligible === false) return go('/enter/unavailable')
    if (data?.eligible === true && typeof data.ticket === 'string' && data.ticket) {
      const response = go('/enter/finish')
      response.cookies.set(TICKET_COOKIE, data.ticket, { httpOnly: true, secure: true, sameSite: 'lax', path: '/', maxAge: 60 })
      return response
    }
  } catch { /* fall through: never echo backend errors */ }
  return go('/enter/unavailable?reason=retry')
}
