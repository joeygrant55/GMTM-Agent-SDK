// GET /api/sparq/session -> {sub} for useSparqSession. Never returns the token.
import { type NextRequest } from 'next/server'
import { currentSession, json, signedOut } from '../server'

export const dynamic = 'force-dynamic'

export async function GET(request: NextRequest) {
  const session = await currentSession(request)
  return session ? json({ sub: session.sub }) : signedOut()
}
