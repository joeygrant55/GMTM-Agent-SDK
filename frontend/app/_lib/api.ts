/**
 * Backend API helper.
 *
 * The FastAPI backend now requires a Clerk session JWT on every workspace request
 * (Authorization: Bearer <token>) and checks that the caller owns the resource.
 * `apiFetch` attaches that token automatically for browser calls.
 *
 * Usage: replace `fetch(`${backendUrl}/api/...`)` with `apiFetch(`${BACKEND_URL}/api/...`)`.
 * It accepts an absolute backend URL (or a bare path, which it prefixes with BACKEND_URL)
 * and merges the Authorization header into the request. Same-origin Next.js API routes
 * (relative `/api/...` paths) should keep using plain `fetch` — those proxy server-side.
 */

export const BACKEND_URL =
  process.env.NEXT_PUBLIC_BACKEND_URL ||
  'https://focused-essence-production-9809.up.railway.app'

async function getClerkToken(): Promise<string | null> {
  if (typeof window === 'undefined') return null
  try {
    // ClerkJS exposes the active session on window after ClerkProvider mounts.
    const clerk = (window as unknown as { Clerk?: { session?: { getToken?: () => Promise<string | null> } } }).Clerk
    if (clerk?.session?.getToken) {
      return await clerk.session.getToken()
    }
  } catch {
    // fall through — return null, caller still sends the request (may 401)
  }
  return null
}

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  const url = /^https?:\/\//.test(input) ? input : `${BACKEND_URL}${input.startsWith('/') ? '' : '/'}${input}`
  const token = await getClerkToken()
  const headers = new Headers(init.headers || {})
  if (token && !headers.has('Authorization')) {
    headers.set('Authorization', `Bearer ${token}`)
  }
  return fetch(url, { ...init, headers })
}
