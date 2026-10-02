'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import { apiFetch } from '@/app/_lib/api'
import Link from 'next/link'
import { evidenceDate, knownSport, ProfileEvidence, readProfileEvidence } from './profileEvidence'
import ProfileMaterialsPanel, { useProfileMaterials } from './ProfileMaterialsPanel'
import { ProfileMaterialItem } from './profileMaterials'
import AthleteCareerHome, { drillResults, featuredClip, playableClips, Poster } from './AthleteCareerHome'
import { CareerGoal, useCareerWorkspace, workLabels } from './careerWorkspace'
import { aboutMiles, Badge, readJSON, SavedColleges, savedURL, shortDate } from './ProfileColleges'
import MyCard, { leadClip, useCard } from './MyCard'
import { schoolLabels } from './journey'

export type ProfileView = 'home' | 'card' | 'footage' | 'progress'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-jr-edge px-4 py-2 text-sm font-semibold transition-colors hover:border-jr-muted disabled:cursor-wait disabled:opacity-50 ${focus}`
const field = `mt-2 block w-full min-w-0 rounded-xl border border-jr-edge bg-jr-well px-4 py-3 text-sm leading-relaxed text-white placeholder:text-jr-dim focus:border-jr-lime focus:outline-none`
const primary = `inline-flex min-h-12 items-center justify-center rounded-[14px] bg-jr-lime px-6 py-3 text-sm font-bold text-jr-ground transition-colors hover:bg-jr-lime-hover disabled:cursor-not-allowed disabled:opacity-40 ${focus}`
const card = 'rounded-[20px] border border-jr-line bg-jr-card'

export default function ProfileWorkspace({ view = 'home' }: { view?: ProfileView }) {
  const { user, isLoaded } = useSparqSession()
  if (!isLoaded) return <p role="status" className="mx-auto max-w-6xl px-5 py-16 text-gray-300">Loading your account…</p>
  if (!user?.id) return <div className="mx-auto max-w-6xl px-5 py-16"><h1 className="text-3xl font-bold">Your profile is private.</h1><p className="mt-3 text-gray-300">Open SPARQ from GMTM to see your profile.</p><a href={process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com'} className={`${secondary} mt-6`}>Back to GMTM</a></div>
  return <ProfileSession key={user.id} userId={user.id} view={view} />
}

// Saves, list size and "I sent it" counts for Home and the Emails tab.
function useSavedColleges(userId: string) {
  const [data, setData] = useState<SavedColleges | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let live = true
    readJSON<SavedColleges>(apiFetch(savedURL(userId))).then(body => { if (live) setData(body) }, e => { if (live) setError((e as Error).message) })
    return () => { live = false }
  }, [userId])
  return { data, error }
}

function ProfileSession({ userId, view }: { userId: string; view: ProfileView }) {
  const [profile, setProfile] = useState<ProfileEvidence | null>(null)
  const [version, setVersion] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ title: string; detail: string; scope?: boolean } | null>(null)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)

  const refresh = useCallback(async () => {
    if (!mounted.current || active.current) return
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setProfile(null)
    setError(null)
    const timer = window.setTimeout(() => {
      controller.abort()
      if (mounted.current && active.current === controller) {
        active.current = null
        setProfile(null)
        setLoading(false)
        setError({ title: 'Your profile took too long to load.', detail: 'Please try again.' })
      }
    }, 30000)
    controller.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const response = await apiFetch('/api/athlete/evidence', { signal: controller.signal, cache: 'no-store' })
      if (!mounted.current || controller.signal.aborted) return
      if (!response.ok) {
        const messages: Record<number, { title: string; detail: string }> = {
          401: { title: 'Please sign in again.', detail: 'Open SPARQ from GMTM again to see your profile.' },
          403: { title: 'This profile is not open to this account.', detail: 'Open SPARQ from your own GMTM account.' },
          409: { title: 'Your GMTM connection needs a check.', detail: 'Ask your coach or event organizer for help.' },
        }
        setProfile(null)
        setError(messages[response.status] ? { ...messages[response.status], scope: true } : { title: 'Your profile is not available right now.', detail: 'Try again in a moment.' })
        return
      }
      const data = readProfileEvidence(await response.json())
      if (!mounted.current || controller.signal.aborted) return
      setProfile(data)
      setVersion(value => value + 1)
    } catch {
      if (mounted.current && active.current === controller && !controller.signal.aborted) {
        setProfile(null)
        setError({ title: 'Your profile could not be loaded.', detail: 'Please try again.' })
      }
    } finally {
      window.clearTimeout(timer)
      if (active.current === controller) {
        active.current = null
        if (mounted.current) setLoading(false)
      }
    }
  }, [])

  const scopeLost = useCallback(() => {
    active.current?.abort(); active.current = null
    setProfile(null)
    void refresh()
  }, [refresh])
  const workspace = useCareerWorkspace(scopeLost)
  const associationInvalid = !!workspace.snapshot && profile?.state === 'ready' && profile.owner_scope !== workspace.snapshot.owner_scope
  useEffect(() => {
    if (workspace.error?.kind !== 'link' && (associationInvalid || error?.scope || profile?.state === 'unlinked' && workspace.snapshot)) workspace.invalidateScope()
  }, [associationInvalid, error?.scope, profile?.state, workspace.snapshot, workspace.error?.kind, workspace.invalidateScope])
  const refreshAll = async () => {
    if (workspace.loading || workspace.saving) return
    active.current?.abort(); active.current = null
    setProfile(null); setError(null); setLoading(true)
    const confirmed = await workspace.reload()
    if (!mounted.current) return
    if (!confirmed) { setLoading(false); return }
    void refresh()
  }

  useEffect(() => {
    mounted.current = true
    void refresh()
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [refresh])

  return (
    <div className="py-6 sm:py-5">
      {workspace.loading && <p role="status" className="mb-4 text-sm text-gray-400">Loading your saved work…</p>}
      {workspace.error && <div role="alert" className="mb-6 flex flex-wrap items-center justify-between gap-3 border-l-2 border-amber-300 bg-white/[0.03] px-4 py-3 text-sm">
        <p>{workspace.error.message}</p>
        <button type="button" disabled={workspace.loading || workspace.saving} onClick={() => void workspace.reload()} className={secondary}>Reload</button>
      </div>}
      {!workspace.loading && !workspace.error && workspace.snapshot && <p role="status" className="sr-only">Saved work loaded.</p>}
      {loading && !profile && !error && <div role="status" className="py-16"><p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your profile</p><h1 className="mt-4 text-3xl font-bold">Loading your profile…</h1><p className="mt-3 text-gray-400">Getting your details from GMTM.</p></div>}
      {error && <section role="alert" className="max-w-xl rounded-2xl border border-white/15 p-6 sm:p-8"><h1 className="text-2xl font-bold">{error.title}</h1><p className="mt-3 leading-relaxed text-gray-300">{error.detail}</p><div className="mt-6 flex flex-wrap gap-3"><button type="button" disabled={loading} onClick={() => void refresh()} className={secondary}>{loading ? 'Loading…' : 'Try again'}</button><a href="/enter" className={secondary}>Reconnect from GMTM</a></div></section>}
      {!error && profile?.state === 'unlinked' && <section className="max-w-xl py-8"><p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your profile</p><h1 className="mt-4 text-3xl font-bold">Bring your GMTM profile with you.</h1><p className="mt-4 leading-relaxed text-gray-300">Open SPARQ from GMTM again to connect your profile.</p><a href="/enter" className={`${secondary} mt-6`}>Reconnect from GMTM</a></section>}
      {!error && profile?.state === 'source_unavailable' && <section role="alert" className="max-w-xl py-8"><h1 className="text-3xl font-bold">We can&apos;t reach GMTM right now.</h1><p className="mt-4 leading-relaxed text-gray-300">Your results are still safe on GMTM. Try again in a moment.</p><button type="button" disabled={loading} onClick={() => void refresh()} className={`${secondary} mt-6`}>{loading ? 'Loading…' : 'Try again'}</button></section>}
      {!error && (!workspace.loading || workspace.snapshot) && workspace.error?.kind !== 'link' && !associationInvalid && profile?.state === 'ready' && <ProfileReadout key={version} userId={userId} view={view} profile={profile} refreshing={loading} onRefresh={() => void refreshAll()} workspace={workspace} />}
    </div>
  )
}

function ProfileReadout({ userId, view, profile, refreshing, onRefresh, workspace }: {
  userId: string; view: ProfileView; profile: ProfileEvidence; refreshing: boolean; onRefresh: () => void
  workspace: ReturnType<typeof useCareerWorkspace>
}) {
  const athlete = profile.athlete!
  const materialSource = useProfileMaterials()
  const materialsScopeMismatch = materialSource.scopeInvalid || !!materialSource.snapshot && (
    materialSource.snapshot.state === 'unlinked' ||
    materialSource.snapshot.state === 'ready' && (!profile.owner_scope || materialSource.snapshot.owner_scope !== profile.owner_scope) ||
    materialSource.snapshot.state === 'source_unavailable' && !!materialSource.snapshot.owner_scope && materialSource.snapshot.owner_scope !== profile.owner_scope
  )
  const materials = { ...materialSource, snapshot: materialsScopeMismatch ? null : materialSource.snapshot, error: materialSource.error || materialsScopeMismatch }
  useEffect(() => { if (materialsScopeMismatch) workspace.invalidateScope() }, [materialsScopeMismatch, workspace.invalidateScope])
  const colleges = useSavedColleges(userId)
  const featuredId = workspace.snapshot?.featured_source_id || null

  if (materialsScopeMismatch) return <p role="status" className="py-12 text-jr-soft">Checking your GMTM connection…</p>
  if (view === 'card') return <MyCard userId={userId} profile={profile} snapshot={materials.snapshot} />
  if (view === 'footage') return <FootageView profile={profile} materials={materials} workspace={workspace} refreshing={refreshing} onRefresh={onRefresh} />
  if (view === 'progress') return <ProgressView colleges={colleges.data} collegesError={colleges.error} workspace={workspace} />
  return <HomeWithCard userId={userId} profile={profile} materials={materials} featuredId={featuredId} colleges={colleges} />
}

// Home's featured clip is the lead clip on My card.
function HomeWithCard({ userId, profile, materials, featuredId, colleges }: {
  userId: string; profile: ProfileEvidence; materials: ReturnType<typeof useProfileMaterials> & { error: boolean }
  featuredId: string | null; colleges: ReturnType<typeof useSavedColleges>
}) {
  const card = useCard(userId, true)
  const state = card.data?.state === 'ready' ? { state: 'ready' as const, lead: leadClip(card.data) }
    : card.error || card.data ? { state: 'failed' as const } : { state: 'loading' as const }
  return <AthleteCareerHome profile={profile} snapshot={materials.snapshot} loading={materials.loading} error={materials.error}
    featuredId={featuredId} card={state} colleges={colleges.data} collegesError={colleges.error} />
}

// All her footage, results and materials (reached from Home's "See all"). My card is /home/card.
function FootageView({ profile, materials, workspace, refreshing, onRefresh }: {
  profile: ProfileEvidence; materials: ReturnType<typeof useProfileMaterials> & { error: boolean }
  workspace: ReturnType<typeof useCareerWorkspace>; refreshing: boolean; onRefresh: () => void
}) {
  const athlete = profile.athlete!
  const [showAllResults, setShowAllResults] = useState(false)
  const clips = playableClips(materials.snapshot)
  const featured = featuredClip(clips, workspace.snapshot?.featured_source_id || null)
  const results = drillResults(profile, materials.snapshot)
  const identity = [knownSport(athlete.sport), athlete.position, athlete.school, athlete.graduation_year === null ? null : `Class of ${athlete.graduation_year}`].filter(Boolean)
  const feature = async (item: ProfileMaterialItem) => {
    if (!item.can_include || item.kind !== 'footage' || !item.source_url || workspace.loading || workspace.saving) return
    await workspace.save({ featured_source_id: item.id })
  }
  return <div className="max-w-4xl pb-6 pt-8">
    <p className="font-label text-xs uppercase tracking-[2px] text-jr-lime">My footage</p>
    <h1 className="mt-3 break-words text-[34px] font-bold leading-tight sm:text-[44px]">{athlete.name || 'Your athlete profile'}</h1>
    {identity.length > 0 && <p className="mt-2 break-words text-jr-soft">{identity.join(' · ')}</p>}
    {(athlete.city || athlete.state) && <p className="mt-1 text-sm text-jr-muted">{[athlete.city, athlete.state].filter(Boolean).join(', ')}</p>}

    <section aria-labelledby="clips-title" className="mt-10">
      <h2 id="clips-title" className="text-[22px] font-bold">Featured clip</h2>
      <p className="mt-1 text-sm text-jr-muted">Your card leads with this clip until you choose highlights on <Link href="/home/card" className="text-jr-lime underline underline-offset-4">My card</Link>.</p>
      {clips.length ? <ul className="mt-4 grid gap-3 sm:grid-cols-2">
        {clips.map(clip => <li key={clip.id} className={`${card} overflow-hidden ${featured?.id === clip.id ? 'border-2 border-jr-lime' : ''}`}>
          <div className="relative aspect-video"><Poster key={`${clip.id}:${clip.thumbnail_url || ''}`} clip={clip} /></div>
          <div className="flex flex-wrap items-center justify-between gap-2 p-4">
            <div className="min-w-0"><p className="break-words font-semibold">{clip.title}</p><p className="text-xs text-jr-muted">Added {evidenceDate(clip.recorded_at)}</p></div>
            {featured?.id === clip.id && workspace.snapshot?.featured_source_id === clip.id
              ? <span className="rounded-full bg-jr-done px-3 py-1 text-xs font-semibold text-jr-lime">Featured</span>
              : <button type="button" disabled={workspace.saving || workspace.loading || workspace.blocked} onClick={() => void feature(clip)} className={secondary}>Feature this<span className="sr-only">: {clip.title}</span></button>}
          </div>
          <a href={clip.source_url!} target="_blank" rel="noopener noreferrer" className={`mx-4 mb-3 inline-flex min-h-11 items-center text-sm text-jr-lime underline underline-offset-4 ${focus}`}>Watch on GMTM<span className="sr-only">: {clip.title} (opens a new tab)</span></a>
        </li>)}
      </ul> : <p className={`${card} mt-4 p-5 text-jr-soft`}>{materials.loading ? 'Loading your footage…' : materials.error ? 'Your footage could not be loaded.' : 'No videos yet. Videos you add on GMTM will show here.'}</p>}
      {workspace.snapshot?.featured_source_id && <button type="button" disabled={workspace.saving || workspace.blocked} onClick={() => void workspace.save({ featured_source_id: null })} className={`${secondary} mt-4`}>Remove featured video</button>}
    </section>

    <section aria-labelledby="results-title" className="mt-10">
      <h2 id="results-title" className="text-[22px] font-bold">Your combine results</h2>
      {results.length ? <>
        <ul className="mt-4 grid grid-cols-2 gap-3 sm:grid-cols-3">{(showAllResults ? results : results.slice(0, 6)).map(item => <li key={item.id} className={`${card} p-4`}>
          <p className="text-sm text-jr-muted">{item.label}</p>
          <p className="mt-1 text-3xl font-bold tabular-nums">{item.value}<span className="text-base font-normal text-jr-muted"> {item.unit}</span></p>
          <p className="mt-1 text-xs text-jr-muted">{item.kind} · {evidenceDate(item.date)}</p>
        </li>)}</ul>
        {results.length > 6 && <button type="button" aria-expanded={showAllResults} onClick={() => setShowAllResults(value => !value)} className={`${secondary} mt-3`}>{showAllResults ? 'Show less' : `Show all ${results.length}`}</button>}
        <p className="mt-3 text-xs text-jr-dim">These numbers were not checked at an event.</p>
      </> : <p className="mt-2 text-sm text-jr-muted">Your combine results will show here.</p>}
    </section>

    <div className="mt-10"><ProfileMaterialsPanel snapshot={materials.snapshot} loading={materials.loading} error={materials.error} onRetry={() => void materials.reload()} /></div>
    <div className="mt-8 border-t border-jr-line pt-6">
      <p className="mb-3 text-xs leading-relaxed text-jr-muted">Get your newest details from GMTM. Your goal stays here.</p>
      <button type="button" disabled={refreshing} onClick={onRefresh} className={secondary}>{refreshing ? 'Refreshing…' : 'Refresh profile'}</button>
      <a href="https://gmtm.com" className={`mt-3 flex min-h-11 items-center text-sm text-jr-soft underline underline-offset-4 ${focus}`}>Change your profile on GMTM</a>
    </div>
  </div>
}

// TODO(email slice): /home/progress becomes "Emails". For now: email status per saved college, her goal and recent work.
function ProgressView({ colleges, collegesError, workspace }: { colleges: SavedColleges | null; collegesError: string; workspace: ReturnType<typeof useCareerWorkspace> }) {
  const [goalOpen, setGoalOpen] = useState(false)
  const [goalForm, setGoalForm] = useState<CareerGoal>({ text: '', destination: null, timeframe: null })
  const goalDialog = useRef<HTMLDialogElement>(null)
  const lifetime = useRef(false)
  useEffect(() => { lifetime.current = true; return () => { lifetime.current = false } }, [])
  useEffect(() => {
    if (!goalOpen || !goalDialog.current) return
    goalDialog.current.showModal()
    return () => goalDialog.current?.close()
  }, [goalOpen])
  const savedGoal = workspace.snapshot?.goal || null
  const savedLabels = schoolLabels((colleges?.saved || []).map(p => p.school))
  const editGoal = () => { setGoalForm(savedGoal ? { ...savedGoal } : { text: '', destination: null, timeframe: null }); setGoalOpen(true) }
  const saveGoal = async () => {
    const next = { text: goalForm.text.trim(), destination: goalForm.destination?.trim() || null, timeframe: goalForm.timeframe?.trim() || null }
    if (!next.text) return
    const saved = await workspace.save({ goal: next })
    if (saved && lifetime.current) setGoalOpen(false)
  }
  const removeGoal = async () => {
    const saved = await workspace.save({ goal: null })
    if (saved && lifetime.current) setGoalOpen(false)
  }
  return <div className="max-w-3xl pb-6 pt-8">
    <p className="font-label text-xs uppercase tracking-[2px] text-jr-lime">Emails</p>
    <h1 className="mt-3 text-[34px] font-bold leading-tight sm:text-[44px]">Your coach emails</h1>
    <p className="mt-2 text-jr-soft">Each saved college and whether you sent its coach an email. SPARQ never sends for you.</p>
    <section aria-label="Email status" className="mt-6">
      {collegesError ? <p role="alert" className="text-amber-200">{collegesError}</p>
        : !colleges ? <p role="status" className="text-jr-muted">Loading…</p>
          : colleges.saved.length ? <ul className="flex flex-col gap-2.5">{colleges.saved.map(program => <li key={program.id}>
            <Link href={`/home/colleges/${program.id}`} className={`flex items-center gap-3.5 ${card} px-4 py-3.5 hover:border-jr-edge ${focus}`}>
              <Badge program={program} size="sm" label={savedLabels[program.school]} />
              <span className="flex min-w-0 flex-1 flex-col"><span className="break-words font-semibold">{program.school}</span>
                <span className="text-sm text-jr-muted">{[program.level, aboutMiles(program.distance_mi)].filter(Boolean).join(' · ')}</span></span>
              <span className={`shrink-0 rounded-full px-2.5 py-1.5 text-[13px] ${program.sent_at ? 'bg-jr-done font-semibold text-jr-lime' : 'bg-jr-track text-[#D4D4DA]'}`}>{program.sent_at ? `Sent ${shortDate(program.sent_at)}` : 'Write it'}</span>
            </Link></li>)}</ul>
            : <p className={`${card} p-5 text-jr-soft`}>Save a college first. <Link href="/home/colleges" className="text-jr-lime underline underline-offset-4">Pick my colleges</Link></p>}
    </section>

    <section aria-labelledby="goal-title" className="mt-10 border-t border-jr-line pt-6">
      <div className="flex items-center justify-between gap-3">
        <h2 id="goal-title" className="text-xl font-bold">Your goal</h2>
        <button type="button" onClick={editGoal} disabled={workspace.saving || workspace.loading} className={secondary}>{savedGoal ? 'Edit goal' : 'Set a goal'}</button>
      </div>
      <p className="mt-2 break-words text-lg">{savedGoal?.text || 'What do you want to do next?'}</p>
      {savedGoal?.destination && <p className="mt-2 break-words text-sm text-jr-muted">For: {savedGoal.destination}</p>}
      {savedGoal?.timeframe && <p className="mt-1 break-words text-sm text-jr-muted">When: {savedGoal.timeframe}</p>}
    </section>

    <section aria-labelledby="career-progress" className="mt-10 border-t border-jr-line pt-6">
      <h2 id="career-progress" className="text-xl font-bold">Recent work</h2>
      {workspace.snapshot?.recent_work.length ? <ol className="mt-4 divide-y divide-jr-line">{workspace.snapshot.recent_work.map(item => <li key={item.id} className="flex flex-wrap justify-between gap-3 py-4"><span className="font-medium">{workLabels[item.kind]}</span><time dateTime={item.at} className="text-sm text-jr-muted">{evidenceDate(item.at)}</time></li>)}</ol>
        : <p className="mt-3 text-jr-soft">{workspace.loading ? 'Loading your recent work…' : workspace.error ? 'Recent work is not available right now.' : 'Your saved steps will show here.'}</p>}
    </section>

    <dialog ref={goalDialog} aria-labelledby="career-goal-editor-title" onCancel={() => setGoalOpen(false)} onClose={() => setGoalOpen(false)} className="w-[calc(100%-2rem)] max-w-xl rounded-2xl border border-jr-line bg-jr-card p-6 text-white backdrop:bg-black/70 sm:p-8">
      <form onSubmit={event => { event.preventDefault(); void saveGoal() }}>
        <h2 id="career-goal-editor-title" className="text-2xl font-semibold">Your next goal</h2>
        <label htmlFor="career-goal" className="mt-6 block text-sm font-medium">What are you working toward?</label>
        <textarea autoFocus id="career-goal" disabled={workspace.saving} rows={3} required maxLength={600} value={goalForm.text} onChange={event => setGoalForm(value => ({ ...value, text: event.target.value }))} className={field} placeholder="Your goal, in your own words" />
        <label htmlFor="career-recipient" className="mt-5 block text-sm">College or team (optional)</label>
        <input id="career-recipient" disabled={workspace.saving} maxLength={200} value={goalForm.destination || ''} onChange={event => setGoalForm(value => ({ ...value, destination: event.target.value || null }))} className={field} />
        <label htmlFor="career-timeframe" className="mt-5 block text-sm">When (optional)</label>
        <input id="career-timeframe" disabled={workspace.saving} maxLength={100} value={goalForm.timeframe || ''} onChange={event => setGoalForm(value => ({ ...value, timeframe: event.target.value || null }))} className={field} />
        <div className="mt-6 flex flex-wrap gap-3">
          <button type="submit" disabled={!goalForm.text.trim() || workspace.saving || workspace.loading || workspace.blocked} className={primary}>{workspace.saving ? 'Saving…' : 'Save goal'}</button>
          <button type="button" onClick={() => setGoalOpen(false)} className={secondary}>Cancel</button>
          {savedGoal && <button type="button" disabled={workspace.saving || workspace.loading || workspace.blocked} onClick={() => void removeGoal()} className={`min-h-11 text-sm text-jr-muted ${focus}`}>Remove goal</button>}
        </div>
        {workspace.error && <p role="alert" className="mt-4 text-sm text-amber-200">{workspace.error.message}</p>}
      </form>
    </dialog>
  </div>
}
