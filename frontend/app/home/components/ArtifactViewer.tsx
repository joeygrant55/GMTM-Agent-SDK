'use client'

import { apiFetch } from '@/app/_lib/api'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'
import { useUser } from '@clerk/nextjs'
import { ARTIFACT_TYPE_LABEL, Artifact } from './artifactStatus'
import SpecialistAvatar from './SpecialistAvatar'
import ArtifactStatusPill from './ArtifactStatusPill'
import OutreachDraftView from './OutreachDraftView'
import ResearchBriefView from './ResearchBriefView'
import HonestAssessmentView from './HonestAssessmentView'
import GenericArtifactView from './GenericArtifactView'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

export default function ArtifactViewer({ artifactId }: { artifactId: number }) {
  const { user } = useUser()
  const router = useRouter()
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const [artifact, setArtifact] = useState<Artifact | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [savingState, setSavingState] = useState<'idle' | 'saving' | 'saved'>('idle')
  const [pending, setPending] = useState<null | 'approve' | 'discard'>(null)
  const [resultNotice, setResultNotice] = useState<{ kind: 'queued' | 'send_failed'; message: string } | null>(null)

  const editedPayloadRef = useRef<Record<string, unknown> | null>(null)
  const dirtyRef = useRef(false)
  const saveTimer = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    let cancelled = false
    setLoading(true)
    apiFetch(`${backendUrl}/api/artifacts/${artifactId}`)
      .then(async (res) => {
        if (!res.ok) throw new Error(`Artifact ${artifactId} not found`)
        return res.json()
      })
      .then((data: Artifact) => {
        if (cancelled) return
        setArtifact(data)
        editedPayloadRef.current = (data.payload || {}) as Record<string, unknown>
        dirtyRef.current = false
        setLoading(false)
      })
      .catch((err: Error) => {
        if (!cancelled) {
          setError(err.message)
          setLoading(false)
        }
      })
    return () => {
      cancelled = true
    }
  }, [artifactId, backendUrl])

  // Tell the right rail to scope itself to this artifact.
  useEffect(() => {
    if (!artifact) return
    window.dispatchEvent(
      new CustomEvent('sparq:artifact-opened', {
        detail: { artifactId: artifact.id, type: artifact.type, title: artifact.title, agent_id: artifact.agent_id },
      })
    )
    return () => {
      window.dispatchEvent(new CustomEvent('sparq:artifact-closed'))
    }
  }, [artifact])

  // When chat-driven iteration completes, re-fetch.
  useEffect(() => {
    const handler = (e: Event) => {
      const detail = (e as CustomEvent<{ artifactId: number; childId?: number }>).detail
      if (!detail) return
      if (detail.childId) {
        router.push(`/home/artifact/${detail.childId}`)
      } else if (detail.artifactId === artifactId) {
        // refresh in place
        apiFetch(`${backendUrl}/api/artifacts/${artifactId}`)
          .then((r) => r.json())
          .then((data: Artifact) => setArtifact(data))
          .catch(() => {})
      }
    }
    window.addEventListener('sparq:artifact-updated', handler)
    return () => window.removeEventListener('sparq:artifact-updated', handler)
  }, [artifactId, backendUrl, router])

  const persistPayload = useCallback(async () => {
    if (!artifact || !editedPayloadRef.current || !dirtyRef.current) return
    setSavingState('saving')
    try {
      await apiFetch(`${backendUrl}/api/artifacts/${artifact.id}/edit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          payload: editedPayloadRef.current,
          performed_by: user?.id ?? null,
        }),
      })
      dirtyRef.current = false
      setSavingState('saved')
      setTimeout(() => setSavingState('idle'), 1200)
    } catch {
      setSavingState('idle')
    }
  }, [artifact, backendUrl, user?.id])

  const onPayloadChange = useCallback(
    (next: Record<string, unknown>) => {
      editedPayloadRef.current = next
      dirtyRef.current = true
      if (saveTimer.current) clearTimeout(saveTimer.current)
      saveTimer.current = setTimeout(() => void persistPayload(), 800)
    },
    [persistPayload]
  )

  const approve = async () => {
    if (!artifact) return
    setPending('approve')
    setResultNotice(null)
    await persistPayload()
    try {
      const athleteEmail = user?.primaryEmailAddress?.emailAddress ?? null
      const athleteName = user?.fullName ?? user?.firstName ?? null
      const res = await apiFetch(`${backendUrl}/api/artifacts/${artifact.id}/approve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          performed_by: user?.id ?? null,
          athlete_email: athleteEmail,
          athlete_name: athleteName,
        }),
      })
      const data = await res.json().catch(() => ({}))
      if (data?.state) {
        setArtifact({ ...artifact, state: data.state })
      }
      if (data?.state === 'queued') {
        setResultNotice({
          kind: 'queued',
          message: 'Approved and logged in your outreach log. Send infrastructure is not configured yet — copy & send manually for now.',
        })
        return // don't redirect — let the athlete see the notice
      }
      if (data?.state === 'send_failed') {
        setResultNotice({
          kind: 'send_failed',
          message: `Send failed: ${data?.detail?.reason ?? 'unknown error'}. The draft is still here — retry, or copy & send manually.`,
        })
        return
      }
      router.push('/home/inbox')
    } finally {
      setPending(null)
    }
  }

  const discard = async () => {
    if (!artifact) return
    setPending('discard')
    try {
      await apiFetch(`${backendUrl}/api/artifacts/${artifact.id}/discard`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ performed_by: user?.id ?? null }),
      })
      router.push('/home/inbox')
    } finally {
      setPending(null)
    }
  }

  const typeLabel = useMemo(
    () => (artifact ? ARTIFACT_TYPE_LABEL[artifact.type] ?? 'Artifact' : 'Artifact'),
    [artifact]
  )

  if (loading) {
    return (
      <div className="p-8 text-gray-400">
        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6 animate-pulse h-48" />
      </div>
    )
  }
  if (error || !artifact) {
    return (
      <div className="p-8">
        <button onClick={() => router.push('/home/inbox')} className="text-sparq-lime text-sm">
          ← Inbox
        </button>
        <div className="mt-6 bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-red-300 text-sm">
          {error || 'Artifact unavailable.'}
        </div>
      </div>
    )
  }

  const approveLabel =
    artifact.type === 'outreach_draft' ? (pending === 'approve' ? 'Sending…' : 'Approve & Send') : 'Approve'

  return (
    <div className="p-8 pb-12 text-white">
      <button
        onClick={() => router.push('/home/inbox')}
        className="text-xs text-gray-400 hover:text-sparq-lime transition-colors mb-4"
      >
        ← Inbox
      </button>

      <div className="flex items-start justify-between gap-4 mb-2">
        <div className="min-w-0">
          <div className="text-xs uppercase tracking-wide text-gray-500 mb-1">{typeLabel}</div>
          <h1 className="text-2xl font-black text-white truncate">{artifact.title}</h1>
          {artifact.summary && <p className="text-gray-400 mt-1">{artifact.summary}</p>}
        </div>
        <ArtifactStatusPill artifact={artifact} />
      </div>

      <div className="flex items-center gap-3 text-xs text-gray-500 mb-6">
        <SpecialistAvatar agentId={artifact.agent_id} />
        {artifact.updated_at && (
          <>
            <span>·</span>
            <span>updated {new Date(artifact.updated_at).toLocaleString()}</span>
          </>
        )}
        {savingState !== 'idle' && (
          <>
            <span>·</span>
            <span className={savingState === 'saving' ? 'text-gray-400' : 'text-sparq-lime'}>
              {savingState === 'saving' ? 'saving…' : 'saved'}
            </span>
          </>
        )}
      </div>

      {artifact.type === 'outreach_draft' ? (
        <OutreachDraftView artifact={artifact} onPayloadChange={onPayloadChange} />
      ) : artifact.type === 'research_brief' ? (
        <ResearchBriefView artifact={artifact} onPayloadChange={onPayloadChange} />
      ) : artifact.type === 'honest_assessment' ? (
        <HonestAssessmentView artifact={artifact} onPayloadChange={onPayloadChange} />
      ) : (
        <GenericArtifactView artifact={artifact} />
      )}

      {artifact.sources?.length > 0 && (
        <div className="mt-6 bg-white/[0.02] border border-white/5 rounded-xl p-4">
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-2">Sources</div>
          <ul className="space-y-1">
            {artifact.sources.map((s, i) => (
              <li key={i} className="text-xs text-gray-300">
                {s.url ? (
                  <a href={s.url} target="_blank" rel="noopener noreferrer" className="text-sparq-lime hover:underline">
                    {s.label}
                  </a>
                ) : (
                  s.label
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      {resultNotice && (
        <div
          className={`mt-6 rounded-xl px-4 py-3 text-sm ${
            resultNotice.kind === 'queued'
              ? 'bg-amber-500/10 border border-amber-500/30 text-amber-200'
              : 'bg-red-500/10 border border-red-500/30 text-red-300'
          }`}
        >
          {resultNotice.message}
        </div>
      )}

      <div className="mt-6 flex items-center gap-3">
        <button
          onClick={approve}
          disabled={pending !== null}
          className="bg-sparq-lime text-sparq-charcoal font-bold px-4 py-2 rounded-lg text-sm hover:bg-sparq-lime-light disabled:opacity-40"
        >
          {approveLabel}
        </button>
        <button
          onClick={discard}
          disabled={pending !== null}
          className="text-sm text-gray-400 hover:text-red-300 px-3 py-2 disabled:opacity-40"
        >
          Discard
        </button>
        <span className="ml-auto text-[11px] text-gray-500">
          Use the chat panel to iterate this draft.
        </span>
      </div>
    </div>
  )
}
