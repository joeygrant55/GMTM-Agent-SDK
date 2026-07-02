'use client'

import { apiFetch } from '@/app/_lib/api'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useUser } from '@clerk/nextjs'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export default function HomeClient() {
  const { user, isLoaded } = useUser()
  const router = useRouter()

  useEffect(() => {
    if (!isLoaded || !user?.id) return
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

    apiFetch(`${backendUrl}/api/profile/by-clerk/${user.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (!data?.has_sparq_profile) {
          router.replace('/onboarding/search')
        } else {
          router.replace('/home/inbox')
        }
      })
      .catch(() => {
        router.replace('/home/inbox')
      })
  }, [isLoaded, user?.id, router])

  return (
    <div className="h-full min-h-screen bg-sparq-charcoal text-white flex items-center justify-center">
      <div className="text-center">
        <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-4" />
        <p className="text-gray-400">Loading your workspace…</p>
      </div>
    </div>
  )
}
