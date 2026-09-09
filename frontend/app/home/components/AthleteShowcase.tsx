'use client'

import { useState } from 'react'
import { evidenceDate, ProfileEvidence } from './profileEvidence'
import { ProfileMaterialItem, ProfileMaterialsSnapshot } from './profileMaterials'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-white/15 px-4 py-2 text-sm text-gray-300 hover:border-white/35 disabled:cursor-not-allowed disabled:opacity-30 motion-safe:transition-colors motion-reduce:transition-none ${focus}`

interface Props {
  profile: ProfileEvidence
  snapshot: ProfileMaterialsSnapshot | null
  loading: boolean
  error: boolean
  onUseClip: (item: ProfileMaterialItem) => void
  onBrowse: () => void
}

interface DisplayResult {
  id: string
  label: string
  value: number
  unit: string
  kind: 'Recorded' | 'Submitted'
  date: string | null
  source: string
}

function FootagePoster({ clip }: { clip: ProfileMaterialItem }) {
  const thumbnail = clip.thumbnail_url || null
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>(thumbnail ? 'loading' : 'failed')
  return <div className="relative aspect-video overflow-hidden rounded-2xl border border-white/10 bg-white/[0.035]">
    {thumbnail && status !== 'failed' && <img src={thumbnail} alt={`Thumbnail for ${clip.title}`} crossOrigin="anonymous" referrerPolicy="no-referrer" decoding="async" loading="eager" onLoad={() => setStatus('ready')} onError={() => setStatus('failed')} className={`absolute inset-0 h-full w-full object-contain ${status === 'ready' ? '' : 'opacity-0'}`} />}
    {status !== 'ready' && <div className="absolute inset-0 flex items-center justify-center px-6 text-center"><p role="status" className="text-sm text-gray-400">{status === 'loading' ? 'Loading preview…' : 'Preview unavailable'}</p></div>}
  </div>
}

export default function AthleteShowcase({ profile, snapshot, loading, error, onUseClip, onBrowse }: Props) {
  const [chosenId, setChosenId] = useState<string | null>(null)
  const sourceReady = !loading && !error && snapshot?.state === 'ready'
  const items = sourceReady ? snapshot.items : []
  const clips = items.filter(item => item.kind === 'footage' && item.can_include && item.availability === 'unchecked' && item.source_url).slice(0, 10)
  const clip = clips.find(item => item.id === chosenId) || clips[0]
  const clipIndex = clip ? clips.findIndex(item => item.id === clip.id) : -1
  const recorded: DisplayResult[] = profile.state === 'ready' ? profile.evidence.slice(0, 2).map(item => ({ id: `profile-${item.id}`, label: item.label, value: item.value, unit: item.unit, kind: 'Recorded', date: item.recorded_at, source: item.source_label })) : []
  const submitted: DisplayResult[] = items.filter(item => item.kind === 'submitted_result' && item.can_include && item.availability === 'recorded' && item.result).slice(0, 2).map(item => ({ id: `material-${item.id}`, label: item.title, value: item.result!.value, unit: item.result!.unit, kind: 'Submitted', date: item.recorded_at, source: item.source_label }))
  // Preserve both source classes when present; source order is not a performance ranking.
  const results = recorded.length && submitted.length ? [recorded[0], submitted[0]] : [...recorded, ...submitted].slice(0, 2)
  const unavailable = error || snapshot?.state === 'source_unavailable'

  return <section aria-label="Your athlete content" className="min-w-0">
    <header className="mb-6 sm:mb-8">
      <h2 className="text-3xl font-semibold tracking-[-0.04em] sm:text-4xl">Your work. Your next move.</h2>
      <p className="mt-2 text-sm text-gray-400">From your GMTM profile.</p>
    </header>

    <div className={`grid min-w-0 gap-5 ${results.length ? 'lg:grid-cols-[minmax(0,2.3fr)_minmax(0,1fr)] lg:gap-8' : ''}`}>
      <div className="min-w-0">
        {clip ? <figure>
          <FootagePoster key={`${clip.id}:${clip.thumbnail_url || ''}`} clip={clip} />
          <figcaption className="mt-3 flex items-start justify-between gap-4">
            <div className="min-w-0"><h3 title={clip.title} className="line-clamp-2 break-words text-lg font-semibold leading-snug">{clip.title}</h3><p className="mt-1 text-xs leading-relaxed text-gray-400">Published: {evidenceDate(clip.recorded_at)}</p></div>
            {clips.length > 1 && <span aria-label={`Clip ${clipIndex + 1} of ${clips.length} in this view`} className="shrink-0 pt-1 text-xs tabular-nums text-gray-400">{clipIndex + 1} / {clips.length}</span>}
          </figcaption>
          {clips.length > 1 && <div className="mt-3 flex gap-2" aria-label="Browse your clips">
            <button type="button" aria-label="Previous clip" disabled={clipIndex === 0} onClick={() => setChosenId(clips[clipIndex - 1].id)} className={secondary}><span aria-hidden="true" className="mr-2">←</span>Previous</button>
            <button type="button" aria-label="Next clip" disabled={clipIndex >= clips.length - 1} onClick={() => setChosenId(clips[clipIndex + 1].id)} className={secondary}>Next<span aria-hidden="true" className="ml-2">→</span></button>
          </div>}
        </figure> : <div className="flex min-h-44 items-center rounded-2xl border border-white/10 bg-white/[0.025] px-6 py-7 sm:min-h-52">
          {loading ? <p role="status" className="text-sm text-gray-300">Loading your footage…</p>
            : unavailable ? <div role="alert"><p className="text-base font-medium">Your footage could not be loaded.</p><p className="mt-2 text-sm leading-relaxed text-gray-400">Your profile details are still available.</p></div>
              : snapshot?.state === 'unlinked' ? <div role="status"><p className="text-base font-medium">Your footage connection needs review.</p><p className="mt-2 text-sm leading-relaxed text-gray-400">Open your profile details to check it.</p></div>
                : <div><p className="text-base font-medium">No shareable footage in this view.</p><p className="mt-2 text-sm leading-relaxed text-gray-400">You can still build an introduction from your profile.</p></div>}
        </div>}
    {clip && <div className="mt-5 flex flex-wrap items-center gap-x-5 gap-y-2">
      <button type="button" onClick={() => onUseClip(clip)} className={`inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-sparq-lime px-5 py-3 text-sm font-bold text-sparq-charcoal hover:bg-sparq-lime-light motion-safe:transition-colors motion-reduce:transition-none sm:w-auto ${focus}`}>Use this in an introduction</button>
      <a href={clip.source_url!} target="_blank" rel="noopener noreferrer" className={`inline-flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 ${focus}`}>View on GMTM</a>
    </div>}
      </div>

      {results.length > 0 && <div className="grid min-w-0 grid-cols-2 gap-4 lg:grid-cols-1 lg:content-start lg:gap-5" aria-label="Recorded and submitted results">
        {results.map(item => <article key={item.id} className="min-w-0 border-t border-white/15 pt-4">
          <p className="text-[11px] font-medium uppercase tracking-[0.12em] text-gray-400">{item.kind}</p>
          <h3 className="mt-2 break-words text-sm font-medium leading-snug text-gray-300">{item.label}</h3>
          <p className="mt-2 break-words text-3xl font-semibold tracking-tight tabular-nums sm:text-4xl">{item.value}<span className="ml-2 text-sm font-normal tracking-normal text-gray-400">{item.unit}</span></p>
          <p className="mt-2 text-xs leading-relaxed text-gray-400">{evidenceDate(item.date)}</p>
          <span className="sr-only">Source: {item.source}. Measurement verification is unconfirmed.</span>
        </article>)}
      </div>}
    </div>

    <div className="mt-4 flex flex-wrap items-center justify-between gap-x-5 gap-y-1">
      {(clip || results.length > 0) && <p className="text-xs leading-relaxed text-gray-400">{clip ? 'Preview only. ' : ''}{results.length ? 'Results are unverified.' : 'Playback has not been checked.'}</p>}
      <button type="button" onClick={onBrowse} className={`inline-flex min-h-11 items-center text-sm text-gray-400 underline underline-offset-4 hover:text-white ${focus}`}>View all profile details</button>
    </div>
  </section>
}
