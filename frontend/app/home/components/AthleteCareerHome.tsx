'use client'

// Journey Home (2026-10-02 design): greeting, steps left to the first coach email, one
// primary action for the current step, a 4-step tracker from real data, featured clip,
// drill tiles and saved colleges with their email status.
import { useState } from 'react'
import Link from 'next/link'
import { drillKey, evidenceDate, isBodySize, ProfileEvidence } from './profileEvidence'
import { isProfileThumbnail, ProfileMaterialItem, ProfileMaterialsSnapshot } from './profileMaterials'
import { aboutMiles, Badge, primary, SavedColleges, shortDate } from './ProfileColleges'
import { journey, JourneyStep } from './journey'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-jr-lime'
const outline = `inline-flex min-h-12 items-center justify-center rounded-[14px] border border-jr-edge px-6 py-3 text-base font-semibold text-jr-text hover:border-jr-muted ${focus}`

export interface DisplayResult { id: string; label: string; value: number; unit: string; kind: 'On your profile' | 'Self-recorded'; date: string | null }

const UNITS: Record<string, string> = { seconds: 's', inches: 'in', feet: 'ft', repetitions: 'reps', centimeters: 'cm', cm: 'cm', lb: 'lb', kg: 'kg' }
// GMTM stores formatted times in milliseconds; show seconds.
function display(value: number, unit: string): { value: number; unit: string } {
  if (unit === 'milliseconds') return { value: Math.round(value / 10) / 100, unit: 's' }
  return { value, unit: UNITS[unit] ?? unit }
}

// USA Football junior combine drills lead; any other drill follows, newest first.
const PREFERRED = [/^20yard(dash)?$/, /^5105shuttle$/, /^(standing)?broadjump$/]
const preference = (label: string) => { const index = PREFERRED.findIndex(pattern => pattern.test(drillKey(label))); return index < 0 ? PREFERRED.length : index }

export function drillResults(profile: ProfileEvidence, snapshot: ProfileMaterialsSnapshot | null): DisplayResult[] {
  const items = snapshot?.state === 'ready' ? snapshot.items : []
  const recorded: DisplayResult[] = profile.state === 'ready' ? profile.evidence.map(item => ({ id: `profile-${item.id}`, label: item.label, ...display(item.value, item.unit), kind: 'On your profile', date: item.recorded_at })) : []
  const submitted: DisplayResult[] = items.filter(item => item.kind === 'submitted_result' && item.can_include && item.availability === 'recorded' && item.result)
    .map(item => ({ id: `material-${item.id}`, label: item.title, ...display(item.result!.value, item.result!.unit), kind: 'Self-recorded', date: item.recorded_at }))
  // Newest result for each drill, without height or weight.
  const seen = new Set<string>()
  return [...recorded, ...submitted]
    .filter(item => !isBodySize(item.label))
    .sort((a, b) => preference(a.label) - preference(b.label) || (b.date || '').localeCompare(a.date || ''))
    .filter(item => { const key = drillKey(item.label); if (seen.has(key)) return false; seen.add(key); return true })
}

export function playableClips(snapshot: ProfileMaterialsSnapshot | null): ProfileMaterialItem[] {
  return (snapshot?.state === 'ready' ? snapshot.items : []).filter(item => item.kind === 'footage' && item.can_include && item.availability === 'unchecked' && item.source_url).slice(0, 10)
}

// Her chosen clip first, then her Highlight Reel task video, then the newest clip.
export function featuredClip(clips: ProfileMaterialItem[], featuredId: string | null): ProfileMaterialItem | undefined {
  return clips.find(item => item.id === featuredId) || clips.find(item => /highlight reel/i.test(`${item.source_label} ${item.title}`)) || clips[0]
}

// Stored poster only: a preview is never an assertion that playback was checked.
export function Poster({ clip }: { clip: ProfileMaterialItem }) {
  const thumbnail = isProfileThumbnail(clip.thumbnail_url) ? clip.thumbnail_url : null
  const [status, setStatus] = useState<'loading' | 'ready' | 'failed'>(thumbnail ? 'loading' : 'failed')
  return <>
    <div aria-hidden="true" className="absolute inset-0 bg-[repeating-linear-gradient(135deg,#1A1A1F_0,#1A1A1F_14px,#1E1E24_14px,#1E1E24_28px)]" />
    {thumbnail && status !== 'failed' && <img src={thumbnail} alt={`Thumbnail for ${clip.title}`} crossOrigin="anonymous" referrerPolicy="no-referrer" decoding="async"
      onLoad={() => setStatus('ready')} onError={() => setStatus('failed')}
      className={`absolute inset-0 h-full w-full object-cover object-top ${status === 'ready' ? '' : 'opacity-0'}`} />}
    {status === 'failed' && <span className="sr-only">Preview unavailable</span>}
  </>
}

