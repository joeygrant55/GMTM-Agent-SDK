'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUser } from '@clerk/nextjs'
import { apiFetch } from '@/app/_lib/api'
import { ProfileConnectionError, readProfileConnectionResponse } from '@/app/_lib/profileConnection'

export default function CombineConnectionRecovery({ eventId, profileMode = false }: { eventId: number | null; profileMode?: boolean }) {
  const { user, isLoaded } = useUser()
  const eventQuery = !profileMode && (eventId === 1317 || eventId === 1318) ? `?event_id=${eventId}` : ''
  const destination = `/home/inbox${eventQuery}`
  const signInHref = `/sign-in?redirect_url=${encodeURIComponent(`/connect${eventQuery}`)}`

  return (
    <main className="flex min-h-screen items-center justify-center bg-sparq-charcoal px-4 py-8 text-white">
      <section aria-labelledby="combine-connection-title" className="w-full max-w-lg rounded-2xl border border-white/15 p-6">
        <h1 id="combine-connection-title" className="text-2xl font-black">Check your existing connection</h1>
        {!isLoaded ? <p role="status" className="mt-4 text-gray-300">Loading your account…</p> : !user?.id ? <>
          <p className="mt-4 text-gray-300">Sign in to check whether your GMTM athlete profile is already connected.</p>
          <a href={signInHref} className="mt-4 inline-flex min-h-11 items-center font-bold text-sparq-lime underline">Sign in</a>
        </> : <ConnectionCheck key={`${user.id}:${eventQuery}`} clerkId={user.id} destination={destination} signInHref={signInHref} profileMode={profileMode} />}
      </section>
    </main>
  )
}

function ConnectionCheck({ clerkId, destination, signInHref, profileMode }: { clerkId: string; destination: string; signInHref: string; profileMode: boolean }) {
  const router = useRouter()
  const [attempt, setAttempt] = useState(0)
  const [phase, setPhase] = useState<'checking' | 'linked' | 'unlinked' | 'error'>('checking')
  const [failure, setFailure] = useState<ProfileConnectionError | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    setPhase('checking')
    setFailure(null)
    ;(async () => {
      try {
        const response = await apiFetch(`/api/profile/by-clerk/${encodeURIComponent(clerkId)}`, { signal: controller.signal, cache: 'no-store' })
        const connection = await readProfileConnectionResponse(response)
        if (controller.signal.aborted) return
        if (connection.found) {
          setPhase('linked')
          router.replace(destination)
        } else setPhase('unlinked')
      } catch (error) {
        if (controller.signal.aborted) return
        setFailure(error instanceof ProfileConnectionError ? error : new ProfileConnectionError())
        setPhase('error')
      }
    })()
    return () => controller.abort()
  }, [clerkId, destination, router, attempt])

  return (
    <div className="mt-4 text-sm leading-relaxed text-gray-300">
      {phase === 'checking' && <p role="status">Checking your existing connection…</p>}
      {phase === 'linked' && <p role="status">Your connection is confirmed. Returning to your {profileMode ? 'profile' : 'combine'}…</p>}
      {phase === 'unlinked' && <p>No existing connection was found. Open your organizer’s secure invitation to connect your GMTM athlete profile. If you need a new invitation, contact your combine organizer.</p>}
      {phase === 'error' && <>
        <p role="alert">{failure?.message}</p>
        <p className="mt-2">This check has not confirmed whether a profile is connected.</p>
        {failure?.status === 401 && <a href={signInHref} className="mt-3 inline-flex min-h-11 items-center font-bold text-sparq-lime underline">Sign in again</a>}
      </>}
      {(phase === 'error' || phase === 'unlinked') && <button type="button" onClick={() => setAttempt(value => value + 1)} className="mt-4 flex min-h-11 items-center rounded-lg border border-white/20 px-4 font-bold text-white">{phase === 'error' ? 'Try again' : 'Check again'}</button>}
      {phase !== 'linked' && <a href={destination} className="mt-4 inline-flex min-h-11 items-center font-bold text-sparq-lime underline">Return to your {profileMode ? 'profile' : 'combine'}</a>}
    </div>
  )
}
