/**
 * Backend API helper.
 *
 * GMTM is the only sign-in (Joey, 2026-10-01). The backend accepts only a SPARQ
 * session token, which stays in its HttpOnly cookie. Browser calls go to the
 * same-origin /api/sparq/proxy, which adds the session as the bearer.
 *
 * Usage: `apiFetch(`${BACKEND_URL}/api/...`)`. It accepts an absolute backend URL (or
 * a bare path) and refuses any operation the selected surface does not allow.
 * Same-origin Next.js API routes (relative `/api/...` paths) keep using plain `fetch`.
 */

import { resolveBackendOrigin, resolveAPIRequest } from '@/lib/backend-config.cjs'

export const BACKEND_URL = resolveBackendOrigin(process.env.NEXT_PUBLIC_BACKEND_URL)

export async function apiFetch(input: string, init: RequestInit = {}): Promise<Response> {
  // Validate before the request. Never forward to a caller-supplied origin or
  // follow a redirect outside the supported API surface.
  const url = resolveAPIRequest(input, BACKEND_URL, process.env.NEXT_PUBLIC_APP_SURFACE, init.method || 'GET')
  const backend = new URL(url)
  return fetch('/api/sparq/proxy' + backend.pathname + backend.search, { ...init, credentials: 'same-origin', redirect: 'error' })
}
