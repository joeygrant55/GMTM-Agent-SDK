'use client'

// Authed leaf of the claim flow (spec 2b). Middleware guarantees a Clerk session here.
// On mount: POST /api/claims/{token}/redeem, then go to the athlete dashboard.

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'

type Phase = 'working' | 'done' | 'conflict' | 'expired' | 'invalid' | 'error'

export default function ClaimRedeemPage() {
  const params = useParams()
  const token = String(params.token || '')
  const router = useRouter()
  const { isLoaded, isSignedIn, userId, getToken } = useAuth()

  const redeemPath = `/claim/${token}/redeem`
  const signInHref = `/sign-in?redirect_url=${encodeURIComponent(redeemPath)}`

  useEffect(() => {
    if (isLoaded && !isSignedIn) router.replace(signInHref)
  }, [isLoaded, isSignedIn, router, signInHref])

  if (!isLoaded || !isSignedIn || !userId) {
    return <p role="status" className="min-h-screen bg-sparq-charcoal text-gray-300 flex items-center justify-center">Checking your account…</p>
  }
  return <ClaimRedemption key={`${userId}:${token}`} clerkId={userId} token={token} getToken={getToken} signInHref={signInHref} />
}

function ClaimRedemption({ clerkId, token, getToken, signInHref }: {
  clerkId: string
  token: string
  getToken: ReturnType<typeof useAuth>['getToken']
  signInHref: string
}) {
  const router = useRouter()
  const [phase, setPhase] = useState<Phase>(token ? 'working' : 'invalid')
  const [attempt, setAttempt] = useState(0)

  useEffect(() => {
    if (!token) return
    const controller = new AbortController()
    setPhase('working')
    ;(async () => {
      try {
        const session = await getToken()
        if (controller.signal.aborted) return
        if (!session) throw new Error('Session unavailable')
        const res = await apiFetch(`${BACKEND_URL}/api/claims/${encodeURIComponent(token)}/redeem`, {
          method: 'POST',
          signal: controller.signal,
          headers: { Authorization: `Bearer ${session}` },
        })
        if (controller.signal.aborted) return
        if (res.ok) {
          const data = await res.json()
          if (controller.signal.aborted) return
          if (data?.connected !== true || data.clerk_id !== clerkId || !Number.isSafeInteger(data.user_id) || data.user_id <= 0 || typeof data.workspace_ready !== 'boolean') {
            throw new Error('Profile connection was not confirmed')
          }
          setPhase('done')
          // The workspace (/home) is the real product; the legacy dashboard is the fallback
          // only if the workspace row could not be built.
          // Carry only the supported, server-confirmed event; older invitations retain their fallback.
          const eventQuery = data.event_id === 1317 || data.event_id === 1318 ? `?event_id=${data.event_id}` : ''
          router.replace(eventQuery || data.workspace_ready ? `/home/inbox${eventQuery}` : `/athlete/${data.user_id}`)
          return
        }
        if (res.status === 409) setPhase('conflict')
        else if (res.status === 410) setPhase('expired')
        else if (res.status === 400 || res.status === 404) setPhase('invalid')
        else setPhase('error')
      } catch {
        if (!controller.signal.aborted) setPhase('error')
      }
    })()
    return () => controller.abort()
  }, [clerkId, token, getToken, router, attempt])

  const copy: Record<Phase, { title: string; body: string }> = {
    working: { title: 'Connecting your athlete profile...', body: 'One second.' },
    done: { title: 'Linked', body: 'Taking you to your workspace...' },
    conflict: {
      title: 'This profile could not be connected',
      body: 'Try again, check that you are signed in to the intended account, or contact your combine organizer for help.',
    },
    expired: { title: 'This link has expired', body: 'Claim links last 30 days. Ask your combine organizer for a new invitation.' },
    invalid: { title: 'This link is not valid', body: 'Check the link in your email, or ask your combine organizer for a new invitation.' },
    error: { title: 'Something went wrong', body: 'Try again. If this keeps happening, contact your combine organizer for help.' },
  }
  const { title, body } = copy[phase]
  const busy = phase === 'working' || phase === 'done'

  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        {busy ? (
          <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-6" />
        ) : (
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-14 h-14 rounded-2xl mx-auto mb-6" />
        )}
        <h1 className="text-2xl font-bold text-white mb-3">{title}</h1>
        <p className="text-gray-400 mb-8">{body}</p>
        {!busy && (
          <div className="flex flex-col gap-3">
            {(phase === 'conflict' || phase === 'error') && (
              <button type="button" onClick={() => setAttempt(value => value + 1)} className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
                Try again
              </button>
            )}
            {phase === 'conflict' && (
              <a href={signInHref} className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
                Sign in
              </a>
            )}
            <a href="/connect" className="px-6 py-3 border border-white/20 text-white rounded-lg hover:bg-white/5 transition-colors">
              Check an existing connection
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