function StepCard({ step, index, current }: { step: JourneyStep; index: number; current: boolean }) {
  const check = <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#0B0B0C" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true"><path d="M5 12l5 5L20 7" /></svg>
  const body = <>
    <span className={`flex h-[34px] w-[34px] items-center justify-center rounded-full font-bold ${step.done ? 'bg-jr-lime' : current ? 'border-2 border-jr-lime text-jr-lime' : 'border-2 border-[#4A4A52] text-[#8E8E96]'}`}>
      {step.done ? check : index + 1}
    </span>
    <span className={`text-lg font-semibold ${!step.done && !current ? 'text-[#D4D4DA]' : ''}`}>{step.title}</span>
    <span className={`text-sm ${current ? 'font-semibold text-jr-lime' : step.done ? 'text-jr-soft' : 'text-jr-dim'}`}>{current ? 'Do this next →' : step.detail}</span>
    <span className="sr-only">{step.done ? '(done)' : current ? '(current step)' : '(not started)'}</span>
  </>
  const box = `flex flex-col gap-2.5 rounded-[18px] p-4 sm:p-5 ${step.done ? 'border border-jr-done-line bg-jr-done' : current ? 'border-2 border-jr-lime bg-jr-raised' : 'border border-dashed border-jr-edge bg-jr-well'}`
  return current && step.key !== 'profile' ? <Link href="/home/colleges" className={`${box} ${focus}`}>{body}</Link> : <div className={box}>{body}</div>
}

