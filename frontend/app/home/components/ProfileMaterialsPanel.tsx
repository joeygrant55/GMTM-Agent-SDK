'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'
import { evidenceDate } from './profileEvidence'
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

export default function ProfileMaterialsPanel({ snapshot, loading, error, selected, onToggle, onRetry }: {
  snapshot: ProfileMaterialsSnapshot | null
  loading: boolean
  error: boolean
  selected: string[]
  onToggle: (item: ProfileMaterialItem, checked: boolean) => void
  onRetry: () => void
}) {
  const [expanded, setExpanded] = useState(false)
  const items = snapshot?.state === 'ready' ? snapshot.items : []
  const results = items.filter(item => item.kind === 'submitted_result').length
  const footage = items.filter(item => item.kind === 'footage').length
  const failed = error || snapshot?.state === 'source_unavailable'
  return <section aria-labelledby="profile-materials-title" className="border-t border-white/10 pt-8">
    <h3 id="profile-materials-title" className="text-lg font-semibold tracking-tight">Your submitted results and footage</h3>
    {loading && <p role="status" className="mt-5 text-sm text-gray-300">Reading your existing submissions and footage…</p>}
    {!loading && failed && <div className="mt-5 rounded-xl border border-white/15 p-4"><p role="alert" className="text-sm leading-relaxed text-gray-300">These materials could not be loaded. Your profile measurements and text are still available.</p><button type="button" onClick={onRetry} className={`${button} mt-4`}>Retry materials</button></div>}
    {!loading && !failed && snapshot?.state === 'unlinked' && <p role="status" className="mt-5 text-sm leading-relaxed text-gray-300">Your connection could not be confirmed for these materials. Refresh your profile to check it again.</p>}
    {!loading && !failed && snapshot?.state === 'ready' && <>
      <p className="mt-5 text-sm leading-relaxed text-gray-300">{items.length ? `${results} submitted ${results === 1 ? 'result' : 'results'} and ${footage} footage ${footage === 1 ? 'record' : 'records'} in this view.` : 'No supported submissions or footage were returned in this view. Other evidence may exist in your GMTM profile.'}</p>
      {items.length > 0 && <>
        <fieldset className="mt-4"><legend className="sr-only">Submitted evidence to include</legend><div className="divide-y divide-white/10">{(expanded ? items : items.slice(0, 3)).map(item => <article key={item.id} className="min-w-0 py-5">
          <div className="flex items-start gap-3">{item.can_include && <input type="checkbox" aria-label={`Include ${item.title} from ${item.source_label}`} checked={selected.includes(item.id)} onChange={event => onToggle(item, event.target.checked)} className="mt-1 h-5 w-5 shrink-0 accent-sparq-lime focus-visible:outline focus-visible:outline-2 focus-visible:outline-sparq-lime" />}<div className="min-w-0 flex-1"><h3 className="break-words text-sm font-semibold text-gray-200">{item.title}</h3>{item.result && <p className="mt-2 break-words text-xl font-semibold tabular-nums">{item.result.value} {item.result.unit}</p>}<p className="mt-2 break-words text-xs leading-relaxed text-gray-400">{item.source_label} · {item.date_label}: {evidenceDate(item.recorded_at)}</p><p className="mt-2 text-xs leading-relaxed text-gray-400">{item.availability === 'processing' ? 'Processing not confirmed in GMTM.' : item.availability === 'unavailable' ? 'Marked unavailable in GMTM.' : item.kind === 'footage' ? 'Playback has not been checked.' : 'Submitted result; measurement verification is unconfirmed.'}{!item.can_include && ' View only; this record will not be included in your text.'}</p>{item.kind === 'footage' && item.source_url && <a href={item.source_url} target="_blank" rel="noopener noreferrer" className="mt-2 inline-flex min-h-11 items-center text-sm text-sparq-lime underline underline-offset-4 focus-visible:outline focus-visible:outline-2 focus-visible:outline-sparq-lime">View footage on GMTM<span className="sr-only">: {item.title} (opens a new tab)</span></a>}</div></div>
        </article>)}</div></fieldset>
        {items.length > 3 && <button type="button" aria-expanded={expanded} onClick={() => setExpanded(value => !value)} className={`${button} mt-3`}>{expanded ? 'Show fewer materials' : `Show all ${items.length} materials`}</button>}
        {results === 0 && <p className="mt-4 text-xs leading-relaxed text-gray-400">No supported numeric submission results were returned; footage alone does not establish measurements.</p>}
        {footage === 0 && <p className="mt-4 text-xs leading-relaxed text-gray-400">No footage records were returned in this view. That does not confirm that your full GMTM profile has no footage.</p>}
      </>}
      <details className="mt-4"><summary className="min-h-11 cursor-pointer py-3 text-xs text-gray-400">About these materials</summary><p className="text-xs leading-relaxed text-gray-400">Submission dates are not measurement dates. A footage record and link do not confirm playback, video quality, review or selection.</p>{snapshot.limitations.length > 0 && <ul className="mt-3 list-disc space-y-2 pl-4 text-xs leading-relaxed text-gray-400">{snapshot.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>}</details>
    </>}
  </section>
}
