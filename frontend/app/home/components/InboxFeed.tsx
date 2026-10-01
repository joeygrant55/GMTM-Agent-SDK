'use client'

import { apiFetch, BACKEND_URL } from '@/app/_lib/api'
import { useEffect, useRef, useState } from 'react'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import Link from 'next/link'
import ArtifactCard from './ArtifactCard'
import { Artifact } from './artifactStatus'
import AthleteStartingPoint, { AthleteHomeProfile } from './AthleteStartingPoint'
import CurrentCombineCard from './CurrentCombineCard'

export default function InboxFeed() {
  const { user, isLoaded } = useSparqSession()
  const subject = user?.id
  const activeSubject = useRef(subject)
  activeSubject.current = subject
  const [ownerId, setOwnerId] = useState<string>()
  const [profile, setProfile] = useState<AthleteHomeProfile | null>(null)
  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)
  const [profileError, setProfileError] = useState(false)
  const [inboxError, setInboxError] = useState(false)
  const [actionError, setActionError] = useState('')
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [reload, setReload] = useState(0)

  useEffect(() => {
    if (!isLoaded || !subject) return
    const controller = new AbortController()
    setOwnerId(subject)
    setLoading(true)
    setProfile(null)
    setArtifacts([])
    setProfileError(false)
    setInboxError(false)
    setActionError('')
    setPendingId(null)
    const read = async (path: string) => {
      const res = await apiFetch(`${BACKEND_URL}${path}`, { signal: controller.signal })
      if (!res.ok) throw new Error(`Request failed: ${res.status}`)
      return res.json()
    }
    // Independent reads: an inbox failure must not hide the athlete's results.
    Promise.allSettled([
      read(`/api/workspace/profile/${subject}`),
      read(`/api/workspace/inbox/${subject}`),
    ]).then(([profileResult, inboxResult]) => {
      if (controller.signal.aborted) return
      if (profileResult.status === 'fulfilled' && profileResult.value?.clerk_id === subject) {
        setProfile(profileResult.value)
      } else {
        setProfileError(true)
      }
      if (inboxResult.status === 'fulfilled' && Array.isArray(inboxResult.value?.artifacts)) {
        setArtifacts(inboxResult.value.artifacts.filter((a: Artifact) => a?.clerk_id === subject))
      } else {
        setInboxError(true)
      }
      setLoading(false)
    })
    return () => controller.abort()
  }, [subject, isLoaded, reload])

  const act = async (id: number, kind: 'approve' | 'discard') => {
    if (!subject || pendingId !== null) return
    const actionOwner = subject
    setPendingId(id)
    setActionError('')
    try {
      const res = await apiFetch(`${BACKEND_URL}/api/artifacts/${id}/${kind}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ performed_by: subject }),
      })
      if (!res.ok) throw new Error(`Action failed: ${res.status}`)
      const result = await res.json()
      if (!result.ok || result.state !== (kind === 'approve' ? 'approved' : 'rejected')) {
        throw new Error('Action outcome was not confirmed')
      }
      if (activeSubject.current === actionOwner) setArtifacts(prev => prev.filter(a => a.id !== id))
    } catch {
      if (activeSubject.current === actionOwner) {
        setActionError('We could not confirm that action. Open the item to check its status before trying again.')
      }
    } finally {
      if (activeSubject.current === actionOwner) setPendingId(null)
    }
  }

  if (isLoaded && !subject) return <p className="p-6 text-gray-300">Sign in to see your athlete workspace.</p>
  const busy = !isLoaded || loading || ownerId !== subject

  return (
    <div className="mx-auto max-w-4xl px-4 py-8 text-white sm:px-8 space-y-7">
      <header>
        <p className="text-xs font-bold uppercase tracking-[0.2em] text-sparq-lime">Your SPARQ workspace</p>
        <h1 className="mt-2 text-3xl sm:text-4xl font-black tracking-tight">Your next move.</h1>
        <p className="mt-3 max-w-xl text-gray-400">Continue your combine, keep your evidence together, and build your next step.</p>
      </header>
      {/* Combine context loads independently of profile bootstrap and saved AI work. */}
      <CurrentCombineCard />
      {busy ? (
        <div role="status" className="rounded-2xl border border-white/10 bg-white/[0.04] p-6">
          <p className="text-gray-300">Loading your performance evidence and saved work…</p>
        </div>
      ) : (
        <>
          {profileError ? (
            <section role="alert" className="rounded-2xl border border-amber-400/30 bg-amber-400/5 p-6">
              <h2 className="font-bold">Your profile could not be loaded</h2>
              <p className="mt-2 text-sm text-gray-300">Try again to see your results and next step.</p>
              <button type="button" onClick={() => setReload(n => n + 1)} className="mt-3 text-sm font-bold text-sparq-lime underline">Try again</button>
            </section>
          ) : profile ? <AthleteStartingPoint profile={profile} /> : null}
          <section aria-labelledby="saved-work-title" className="space-y-3">
            <div className="flex items-center justify-between gap-3">
              <h2 id="saved-work-title" className="text-lg font-bold">Work to review</h2>
              <Link href="/home/profile" className="text-sm text-sparq-lime hover:underline">Your profile →</Link>
            </div>
            {actionError && <p role="alert" className="text-sm text-amber-300">{actionError}</p>}
            {inboxError ? (
              <div role="alert" className="rounded-2xl border border-white/10 p-5 text-sm text-gray-300">
                <p>Your saved work could not be loaded.</p>
                <button type="button" onClick={() => setReload(n => n + 1)} className="mt-2 text-sparq-lime underline">Try again</button>
              </div>
            ) : artifacts.length === 0 ? (
              <div className="rounded-2xl border border-white/10 bg-white/[0.02] p-5">
                <p className="font-semibold text-gray-200">No saved work awaiting review</p>
                <p className="mt-1 text-sm text-gray-400">Your research and drafts will appear here when they are ready for you to review.</p>
              </div>
            ) : artifacts.map(a => (
              <ArtifactCard key={a.id} artifact={a} onApprove={id => act(id, 'approve')} onDiscard={id => act(id, 'discard')} pending={pendingId !== null} />
            ))}
          </section>
        </>
      )}
    </div>
  )
}
