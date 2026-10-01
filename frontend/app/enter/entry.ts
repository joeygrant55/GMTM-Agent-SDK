// Server-only helpers for the GMTM -> SPARQ entry routes.
import { timingSafeEqual } from 'node:crypto'
import { NextResponse } from 'next/server'

export const TX_COOKIE = '__Host-sparq-tx'
export const TICKET_COOKIE = '__Host-sparq-ticket'
export const ENTRY_HEADERS = { 'Referrer-Policy': 'no-referrer', 'Cache-Control': 'no-store' } as const

export function statesMatch(cookie: string | undefined, query: string | null): boolean {
  if (!cookie || !query) return false
  const a = Buffer.from(cookie), b = Buffer.from(query)
  return a.length === b.length && timingSafeEqual(a, b)
}

export function entryRedirect(target: URL): NextResponse {
  const response = NextResponse.redirect(target, 302)
  for (const [name, value] of Object.entries(ENTRY_HEADERS)) response.headers.set(name, value)
  return response
}
