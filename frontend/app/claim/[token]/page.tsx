import Link from 'next/link'
import { BACKEND_URL } from '@/app/_lib/api'

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
    const res = await fetch(`${BACKEND_URL}/api/claims/${encodeURIComponent(token)}`, { cache: 'no-store' })
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
    return (
      <div className="min-h-screen bg-sparq-charcoal flex items-center justify-center px-4">
        <div className="max-w-md w-full text-center">
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-14 h-14 rounded-2xl mx-auto mb-6" />
          <h1 className="text-2xl font-bold text-white mb-3">
            {expired ? 'This link has expired' : 'This link is not valid'}
          </h1>
          <p className="text-gray-400 mb-8">
            {expired
              ? 'Claim links last 30 days. You can still connect your GMTM profile by searching for your name.'
              : 'Check the link in your email, or connect your GMTM profile by searching for your name.'}
          </p>
          <Link
            href="/connect"
            className="inline-block px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-lg hover:bg-sparq-lime-dark transition-colors"
          >
            Connect my profile
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
          Hey {claim.first_name}, your {claim.event_name} results are in.
        </h1>
        <p className="text-gray-400 mb-8">See how you compare and what to do next.</p>
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
