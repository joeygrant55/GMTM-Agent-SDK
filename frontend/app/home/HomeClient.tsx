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
      <div className="h-full min-h-screen bg-sparq-charcoal text-white flex items-center justify-center">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-gray-400">Loading your workspace...</p>
        </div>
      </div>
    )
  }

  return (
    <div className="text-white pb-8">
      <div className="p-8 pb-0">
        <h1 className="text-3xl font-black text-white">Welcome back 👋</h1>
        <p className="text-gray-400 mt-1">Your recruiting workspace</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4 p-8">
        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <div className="text-2xl mb-3">🎯</div>
          <h2 className="font-bold text-white">New College Matches</h2>
          <p className="text-gray-400 text-sm mt-2">12 programs matched to your profile.</p>
          <Link href="/home/colleges" className="inline-block mt-4 text-sparq-lime font-semibold">
            View Matches →
          </Link>
        </div>

        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <div className="text-2xl mb-3">✉️</div>
          <h2 className="font-bold text-white">Draft Coach Emails</h2>
          <p className="text-gray-400 text-sm mt-2">Start reaching out to your top programs.</p>
          <p className="mt-4 text-gray-500 font-semibold">Coming Soon</p>
        </div>

        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <div className="text-2xl mb-3">📊</div>
          <h2 className="font-bold text-white">Complete Your Profile</h2>
          <p className="text-gray-400 text-sm mt-2">Add combine metrics to improve your matches.</p>
          <p className="mt-4 text-gray-500 font-semibold">Update Profile</p>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-4 px-8">
        <div className="bg-white/[0.04] border border-white/10 rounded-xl p-4 text-center">
          <div className="text-3xl font-black text-sparq-lime">0</div>
          <div className="text-gray-400 text-sm mt-1">Colleges Tracked</div>
        </div>
        <div className="bg-white/[0.04] border border-white/10 rounded-xl p-4 text-center">
          <div className="text-3xl font-black text-sparq-lime">0</div>
          <div className="text-gray-400 text-sm mt-1">Outreach Sent</div>
        </div>
        <div className="bg-white/[0.04] border border-white/10 rounded-xl p-4 text-center">
          <div className="text-3xl font-black text-sparq-lime">0</div>
          <div className="text-gray-400 text-sm mt-1">Responses</div>
        </div>
      </div>

      <div className="px-8 pb-8 mt-8">
        <h2 className="text-lg font-bold text-white mb-4">Recruiting Calendar</h2>
        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 space-y-3">
          <div className="flex items-center gap-3 text-gray-300">
            <span className="text-sparq-lime">●</span>
            <span>Junior Days — Spring 2026</span>
          </div>
          <div className="flex items-center gap-3 text-gray-300">
            <span className="text-sparq-lime">●</span>
            <span>Summer Camp Circuit — June–July 2026</span>
          </div>
          <div className="flex items-center gap-3 text-gray-300">
            <span className="text-sparq-lime">●</span>
            <span>Early Signing Period — Dec 3–5, 2026</span>
          </div>
          <div className="flex items-center gap-3 text-gray-300">
            <span className="text-sparq-lime">●</span>
            <span>National Signing Day — Feb 4, 2027</span>
          </div>
        </div>
      </div>
    </div>
  )
}
