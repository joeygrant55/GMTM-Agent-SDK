'use client'

// Profile surface identity (no Clerk). {sub} comes from GET /api/sparq/session; the
// token itself stays in its HttpOnly cookie. Same shape as Clerk's useUser
// ({ isLoaded, user: { id } }) so profile components read user.id unchanged.
import { useEffect, useState } from 'react'

export type SparqSession = { isLoaded: boolean; user: { id: string } | null }

let pending: Promise<string | null> | null = null

function loadSub(): Promise<string | null> {
  pending ??= fetch('/api/sparq/session', { cache: 'no-store', credentials: 'same-origin' })
    .then(async res => {
      const body = res.ok ? await res.json() : null
      return typeof body?.sub === 'string' && body.sub ? body.sub : null
    })
    .catch(() => null)
  return pending
}

export function useSparqSession(): SparqSession {
  const [state, setState] = useState<SparqSession>({ isLoaded: false, user: null })
  useEffect(() => {
    let live = true
    loadSub().then(sub => { if (live) setState({ isLoaded: true, user: sub ? { id: sub } : null }) })
    return () => { live = false }
  }, [])
  return state
}

// Clear the cookie and end the session server-side, then leave for GMTM.
export async function signOutOfSparq(): Promise<void> {
  let next = process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com'
  try {
    const res = await fetch('/api/sparq/sign-out', { method: 'POST', cache: 'no-store', credentials: 'same-origin' })
    const body = res.ok ? await res.json() : null
    if (typeof body?.next === 'string') next = body.next
  } catch { /* still leave; the cookie expires within 24 h */ }
  pending = null
  window.location.assign(next)
}