export default function AthleteCareerHome({ profile, snapshot, loading, error, featuredId, colleges, collegesError }: {
  profile: ProfileEvidence; snapshot: ProfileMaterialsSnapshot | null; loading: boolean; error: boolean; featuredId: string | null
  colleges: SavedColleges | null; collegesError: string
}) {
  const athlete = profile.athlete
  const clips = playableClips(snapshot)
  const hero = featuredClip(clips, featuredId)
  const results = drillResults(profile, snapshot)
  const first = athlete?.name?.trim().split(/\s+/)[0] || null
  const place = [athlete?.city, athlete?.state].filter(Boolean).join(', ')
  // Grad year is already limited to a plausible 13-17 year (backend filter); otherwise omitted.
  const line = [athlete?.graduation_year ? `Class of ${athlete.graduation_year}` : null, athlete?.position, place].filter(Boolean).join(' · ')
  const flow = journey({ profileReady: clips.length > 0 || results.length > 0, found: colleges?.found || 0, saved: colleges?.saved_count || 0, sent: colleges?.sent_count || 0 })
  const nextEmail = colleges?.saved.find(program => !program.sent_at)
  const cta = !flow.current ? { href: '/home/colleges', label: 'Email another coach' }
    : flow.current.key === 'profile' ? { href: 'https://gmtm.com', label: 'Add a clip on GMTM', external: true }
      : flow.current.key === 'colleges' ? { href: '/home/colleges', label: 'Find my colleges' }
        : flow.current.key === 'save' ? { href: '/home/colleges', label: 'Pick my colleges' }
          : { href: nextEmail ? `/home/colleges/${nextEmail.id}` : '/home/colleges', label: 'Email a coach' }

  return <div className="flex flex-col gap-10 pb-6 pt-8 md:pt-12">
    <section className="grid gap-8 md:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
      <div className="flex flex-col justify-center gap-5">
        {line && <p className="font-label text-xs uppercase tracking-[2px] text-jr-lime sm:text-[13px]">{line}</p>}
        <h1 className="break-words text-[34px] font-bold leading-[1.05] tracking-[-0.5px] sm:text-5xl lg:text-[64px] lg:leading-[1.02] lg:tracking-[-1.5px]">
          Hey {first || 'there'}.<br className="hidden sm:block" /> {colleges ? flow.headline : 'Let’s get you to your first coach email.'}
        </h1>
        <p className="max-w-[560px] text-[17px] leading-normal text-jr-soft sm:text-[19px]">Save the colleges you like, then send a short note to one coach. Your combine numbers do the talking.</p>
        <div className="flex flex-col gap-3 sm:flex-row">
          {cta.external ? <a href={cta.href} target="_blank" rel="noopener noreferrer" className={primary}>{cta.label}<span className="sr-only"> (opens in a new tab)</span></a>
            : <Link href={cta.href} className={primary}>{cta.label}</Link>}
          <Link href="/home/footage" className={outline}>See my athlete card</Link>
        </div>
      </div>
      <Link href="/home/footage" aria-label={hero ? `Featured clip: ${hero.title}. Change it on My card.` : 'Add footage. Open My card.'}
        className={`relative flex min-h-[220px] flex-col justify-end overflow-hidden rounded-3xl border border-[#26262C] bg-[#17171B] sm:min-h-[360px] ${focus}`}>
        {hero ? <Poster key={`${hero.id}:${hero.thumbnail_url || ''}`} clip={hero} /> : <div aria-hidden="true" className="absolute inset-0 bg-[repeating-linear-gradient(135deg,#1A1A1F_0,#1A1A1F_14px,#1E1E24_14px,#1E1E24_28px)]" />}
        <div className="relative flex flex-col gap-2 bg-gradient-to-t from-black/80 to-transparent p-6">
          <span className="self-start rounded-full bg-[rgba(11,11,12,0.85)] px-3 py-1.5 text-[13px] font-semibold text-jr-lime">Featured clip</span>
          <span className="break-words text-xl font-semibold">{hero ? hero.title : loading ? 'Loading your footage…' : error ? 'Your footage could not be loaded.' : 'No videos yet'}</span>
          <span className="text-sm text-jr-soft">{hero ? 'From GMTM · tap to change' : 'Videos you add on GMTM show here'}</span>
        </div>
      </Link>
    </section>

    <section aria-labelledby="journey-title" className="flex flex-col gap-6 rounded-3xl border border-jr-line bg-jr-card p-5 sm:p-8">
      <div className="flex items-baseline justify-between gap-4">
        <h2 id="journey-title" className="text-xl font-bold sm:text-2xl">Your recruiting journey</h2>
        <span className="text-[15px] text-jr-muted">{flow.done} of {flow.steps.length} done</span>
      </div>
      {collegesError && <p role="alert" className="text-sm text-amber-200">{collegesError}</p>}
      {colleges && !colleges.eligible && colleges.notice && <p role="status" className="text-sm text-jr-soft">{colleges.notice}</p>}
      <ol className="grid grid-cols-2 gap-3 lg:grid-cols-4 lg:gap-4">
        {flow.steps.map((step, index) => <li key={step.key} className="flex flex-col [&>*]:flex-1"><StepCard step={step} index={index} current={flow.current?.key === step.key} /></li>)}
      </ol>
      <div role="progressbar" aria-label="Journey progress" aria-valuemin={0} aria-valuemax={100} aria-valuenow={flow.percent} className="h-2 overflow-hidden rounded-full bg-jr-track">
        <div className="h-full bg-jr-lime" style={{ width: `${flow.percent}%` }} />
      </div>
    </section>

    <section className="grid gap-8 md:grid-cols-2">
      <div aria-labelledby="numbers-title" className="flex flex-col gap-4">
        <h2 id="numbers-title" className="text-[22px] font-bold">Your numbers</h2>
        {results.length ? <div className="grid grid-cols-3 gap-2 sm:gap-3">
          {results.slice(0, 3).map(item => <article key={item.id} className="flex min-w-0 flex-col gap-1.5 rounded-[18px] border border-jr-line bg-jr-card p-3 sm:p-5">
            <h3 className="break-words text-xs text-jr-muted sm:text-sm">{item.label}</h3>
            <p className="text-[22px] font-bold tabular-nums sm:text-4xl">{item.value}<span className="text-sm font-normal text-jr-muted sm:text-base"> {item.unit}</span></p>
            <p className="text-xs text-jr-muted sm:text-[13px]">{item.kind}</p>
          </article>)}
        </div> : <p className="rounded-[18px] border border-jr-line bg-jr-card p-5 text-jr-soft">{loading ? 'Loading your results…' : 'Your combine results will show here.'}</p>}
        {results.length > 0 && <p className="text-xs text-jr-dim">These numbers were not checked at an event. {results.length > 3 && <Link href="/home/footage" className="underline underline-offset-4">See all {results.length}</Link>}</p>}
      </div>
      <div aria-labelledby="saved-title" className="flex flex-col gap-4">
        <div className="flex items-baseline justify-between">
          <h2 id="saved-title" className="text-[22px] font-bold">Saved colleges</h2>
          {colleges?.built && colleges.found > 0 && <Link href="/home/colleges" className={`text-[15px] text-jr-lime underline-offset-4 hover:underline ${focus}`}>See all {colleges.found}</Link>}
        </div>
        {!colleges ? <p className="text-jr-muted">{collegesError ? 'Saved colleges are not available right now.' : 'Loading…'}</p>
          : colleges.saved.length ? <ul className="flex flex-col gap-2.5">
            {colleges.saved.slice(0, 5).map(program => <li key={program.id}>
              <Link href={`/home/colleges/${program.id}`} className={`flex items-center gap-3.5 rounded-2xl border border-jr-line bg-jr-card px-4 py-3.5 hover:border-jr-edge ${focus}`}>
                <Badge program={program} size="sm" />
                <span className="flex min-w-0 flex-1 flex-col"><span className="break-words font-semibold">{program.school}</span>
                  <span className="text-sm text-jr-muted"><span className="whitespace-nowrap">{program.level}</span>{program.distance_mi !== null && ` · ${aboutMiles(program.distance_mi)}`}</span></span>
                <span className={`shrink-0 rounded-full px-2.5 py-1.5 text-[13px] ${program.sent_at ? 'bg-jr-done font-semibold text-jr-lime' : 'bg-jr-track text-[#D4D4DA]'}`}>{program.sent_at ? `Emailed ${shortDate(program.sent_at)}` : 'Not emailed'}</span>
              </Link>
            </li>)}
          </ul> : <p className="rounded-2xl border border-jr-line bg-jr-card p-5 text-jr-soft">No saved colleges yet. Tap the heart on a college to save it.</p>}
      </div>
    </section>
    {hero && <p className="sr-only">Featured clip added {evidenceDate(hero.recorded_at)}.</p>}
  </div>
}
