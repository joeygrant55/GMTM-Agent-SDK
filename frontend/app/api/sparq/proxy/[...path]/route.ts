// /api/sparq/proxy/<backend path>: the browser's only authenticated route to the backend.
// Refuses any operation the selected surface does not allow
// BEFORE reading the session, then forwards with the HttpOnly session as a bearer.
import { NextResponse, type NextRequest } from 'next/server'
import { resolveAPIRequest } from '@/lib/backend-config.cjs'
import { NO_STORE, currentSession, json, sameOriginWrite, signedOut } from '../../server'

export const dynamic = 'force-dynamic'
const PREFIX = '/api/sparq/proxy'

async function forward(request: NextRequest): Promise<NextResponse> {
  let url: string
  try {
    // Raw pathname (no decoding); resolveAPIRequest refuses encoded dots/slashes.
    const path = request.nextUrl.pathname.slice(PREFIX.length)
    url = resolveAPIRequest(path + request.nextUrl.search, process.env.NEXT_PUBLIC_BACKEND_URL || '', process.env.NEXT_PUBLIC_APP_SURFACE, request.method)
  } catch {
    return json({ detail: 'Not found' }, 404)
  }
  if (!sameOriginWrite(request)) return json({ detail: 'Forbidden' }, 403)
  const session = await currentSession(request)
  if (!session) return signedOut()
  const headers: Record<string, string> = { Authorization: `Bearer ${session.token}`, Accept: request.headers.get('accept') || 'application/json' }
  const type = request.headers.get('content-type')
  if (type) headers['Content-Type'] = type
  try {
    const res = await fetch(url, {
      method: request.method, headers, cache: 'no-store', redirect: 'error',
      body: request.method === 'GET' || request.method === 'DELETE' ? undefined : await request.arrayBuffer(),
    })
    const out: Record<string, string> = { ...NO_STORE }
    const resType = res.headers.get('content-type')
    if (resType) out['Content-Type'] = resType
    return new NextResponse(res.body, { status: res.status, headers: out })
  } catch {
    return json({ detail: 'SPARQ is temporarily unavailable.' }, 502)
  }
}

export const GET = forward
export const POST = forward
export const PATCH = forward
export const PUT = forward
export const DELETE = forward
