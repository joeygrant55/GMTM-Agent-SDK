'use client'

import { useCallback, useEffect, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import ArtifactCard from './ArtifactCard'
import { Artifact } from './artifactStatus'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export default function InboxFeed() {
  const { user, isLoaded } = useUser()
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const [artifacts, setArtifacts] = useState<Artifact[]>([])
  const [loading, setLoading] = useState(true)
  const [pendingId, setPendingId] = useState<number | null>(null)
  const [seedTried, setSeedTried] = useState(false)

  const fetchInbox = useCallback(
    async (clerkId: string) => {
      try {
        const res = await fetch(`${backendUrl}/api/workspace/inbox/${clerkId}`)
        const data = await res.json()
        const list = Array.isArray(data?.artifacts) ? (data.artifacts as Artifact[]) : []
        setArtifacts(list)
        return list
      } catch {
        setArtifacts([])
        return []
      }
    },
    [backendUrl]
  )

  useEffect(() => {
    if (!isLoaded || !user?.id) return
    let cancelled = false
    ;(async () => {
      const list = await fetchInbox(user.id)
      // First-time visit with empty inbox? Seed demo artifacts so V2 has something to show.
      if (!cancelled && list.length === 0 && !seedTried) {
        setSeedTried(true)
        try {
          await fetch(`${backendUrl}/api/artifacts/seed-demo/${user.id}`, { method: 'POST' })
          if (!cancelled) await fetchInbox(user.id)
        } catch {
          // If seed fails (DB down), inbox just stays empty — UX shows the empty state.
        }
      }
      if (!cancelled) setLoading(false)
    })()
    return () => {
      cancelled = true
    }
  }, [backendUrl, fetchInbox, isLoaded, user?.id, seedTried])

  const approve = async (id: number) => {
    setPendingId(id)
    try {
      await fetch(`${backendUrl}/api/artifacts/${id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ performed_by: user?.id ?? null }),
      })
      setArtifacts((prev) => prev.filter((a) => a.id !== id))
    } finally {
      setPendingId(null)
    }
  }

  const discard = async (id: number) => {
    setPendingId(id)
    try {
      await fetch(`${backendUrl}/api/artifacts/${id}/discard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ performed_by: user?.id ?? null }),
      })
      setArtifacts((prev) => prev.filter((a) => a.id !== id))
    } finally {
      setPendingId(null)
    }
  }

  const greeting = (() => {
    const h = new Date().getHours()
    if (h < 12) return 'Good morning'
    if (h < 18) return 'Good afternoon'
    return 'Good evening'
  })()

  return (
    <div className="text-white pb-12">
      <div className="p-8 pb-2">
        <h1 className="text-3xl font-black text-white">
          {greeting}{user?.firstName ? `, ${user.firstName}` : ''}
        </h1>
        <p className="text-gray-400 mt-1">
          {loading
            ? 'Loading what your team did overnight…'
            : artifacts.length === 0
            ? 'Your team has no new work for you to review. Check back tomorrow morning.'
            : `${artifacts.length} ${artifacts.length === 1 ? 'thing' : 'things'} from your team`}
        </p>
      </div>

      <div className="px-8 pt-4 space-y-3">
        {loading && (
          <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6 animate-pulse">
            <div className="h-4 bg-white/10 rounded w-1/3 mb-3" />
            <div className="h-3 bg-white/10 rounded w-2/3" />
          </div>
        )}

        {!loading &&
          artifacts.map((a) => (
            <ArtifactCard
              key={a.id}
              artifact={a}
              onApprove={approve}
              onDiscard={discard}
              pending={pendingId === a.id}
            />
          ))}
      </div>
    </div>
  )
}
