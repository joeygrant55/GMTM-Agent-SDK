'use client'

import { useState } from 'react'
import { evidenceDate, ProfileEvidence } from './profileEvidence'
import { isProfileThumbnail, ProfileMaterialItem, ProfileMaterialsSnapshot } from './profileMaterials'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const textAction = `inline-flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 hover:text-white disabled:cursor-wait disabled:opacity-50 ${focus}`

export interface AthleteCareerHomeProps {
  profile: ProfileEvidence
  snapshot: ProfileMaterialsSnapshot | null
  loading: boolean
  error: boolean
  goal: { text: string; destination: string | null; timeframe: string | null } | null
  featuredId: string | null
  saving: boolean
  nextMove: { title: string; detail: string; label: string }
  recent: Array<{ id: string; kind: string; at: string }>
  onNext: () => void
  onEditGoal: () => void
  onFeature: (item: ProfileMaterialItem) => void
  onAsk: () => void
  onBrowse: () => void
  onProgress: () => void
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

// Stored poster only: a preview is never an assertion that playback was checked.
function FilmPreview({ clip, compact = false }: { clip: ProfileMaterialItem; compact?: boolean }) {
  const thumbnail = isProfileThumbnail(clip.thumbnail_url) ? clip.thumbnail_url : null
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>(thumbnail ? 'loading' : 'failed')
  const Title = compact ? 'p' : 'h3'
  return <div className={`relative overflow-hidden rounded-xl border border-white/10 bg-sparq-charcoal-light ${compact ? 'aspect-[2.5/1]' : 'aspect-[2.1/1] sm:aspect-[2.35/1]'}`}>
    {thumbnail && status !== 'failed' && <img
      src={thumbnail} alt={`Thumbnail for ${clip.title}`} crossOrigin="anonymous" referrerPolicy="no-referrer"
      loading={compact ? 'lazy' : 'eager'} decoding="async"
      onLoad={() => setStatus('ready')} onError={() => setStatus('failed')}
      className={`absolute inset-0 h-full w-full object-cover object-top ${status === 'ready' ? '' : 'opacity-0'}`}
    />}
    {status !== 'ready' && <div className="absolute inset-0 flex items-center justify-center px-4 pb-14 text-center">
      <p role="status" className="text-sm text-gray-400">{status === 'loading' ? 'Loading preview…' : 'Preview unavailable'}</p>
    </div>}
    <div className={`absolute inset-x-0 bottom-0 bg-black/65 ${compact ? 'px-3 py-2 sm:px-4' : 'px-4 py-3 sm:px-5 sm:py-4'}`}>
      <Title className={`line-clamp-2 break-words font-semibold leading-snug ${compact ? 'text-sm sm:text-base' : 'text-lg sm:text-xl'}`}>{clip.title}</Title>
      <p className={`mt-0.5 text-gray-300 ${compact ? 'text-xs' : 'text-xs sm:text-sm'}`}>Published: {evidenceDate(clip.recorded_at)}</p>
    </div>
  </div>
}

const activityLabels: Record<string, string> = {
  goal_saved: 'Goal saved', goal_removed: 'Goal removed',
  featured_saved: 'Featured footage chosen', featured_removed: 'Featured footage removed',
  draft_saved: 'Draft saved', draft_removed: 'Draft removed',
}

export default function AthleteCareerHome({ profile, snapshot, loading, error, goal, featuredId, saving, nextMove, recent, onNext, onEditGoal, onFeature, onAsk, onBrowse, onProgress }: AthleteCareerHomeProps) {
  const sourceReady = !loading && !error && snapshot?.state === 'ready'
  const items = sourceReady ? snapshot.items : []
  const clips = items.filter(item => item.kind === 'footage' && item.can_include && item.availability === 'unchecked' && item.source_url).slice(0, 10)
  const featured = featuredId ? clips.find(item => item.id === featuredId) : undefined
  const hero = featured || clips[0]
  const alternates = clips.filter(item => item.id !== hero?.id).slice(0, 2)
  const recorded: DisplayResult[] = profile.state === 'ready' ? profile.evidence.slice(0, 2).map(item => ({ id: `profile-${item.id}`, label: item.label, value: item.value, unit: item.unit, kind: 'Recorded', date: item.recorded_at, source: item.source_label })) : []
  const submitted: DisplayResult[] = items.filter(item => item.kind === 'submitted_result' && item.can_include && item.availability === 'recorded' && item.result).slice(0, 2).map(item => ({ id: `material-${item.id}`, label: item.title, value: item.result!.value, unit: item.result!.unit, kind: 'Submitted', date: item.recorded_at, source: item.source_label }))
  const results = recorded.length && submitted.length ? [recorded[0], submitted[0]] : [...recorded, ...submitted].slice(0, 2)
  const activity = recent.filter(item => Object.prototype.hasOwnProperty.call(activityLabels, item.kind)).slice(0, 3)
  const identity = [profile.athlete?.sport, profile.athlete?.position].filter(Boolean).join(' · ')
  const unavailable = error || snapshot?.state === 'source_unavailable'

  return <div className="pb-10 sm:pb-12">
    <header className="mb-7">
      <h1 className="break-words text-4xl font-semibold leading-[1.05] tracking-[-0.045em] sm:text-5xl">{profile.athlete?.name || 'Your athlete home'}</h1>
      {identity && <p className="mt-2 break-words text-base text-gray-400 sm:text-xl">{identity}</p>}
    </header>

    <section aria-label="Your athlete content" className="grid min-w-0 gap-x-6 gap-y-6 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)] md:gap-y-0 lg:grid-cols-[minmax(0,1.8fr)_minmax(0,1fr)] lg:gap-x-9">
      <div className="min-w-0 md:col-start-1 md:row-start-1">
        <div className="mb-3 flex min-h-8 items-center justify-between gap-3">
          <h2 className="text-xl font-semibold tracking-tight sm:text-2xl">{featured ? 'Your featured work' : 'Your footage'}</h2>
        </div>
        {hero ? <>
          <figure className="relative">
            <FilmPreview key={`${hero.id}:${hero.thumbnail_url || ''}`} clip={hero} />
            {featured && <span className="absolute left-4 top-3 rounded-full bg-sparq-lime px-3 py-1 text-xs font-semibold text-sparq-charcoal">Featured</span>}
            <figcaption className="sr-only">{hero.title}. A stored image preview; playback has not been checked.</figcaption>
          </figure>
          <div className="flex flex-wrap items-center justify-between gap-x-4">
            <a href={hero.source_url!} target="_blank" rel="noopener noreferrer" className={textAction}>Open on GMTM</a>
            {!featured && <button type="button" disabled={saving} onClick={() => onFeature(hero)} className={textAction}>Feature this footage</button>}
          </div>
        </> : <div className="flex min-h-48 items-center rounded-xl border border-white/10 bg-sparq-charcoal-light p-6 sm:min-h-64">
          {loading ? <p role="status" className="text-sm text-gray-400">Loading your footage…</p>
            : unavailable ? <div role="alert"><p className="font-medium">Your footage could not be loaded.</p><p className="mt-2 text-sm text-gray-400">Your profile details are still available.</p></div>
              : snapshot?.state === 'unlinked' ? <div role="status"><p className="font-medium">Your footage connection needs review.</p><p className="mt-2 text-sm text-gray-400">Open your portfolio to check it.</p></div>
                : <div><p className="font-medium">No shareable footage in this view.</p><p className="mt-2 text-sm text-gray-400">Your existing profile can still support your next move.</p></div>}
        </div>}

      </div>

      <aside aria-label="Your goal and next move" className="min-w-0 border-t border-white/15 pt-4 md:col-start-2 md:row-span-2 md:row-start-1 md:border-l md:border-t-0 md:pl-6 md:pt-0 lg:pl-9">
        <section aria-labelledby="career-goal-title" className="border-b border-white/15 pb-4 sm:pb-6">
          <div className="flex items-center justify-between gap-3">
            <h2 id="career-goal-title" className="text-[11px] font-medium uppercase tracking-[0.16em] text-gray-300">Current goal</h2>
            <button type="button" onClick={onEditGoal} disabled={saving} className={textAction}>{goal ? 'Edit goal' : 'Set a goal'}</button>
          </div>
          <p className="mt-2 break-words text-xl leading-snug tracking-tight sm:text-2xl">{goal?.text || 'What do you want to do next?'}</p>
          {goal?.destination && <p className="mt-3 break-words text-sm text-gray-400">For: {goal.destination}</p>}
          {goal?.timeframe && <p className="mt-1 break-words text-sm text-gray-400">When: {goal.timeframe}</p>}
        </section>
        <section aria-labelledby="career-next-title" className="pt-5 sm:pt-9">
          <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-gray-300">Your next move</p>
          <h2 id="career-next-title" className="mt-3 break-words text-3xl font-semibold leading-[1.08] tracking-[-0.04em] sm:mt-4 xl:text-[2.6rem]">{nextMove.title}</h2>
          <p className="mt-2 break-words text-base leading-relaxed text-gray-400 sm:mt-3 xl:text-lg">{nextMove.detail}</p>
          <button type="button" onClick={onNext} disabled={saving} className={`mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-sparq-lime px-6 py-3 text-base font-semibold text-sparq-charcoal hover:bg-sparq-lime-light disabled:cursor-wait disabled:opacity-50 sm:mt-6 sm:min-h-14 sm:w-auto sm:px-8 sm:text-lg ${focus}`}>{nextMove.label}</button>
          <div className="mt-4"><button type="button" onClick={onAsk} className={textAction}>Ask SPARQ</button></div>
        </section>
      </aside>

      <div className="min-w-0 md:col-start-1 md:row-start-2">
        {alternates.length > 0 && <div className="mt-1 grid grid-cols-2 gap-3 sm:gap-4" aria-label="Choose featured footage">
          {alternates.map(clip => <button key={clip.id} type="button" aria-label={`Feature ${clip.title}`} disabled={saving} onClick={() => onFeature(clip)} className={`min-w-0 rounded-xl text-left disabled:cursor-wait disabled:opacity-50 ${focus}`}>
            <FilmPreview key={`${clip.id}:${clip.thumbnail_url || ''}`} clip={clip} compact />
          </button>)}
        </div>}
        {alternates.length > 0 && <p className="mt-3 text-xs text-gray-500">Choose footage to feature on your private home.</p>}
        {results.length > 0 && <section aria-label="Recorded and submitted results" className="mt-5 border-t border-white/15 pt-4">
          <h2 className="text-lg font-semibold tracking-tight">Your results</h2>
          <div className="mt-3 grid grid-cols-2 gap-4 sm:gap-6">
            {results.map((item, index) => <article key={item.id} className={`min-w-0 ${index ? 'border-l border-white/15 pl-4 sm:pl-6' : ''}`}>
              <p className="text-[10px] font-medium uppercase tracking-[0.16em] text-gray-400">{item.kind}</p>
              <h3 className="mt-1 break-words text-sm leading-snug text-gray-200">{item.label}</h3>
              <p className="mt-1 break-words text-2xl font-semibold tracking-tight tabular-nums sm:text-3xl">{item.value}<span className="ml-1.5 text-base font-normal text-gray-300">{item.unit}</span></p>
              <p className="mt-1 text-xs text-gray-400">{evidenceDate(item.date)}</p>
              <span className="sr-only">Source: {item.source}. Measurement verification is unconfirmed.</span>
            </article>)}
          </div>
          <p className="mt-3 text-xs text-gray-500">Results are unverified.</p>
        </section>}
        <button type="button" onClick={onBrowse} className={`${textAction} mt-1`}>Browse portfolio</button>
      </div>
    </section>

    <section aria-labelledby="career-recent-title" className="mt-7 border-t border-white/15 pt-4 sm:mt-8">
      <div className="flex flex-col items-start gap-x-8 gap-y-3 sm:flex-row sm:flex-wrap sm:items-center">
        <h2 id="career-recent-title" className="text-base font-semibold">Recent work</h2>
        {activity.length ? <ul className="flex flex-1 flex-wrap gap-x-7 gap-y-3">{activity.map(item => <li key={item.id} className="min-w-0 border-l border-white/15 pl-4"><p className="text-sm text-gray-200">{activityLabels[item.kind]}</p><time dateTime={item.at} className="mt-1 block text-xs text-gray-500">{evidenceDate(item.at)}</time></li>)}</ul>
          : <p className="flex-1 text-sm text-gray-500">Your saved work will appear here.</p>}
        <button type="button" onClick={onProgress} className={textAction}>View progress</button>
      </div>
    </section>
  </div>
}
