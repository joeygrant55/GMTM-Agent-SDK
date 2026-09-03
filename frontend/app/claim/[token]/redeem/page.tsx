'use client'

// Authed leaf of the claim flow (spec 2b). Middleware guarantees a Clerk session here.
// On mount: POST /api/claims/{token}/redeem, then go to the athlete dashboard.

import { useEffect, useRef, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'

type Phase = 'working' | 'done' | 'conflict' | 'expired' | 'invalid' | 'error'

export default function ClaimRedeemPage() {
  const params = useParams()
  const token = String(params.token || '')
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [phase, setPhase] = useState<Phase>('working')
  const fired = useRef(false)

  const redeemPath = `/claim/${token}/redeem`
  const signInHref = `/sign-in?redirect_url=${encodeURIComponent(redeemPath)}`

  useEffect(() => {
    if (!isLoaded || fired.current) return
    if (!isSignedIn) {
      router.replace(signInHref)
      return
    }
    fired.current = true
    ;(async () => {
      try {
        const session = await getToken()
        const res = await apiFetch(`${BACKEND_URL}/api/claims/${encodeURIComponent(token)}/redeem`, {
          method: 'POST',
          headers: session ? { Authorization: `Bearer ${session}` } : {},
        })
        if (res.ok) {
          const data = await res.json()
          setPhase('done')
          router.replace(`/athlete/${data.user_id}`)
          return
        }
        if (res.status === 409) setPhase('conflict')
        else if (res.status === 410) setPhase('expired')
        else if (res.status === 400 || res.status === 404) setPhase('invalid')
        else setPhase('error')
      } catch {
        setPhase('error')
      }
    })()
  }, [isLoaded, isSignedIn, token, getToken, router, signInHref])

  const copy: Record<Phase, { title: string; body: string }> = {
    working: { title: 'Linking your combine results...', body: 'One second.' },
    done: { title: 'Linked', body: 'Taking you to your dashboard...' },
    conflict: {
      title: 'This link was already used',
      body: 'Another account already claimed these results. Sign in with that account, or connect your profile by name.',
    },
    expired: { title: 'This link has expired', body: 'Claim links last 30 days. Connect your profile by name instead.' },
    invalid: { title: 'This link is not valid', body: 'Check the link in your email, or connect your profile by name.' },
    error: { title: 'Something went wrong', body: 'Reload to try again, or connect your profile by name.' },
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
            {phase === 'conflict' && (
              <a href={signInHref} className="px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors">
                Sign in with the other account
              </a>
            )}
            <a href="/connect" className="px-6 py-3 border border-white/20 text-white rounded-lg hover:bg-white/5 transition-colors">
              Connect my profile by name
            </a>
          </div>
        )}
      </div>
    </div>
  )
}
