import Link from 'next/link'
import { apiFetch } from '@/app/_lib/api'

// Public claim landing (spec 2b). Server-fetches GET /api/claims/{token}; that call is
// what stamps `opened_at`, the funnel's "opened" signal.
export const dynamic = 'force-dynamic'

interface ClaimInfo {
  valid: boolean
  first_name?: string
  event_name?: string
  claimed?: boolean
  status: number
}

async function fetchClaim(token: string): Promise<ClaimInfo> {
  try {
    const res = await apiFetch(`/api/claims/${encodeURIComponent(token)}`, { cache: 'no-store' })
    if (!res.ok) return { valid: false, status: res.status }
    const data = await res.json()
    return { ...data, valid: Boolean(data?.valid), status: res.status }
  } catch {
    return { valid: false, status: 0 }
  }
}

export default async function ClaimPage({ params }: { params: { token: string } }) {
  const token = params.token
  const claim = await fetchClaim(token)
  const redeemPath = `/claim/${token}/redeem`
  const signUpHref = `/sign-up?redirect_url=${encodeURIComponent(redeemPath)}`
  const signInHref = `/sign-in?redirect_url=${encodeURIComponent(redeemPath)}`

  if (!claim.valid) {
    const expired = claim.status === 410
    const unavailable = claim.status === 0 || claim.status >= 500 || claim.status === 401 || claim.status === 403 || claim.status === 429
    return (
      <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-14 h-14 rounded-2xl mx-auto mb-6" />
          <h1 className="text-2xl font-bold text-white mb-3">
            {unavailable ? 'We could not check this invitation' : expired ? 'This link has expired' : 'This link is not valid'}
          </h1>
          <p className="text-gray-400 mb-8">
            {unavailable
              ? 'Your invitation has not been confirmed. Reload this page to try again, or check an existing connection below.'
              : expired
              ? 'Claim links last 30 days. Ask your combine organizer for a new invitation to connect your profile.'
              : 'Check the link in your email, or ask your combine organizer for a new invitation.'}
          </p>
          <Link
            href="/connect"
            className="inline-block px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors"
          >
            Check an existing connection
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4">
      <div className="max-w-md w-full text-center">
        <img src="/sparq-logo.jpg" alt="SPARQ" className="w-14 h-14 rounded-2xl mx-auto mb-6" />
        <h1 className="text-3xl font-bold text-white mb-3">
          Hey {claim.first_name}, connect your profile for {claim.event_name}.
        </h1>
        <p className="text-gray-400 mb-8">Open your athlete workspace, including before your first results are available. Your combine entry and requirements remain in GMTM.</p>
        <Link
          href={claim.claimed ? signInHref : signUpHref}
          className="block w-full px-6 py-4 bg-sparq-lime text-sparq-charcoal font-bold text-lg rounded-xl hover:bg-sparq-lime-dark transition-colors"
        >
          Continue
        </Link>
        <p className="text-gray-500 text-sm mt-5">
          Already have an account?{' '}
          <Link href={signInHref} className="text-sparq-lime hover:underline">
            Sign in
          </Link>
        </p>
      </div>
    </div>
  )
}
