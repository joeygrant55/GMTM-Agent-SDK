'use client'

import { useEffect } from 'react'
import Link from 'next/link'
import { useRouter, useSearchParams } from 'next/navigation'
import { useUser } from '@clerk/nextjs'

export default function HomeClient() {
  const { user, isLoaded } = useUser()
  const router = useRouter()
  const searchParams = useSearchParams()
  const requestedEvent = searchParams.get('event_id')
  // Preserve even an invalid selection so the combine view can ask the athlete
  // to choose, instead of silently substituting a previously claimed event.
  const destination = requestedEvent !== null
    ? `/home/inbox?event_id=${encodeURIComponent(requestedEvent)}`
    : '/home/inbox'

  useEffect(() => {
    if (!isLoaded || !user?.id) return
    // Public combine requirements are useful before a recruiting profile exists.
    // Ownership and personal progress are resolved by the combine service itself.
    router.replace(destination)
  }, [isLoaded, user?.id, router, destination])

  return (
    <div className="h-full min-h-screen bg-sparq-charcoal text-white flex items-center justify-center">
      <div className="text-center">
        {isLoaded && !user?.id ? (
          <Link className="text-sparq-lime underline" href={`/sign-in?redirect_url=${encodeURIComponent(destination)}`}>
            Sign in to your workspace
          </Link>
        ) : (
          <>
            <div aria-hidden="true" className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p role="status" className="text-gray-400">Loading your workspace…</p>
          </>
        )}
      </div>
    </div>
  )
}
