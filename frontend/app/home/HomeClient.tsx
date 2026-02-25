'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useUser } from '@clerk/nextjs'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export default function HomeClient() {
  const { user, isLoaded } = useUser()
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isLoaded || !user?.id) return

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
    fetch(`${backendUrl}/api/profile/by-clerk/${user.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (data?.found && data?.user_id) {
          window.location.href = `/athlete/${data.user_id}`
          return
        }
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [isLoaded, user?.id])

  if (loading) {
    return (
      <div className="min-h-screen bg-sparq-charcoal text-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading your workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white flex items-center justify-center px-4">
      <div className="max-w-xl w-full bg-white/[0.04] border border-white/10 rounded-2xl p-8 text-center">
        <div className="w-16 h-16 bg-sparq-lime/10 border border-sparq-lime/20 rounded-2xl flex items-center justify-center mx-auto mb-6">
          <span className="text-3xl">🏈</span>
        </div>
        <h1 className="text-3xl font-black text-white mb-3">Your Workspace is Ready</h1>
        <p className="text-gray-400 mb-8 leading-relaxed">
          Connect your athlete profile to open your personalized recruiting dashboard — college matches, outreach tracker, and AI recruiting advisor.
        </p>
        <Link
          href="/connect"
          className="inline-flex items-center gap-2 px-8 py-4 bg-sparq-lime text-sparq-charcoal font-black rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105 shadow-lg shadow-sparq-lime/25"
        >
          Connect Profile →
        </Link>
        <p className="text-gray-600 text-xs mt-4">
          Already connected?{' '}
          <Link href="/quick-scan" className="text-sparq-lime hover:underline">
            View your Quick Scan →
          </Link>
        </p>
      </div>
    </div>
  )
}
