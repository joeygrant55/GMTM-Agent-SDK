'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import { apiFetch } from '@/app/_lib/api'
import { evidenceDate, evidenceValue, isBodySize, knownSport, ProfileEvidence, readProfileEvidence } from './profileEvidence'
import ProfileMaterialsPanel, { useProfileMaterials } from './ProfileMaterialsPanel'
import { ProfileMaterialItem } from './profileMaterials'
import AthleteCareerHome from './AthleteCareerHome'
import { CareerGoal, useCareerWorkspace, workLabels } from './careerWorkspace'
import { useCareerNavigation } from './ProfileWorkspaceShell'
import { useRouter } from 'next/navigation'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold transition-colors hover:border-white/40 disabled:cursor-wait disabled:opacity-50 ${focus}`
const field = `mt-2 block w-full min-w-0 rounded-xl border border-white/15 bg-white/[0.03] px-4 py-3 text-sm leading-relaxed text-white placeholder:text-gray-400 focus:border-sparq-lime focus:outline-none`
const primary = `inline-flex min-h-12 items-center justify-center rounded-xl bg-sparq-lime px-6 py-3 text-sm font-bold text-sparq-charcoal transition-colors hover:bg-sparq-lime-light disabled:cursor-not-allowed disabled:opacity-40 ${focus}`

// Junior pilot: the main action is finding colleges. The colleges page explains
// itself to an account that cannot use it yet.
const NEXT_MOVE = { title: 'Find colleges.', detail: 'See college flag football programs and why each one could fit you.', label: 'Find colleges' }

export default function ProfileWorkspace() {
  const { user, isLoaded } = useSparqSession()
  if (!isLoaded) return <p role="status" className="mx-auto max-w-6xl px-5 py-16 text-gray-300">Loading your account…</p>
  if (!user?.id) return <div className="mx-auto max-w-6xl px-5 py-16"><h1 className="text-3xl font-bold">Your profile is private.</h1><p className="mt-3 text-gray-300">Open SPARQ from GMTM to see your profile.</p><a href={process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com'} className={`${secondary} mt-6`}>Back to GMTM</a></div>
  return <ProfileSession key={user.id} />
}

function ProfileSession() {
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
      {!error && (!workspace.loading || workspace.snapshot) && workspace.error?.kind !== 'link' && !associationInvalid && profile?.state === 'ready' && <ProfileReadout key={version} profile={profile} refreshing={loading} onRefresh={() => void refreshAll()} workspace={workspace} />}
    </div>
  )
}

function ProfileReadout({ profile, refreshing, onRefresh, workspace }: {
  profile: ProfileEvidence; refreshing: boolean; onRefresh: () => void
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
  const [showAllResults, setShowAllResults] = useState(false)
  const { view, setView, revision: navigationRevision } = useCareerNavigation()
  const router = useRouter()
  const [goalOpen, setGoalOpen] = useState(false)
  const [goalForm, setGoalForm] = useState<CareerGoal>({ text: '', destination: null, timeframe: null })
  const goalDialog = useRef<HTMLDialogElement>(null)
  const [profileOpen, setProfileOpen] = useState(false)
  const sheet = useRef<HTMLDialogElement>(null)
  const lifetime = useRef(false)
  useEffect(() => { lifetime.current = true; return () => { lifetime.current = false } }, [])
  useEffect(() => {
    const dialog = sheet.current
    if (!dialog || !profileOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog.showModal()
    return () => { dialog.close(); document.body.style.overflow = previousOverflow }
  }, [profileOpen])
  const featureClip = async (item: ProfileMaterialItem) => {
    if (!item.can_include || item.kind !== 'footage' || !item.source_url || workspace.loading || workspace.saving) return
    await workspace.save({ featured_source_id: item.id })
  }
  const editGoal = () => {
    setGoalForm(workspace.snapshot?.goal ? { ...workspace.snapshot.goal } : { text: '', destination: null, timeframe: null })
    setGoalOpen(true)
  }
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
  useEffect(() => {
    if (!goalOpen || !goalDialog.current) return
    goalDialog.current.showModal()
    return () => goalDialog.current?.close()
  }, [goalOpen])
  useEffect(() => {
    setGoalOpen(false)
    setProfileOpen(view === 'portfolio')
  }, [navigationRevision, view])
  const closeProfile = () => { setProfileOpen(false); if (view === 'portfolio') setView('home') }
  const savedGoal = workspace.snapshot?.goal || null
  const identity = [knownSport(athlete.sport), athlete.position, athlete.school, athlete.graduation_year === null ? null : `Class of ${athlete.graduation_year}`].filter(Boolean)
  // Body size is not a combine result.
  const results = profile.evidence.filter(item => !isBodySize(item.label))

  if (materialsScopeMismatch) return <p role="status" className="py-12 text-gray-300">Checking your GMTM connection…</p>

  return (
    <>
      <div hidden={view !== 'home' && view !== 'portfolio'}>
        <AthleteCareerHome profile={profile} snapshot={materials.snapshot} loading={materials.loading} error={materials.error}
          goal={savedGoal} featuredId={workspace.snapshot?.featured_source_id || null} saving={workspace.saving || workspace.loading}
          nextMove={NEXT_MOVE} recent={workspace.snapshot?.recent_work || []}
          onNext={() => router.push('/home/colleges')} onEditGoal={editGoal} onFeature={item => void featureClip(item)}
          onBrowse={() => setProfileOpen(true)} onProgress={() => setView('progress')} />
      </div>

      <section hidden={view !== 'progress'} className="max-w-3xl py-8 sm:py-16" aria-labelledby="career-progress">
        <p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your progress</p>
        <h1 id="career-progress" className="mt-4 text-3xl font-semibold tracking-tight sm:text-5xl">Recent work</h1>
        <p className="mt-4 text-base text-gray-400">The steps you have saved in SPARQ.</p>
        {workspace.snapshot?.recent_work.length ? <ol className="mt-8 divide-y divide-white/10">{workspace.snapshot.recent_work.map(item => <li key={item.id} className="flex flex-wrap justify-between gap-3 py-5"><span className="font-medium">{workLabels[item.kind]}</span><time dateTime={item.at} className="text-sm text-gray-400">{evidenceDate(item.at)}</time></li>)}</ol> : <p className="mt-8 text-gray-300">{workspace.loading ? 'Loading your recent work…' : workspace.error ? 'Recent work is not available right now.' : 'Your saved steps will show here.'}</p>}
        <button type="button" onClick={() => setView('home')} className={secondary + ' mt-6'}>Back to my home</button>
      </section>

      <dialog ref={goalDialog} aria-labelledby="career-goal-editor-title" onCancel={() => setGoalOpen(false)} onClose={() => setGoalOpen(false)} className="w-[calc(100%-2rem)] max-w-xl rounded-2xl border border-white/15 bg-sparq-charcoal-light p-6 text-white backdrop:bg-black/70 sm:p-8">
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
            {savedGoal && <button type="button" disabled={workspace.saving || workspace.loading || workspace.blocked} onClick={() => void removeGoal()} className={`min-h-11 text-sm text-gray-400 ${focus}`}>Remove goal</button>}
          </div>
          {workspace.error && <p role="alert" className="mt-4 text-sm text-amber-200">{workspace.error.message}</p>}
        </form>
      </dialog>

      <dialog ref={sheet} aria-labelledby="profile-sheet-title" onCancel={closeProfile} onClose={closeProfile} className="fixed inset-y-0 left-auto right-0 m-0 ml-auto h-[100dvh] max-h-none w-full max-w-[540px] border-0 bg-sparq-charcoal-light p-0 text-white backdrop:bg-black/70">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-white/10 bg-sparq-charcoal-light px-5 py-4 sm:px-8">
          <h2 id="profile-sheet-title" className="text-lg font-semibold">Your profile</h2>
          <button type="button" autoFocus onClick={closeProfile} className={secondary}>Done</button>
        </div>
        <div className="px-5 py-6 sm:px-8">
          <p className="break-words text-2xl font-semibold tracking-tight">{athlete.name || 'Your athlete profile'}</p>
          {identity.length > 0 && <p className="mt-2 break-words text-sm leading-relaxed text-gray-300">{identity.join(' · ')}</p>}
          {(athlete.city || athlete.state) && <p className="mt-1 text-sm text-gray-400">{[athlete.city, athlete.state].filter(Boolean).join(', ')}</p>}
          <section aria-labelledby="profile-evidence-title" className="my-8">
            <h3 id="profile-evidence-title" className="text-lg font-semibold">Your combine results</h3>
            {results.length ? <>
              <ul className="mt-2 divide-y divide-white/10">{(showAllResults ? results : results.slice(0, 3)).map(item => <li key={item.id} className="py-5"><span className="block break-words text-sm font-medium text-gray-300">{item.label}</span><span className="mt-1 block break-words text-2xl font-semibold tabular-nums">{evidenceValue(item)}</span><span className="mt-2 block break-words text-xs leading-relaxed text-gray-400">{evidenceDate(item.recorded_at)}{item.event_name ? ` · ${item.event_name}` : ''}</span></li>)}</ul>
              {results.length > 3 && <button type="button" aria-expanded={showAllResults} onClick={() => setShowAllResults(value => !value)} className={`${secondary} mt-3`}>{showAllResults ? 'Show less' : `Show all ${results.length}`}</button>}
              <p className="mt-3 text-xs leading-relaxed text-gray-400">These numbers were not checked at an event.</p>
            </> : <p className="mt-2 text-sm leading-relaxed text-gray-400">Your combine results will show here.</p>}
          </section>
          <ProfileMaterialsPanel snapshot={materials.snapshot} loading={materials.loading} error={materials.error} onRetry={() => void materials.reload()} />
          <div className="mt-8 border-t border-white/10 pt-6">
            {workspace.snapshot?.featured_source_id && <button type="button" disabled={workspace.saving || workspace.blocked} onClick={() => void workspace.save({ featured_source_id: null })} className={secondary + ' mb-5'}>Remove featured video</button>}
            <p className="mb-3 text-xs leading-relaxed text-gray-400">Get your newest details from GMTM. Your goal stays here.</p>
            <button type="button" disabled={refreshing} onClick={onRefresh} className={secondary}>{refreshing ? 'Refreshing…' : 'Refresh profile'}</button>
            <a href="https://gmtm.com" className={`mt-3 flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 ${focus}`}>Change your profile on GMTM</a>
          </div>
        </div>
      </dialog>
    </>
  )
}
