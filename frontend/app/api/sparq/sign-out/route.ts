// POST /api/sparq/sign-out: end the jti on the backend (best effort), always clear
// the cookie. SameSite=Lax keeps the cookie off cross-site POSTs.
import { type NextRequest } from 'next/server'
import { resolveBackendOrigin } from '@/lib/backend-config.cjs'
import { SESSION_COOKIE, clearedSessionCookie } from '@/lib/sparq-session.cjs'
import { json, sameOriginWrite } from '../server'

export const dynamic = 'force-dynamic'

export async function POST(request: NextRequest) {
  if (!sameOriginWrite(request)) return json({ detail: 'Forbidden' }, 403)
  const token = request.cookies.get(SESSION_COOKIE)?.value
  if (token) {
    try {
      await fetch(`${resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)}/gmtm-entry/sign-out`, {
        method: 'POST', cache: 'no-store', redirect: 'error', headers: { Authorization: `Bearer ${token}` },
      })
    } catch { /* the cookie is cleared anyway; the jti expires within 24 h */ }
  }
  const response = json({ signed_out: true, next: process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com' })
  response.cookies.set(clearedSessionCookie())
  return response
}
