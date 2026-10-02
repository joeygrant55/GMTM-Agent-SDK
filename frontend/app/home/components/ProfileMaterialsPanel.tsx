'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'
import { evidenceDate, isBodySize } from './profileEvidence'
import { ProfileMaterialItem, ProfileMaterialsSnapshot, readProfileMaterials } from './profileMaterials'

const button = 'inline-flex min-h-11 items-center rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'

export function useProfileMaterials() {
  const [snapshot, setSnapshot] = useState<ProfileMaterialsSnapshot | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(false)
  const [scopeInvalid, setScopeInvalid] = useState(false)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const reload = useCallback(async () => {
    if (!mounted.current || active.current) return
    const controller = new AbortController()
    active.current = controller
    setLoading(true); setError(false); setScopeInvalid(false); setSnapshot(null)
    const timer = window.setTimeout(() => {
      controller.abort()
      if (mounted.current && active.current === controller) {
        active.current = null; setLoading(false); setError(true); setSnapshot(null)
      }
    }, 30000)
    controller.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const response = await apiFetch('/api/athlete/materials', { signal: controller.signal, cache: 'no-store' })
      if (!mounted.current || controller.signal.aborted) return
      if (!response.ok) {
        if ([401, 403, 409].includes(response.status)) setScopeInvalid(true)
        throw new Error('Materials unavailable')
      }
      const data = readProfileMaterials(await response.json())
      if (!mounted.current || controller.signal.aborted) return
      setSnapshot(data)
    } catch {
      if (mounted.current && active.current === controller && !controller.signal.aborted) setError(true)
    } finally {
      window.clearTimeout(timer)
      if (active.current === controller) { active.current = null; if (mounted.current) setLoading(false) }
    }
  }, [])
  useEffect(() => {
    mounted.current = true; void reload()
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [reload])
  return { snapshot, loading, error, scopeInvalid, reload }
}

export default function ProfileMaterialsPanel({ snapshot, loading, error, onRetry }: {
  snapshot: ProfileMaterialsSnapshot | null
  loading: boolean
  error: boolean
  onRetry: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const items = snapshot?.state === 'ready' ? snapshot.items.filter(item => item.kind !== 'submitted_result' || !isBodySize(item.title)) : []
  const failed = error || snapshot?.state === 'source_unavailable'
  const note = (item: ProfileMaterialItem) => item.availability === 'processing' ? 'Still processing on GMTM.'
    : item.availability === 'unavailable' ? 'Not available on GMTM right now.'
      : item.kind === 'submitted_result' ? 'Self-recorded.' : ''
  return <section aria-labelledby="profile-materials-title" className="border-t border-white/10 pt-8">
    <h3 id="profile-materials-title" className="text-lg font-semibold tracking-tight">Your results and videos</h3>
    {loading && <p role="status" className="mt-5 text-sm text-gray-300">Loading your results and videos…</p>}
    {!loading && failed && <div className="mt-5 rounded-xl border border-white/15 p-4"><p role="alert" className="text-sm leading-relaxed text-gray-300">We could not load these right now.</p><button type="button" onClick={onRetry} className={`${button} mt-4`}>Try again</button></div>}
    {!loading && !failed && snapshot?.state === 'unlinked' && <p role="status" className="mt-5 text-sm leading-relaxed text-gray-300">We could not connect to your GMTM profile. Tap Refresh profile to try again.</p>}
    {!loading && !failed && snapshot?.state === 'ready' && <>
      {!items.length && <p className="mt-5 text-sm leading-relaxed text-gray-300">Nothing here yet. Results and videos you add on GMTM will show here.</p>}
      {items.length > 0 && <>
        <ul className="mt-4 divide-y divide-white/10">{(expanded ? items : items.slice(0, 3)).map(item => <li key={item.id} className="min-w-0 py-5">
          <h4 className="break-words text-sm font-semibold text-gray-200">{item.title}</h4>
          {item.result && <p className="mt-2 break-words text-xl font-semibold tabular-nums">{item.result.value} {item.result.unit}</p>}
          <p className="mt-2 break-words text-xs leading-relaxed text-gray-400">{item.date_label === 'Published' ? 'Added' : 'Sent'} {evidenceDate(item.recorded_at)}{note(item) ? ` · ${note(item)}` : ''}</p>
          {item.kind === 'footage' && item.source_url && <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex min-h-11 items-center text-sm text-sparq-lime underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sparq-lime">Watch on GMTM<span className="sr-only">: {item.title} (opens a new tab)</span></a>}
        </li>)}</ul>
        {items.length > 3 && <button type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)} className={`${button} mt-3`}>{expanded ? 'Show less' : `Show all ${items.length}`}</button>}
      </>}
    </>}
  </section>
}
