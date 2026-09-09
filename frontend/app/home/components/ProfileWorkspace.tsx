'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { apiFetch } from '@/app/_lib/api'
import { evidenceDate, evidenceValue, prepareProfileDraft, ProfileDraftKind, ProfileEvidence, readProfileEvidence } from './profileEvidence'
import ProfileMaterialsPanel, { useProfileMaterials } from './ProfileMaterialsPanel'
import { addMaterialsToDraft, ProfileMaterialItem } from './profileMaterials'
import AthleteDebriefPanel from './AthleteDebriefPanel'
import AthleteShowcase from './AthleteShowcase'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold transition-colors hover:border-white/40 disabled:cursor-wait disabled:opacity-50 ${focus}`
const field = `mt-2 block w-full min-w-0 rounded-xl border border-white/15 bg-white/[0.03] px-4 py-3 text-sm leading-relaxed text-white placeholder:text-gray-400 focus:border-sparq-lime focus:outline-none`
const primary = `inline-flex min-h-12 items-center justify-center rounded-xl bg-sparq-lime px-6 py-3 text-sm font-bold text-sparq-charcoal transition-colors hover:bg-sparq-lime-light disabled:cursor-not-allowed disabled:opacity-40 ${focus}`

export default function ProfileWorkspace() {
  const { user, isLoaded } = useUser()
  if (!isLoaded) return <p role="status" className="mx-auto max-w-6xl px-5 py-16 text-gray-300">Loading your account…</p>
  if (!user?.id) return <div className="mx-auto max-w-6xl px-5 py-16"><h1 className="text-3xl font-bold">Your profile is private.</h1><p className="mt-3 text-gray-300">Sign in to see your own athlete evidence.</p><Link href="/sign-in" className={`${secondary} mt-6`}>Sign in</Link></div>
  return <ProfileSession key={user.id} />
}

function ProfileSession() {
  const [profile, setProfile] = useState<ProfileEvidence | null>(null)
  const [version, setVersion] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<{ title: string; detail: string } | null>(null)
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
        setError({ title: 'Your profile took too long to load.', detail: 'Please try again. No profile evidence has been changed.' })
      }
    }, 30000)
    controller.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const response = await apiFetch('/api/athlete/evidence', { signal: controller.signal, cache: 'no-store' })
      if (!mounted.current || controller.signal.aborted) return
      if (!response.ok) {
        const messages: Record<number, { title: string; detail: string }> = {
          401: { title: 'Please sign in again.', detail: 'Your session could not be confirmed. Sign in to load your private profile.' },
          403: { title: 'This profile is not available to this account.', detail: 'We could not confirm permission to show this athlete’s evidence.' },
          409: { title: 'Your profile connection needs review.', detail: 'We found a conflicting connection. Ask your organizer to review it before continuing.' },
        }
        setProfile(null)
        setError(messages[response.status] || { title: 'Your profile is temporarily unavailable.', detail: 'We could not read your GMTM evidence. Try again in a moment.' })
        return
      }
      const data = readProfileEvidence(await response.json())
      if (!mounted.current || controller.signal.aborted) return
      setProfile(data)
      setVersion(value => value + 1)
    } catch {
      if (mounted.current && active.current === controller && !controller.signal.aborted) {
        setProfile(null)
        setError({ title: 'Your profile could not be loaded.', detail: 'We could not confirm the latest evidence. Please try again.' })
      }
    } finally {
      window.clearTimeout(timer)
      if (active.current === controller) {
        active.current = null
        if (mounted.current) setLoading(false)
      }
    }
  }, [])

  useEffect(() => {
    mounted.current = true
    void refresh()
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [refresh])

  return (
    <div className="mx-auto max-w-6xl px-5 py-6 sm:px-8 sm:py-8">
      {loading && !profile && !error && <div role="status" className="py-16"><p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your private profile</p><h1 className="mt-4 text-3xl font-bold">Bringing your evidence together…</h1><p className="mt-3 text-gray-400">Reading the details already in your GMTM profile.</p></div>}
      {error && <section role="alert" className="max-w-xl rounded-2xl border border-white/15 p-6 sm:p-8"><h1 className="text-2xl font-bold">{error.title}</h1><p className="mt-3 leading-relaxed text-gray-300">{error.detail}</p><div className="mt-6 flex flex-wrap gap-3"><button type="button" disabled={loading} onClick={() => void refresh()} className={secondary}>{loading ? 'Loading…' : 'Try again'}</button><Link href="/connect" className={secondary}>Check connection</Link>{error.title === 'Please sign in again.' && <Link href="/sign-in" className={secondary}>Sign in</Link>}</div></section>}
      {!error && profile?.state === 'unlinked' && <section className="max-w-xl py-8"><p className="text-xs uppercase tracking-[0.18em] text-sparq-lime">Your private profile</p><h1 className="mt-4 text-3xl font-bold">Bring your GMTM profile with you.</h1><p className="mt-4 leading-relaxed text-gray-300">Your account does not have a confirmed athlete connection yet. Use your organizer’s secure invitation, or check an existing connection.</p><Link href="/connect" className={`${secondary} mt-6`}>Check connection</Link></section>}
      {!error && profile?.state === 'source_unavailable' && <section role="alert" className="max-w-xl py-8"><h1 className="text-3xl font-bold">Your GMTM evidence is unavailable.</h1><p className="mt-4 leading-relaxed text-gray-300">We could not read your source profile. This does not mean your results are missing.</p><button type="button" disabled={loading} onClick={() => void refresh()} className={`${secondary} mt-6`}>{loading ? 'Loading…' : 'Try again'}</button></section>}
      {!error && profile?.state === 'ready' && <ProfileReadout key={version} profile={profile} refreshing={loading} onRefresh={() => void refresh()} />}
    </div>
  )
}

function ProfileReadout({ profile, refreshing, onRefresh }: { profile: ProfileEvidence; refreshing: boolean; onRefresh: () => void }) {
  const athlete = profile.athlete!
  const [selected, setSelected] = useState<string[]>([])
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>([])
  const materials = useProfileMaterials()
  const [showAllResults, setShowAllResults] = useState(false)
  const [kind, setKind] = useState<ProfileDraftKind>('summary')
  const [goal, setGoal] = useState('')
  const [destination, setDestination] = useState('')
  const [draft, setDraft] = useState<string | null>(null)
  const [inputsChanged, setInputsChanged] = useState(false)
  const [copyStatus, setCopyStatus] = useState('')
  const [copying, setCopying] = useState(false)
  const [composerOpen, setComposerOpen] = useState(false)
  const [guidanceOpen, setGuidanceOpen] = useState(false)
  const [detailsOpen, setDetailsOpen] = useState(true)
  const [profileOpen, setProfileOpen] = useState(false)
  const [debriefVersion, setDebriefVersion] = useState(0)
  const sheet = useRef<HTMLDialogElement>(null)
  const composerHeading = useRef<HTMLHeadingElement>(null)
  const writeButton = useRef<HTMLButtonElement>(null)
  const askButton = useRef<HTMLButtonElement>(null)
  const draftInput = useRef<HTMLTextAreaElement>(null)
  const lifetime = useRef(false)
  const draftRevision = useRef(0)
  useEffect(() => { lifetime.current = true; return () => { lifetime.current = false } }, [])
  const changed = () => { if (draft !== null) setInputsChanged(true); setCopyStatus('') }
  useEffect(() => {
    const dialog = sheet.current
    if (!dialog || !profileOpen) return
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    dialog.showModal()
    return () => { dialog.close(); document.body.style.overflow = previousOverflow }
  }, [profileOpen])
  const openComposer = (nextKind: ProfileDraftKind, question: string) => {
    setComposerOpen(true)
    if (kind !== nextKind) { setKind(nextKind); setDestination(''); setDetailsOpen(true); changed() }
    if (!goal.trim() && question.length <= 600) { setGoal(question); changed() }
    requestAnimationFrame(() => { if (lifetime.current) composerHeading.current?.focus() })
  }
  const backToSPARQ = () => {
    setComposerOpen(false)
    requestAnimationFrame(() => { if (lifetime.current) writeButton.current?.focus() })
  }
  const useClip = (item: ProfileMaterialItem) => {
    if (!item.can_include || item.kind !== 'footage' || !item.source_url) return
    if (!selectedMaterials.includes(item.id)) {
      setSelectedMaterials(value => value.includes(item.id) ? value : [...value, item.id])
      changed()
    }
    openComposer('introduction', '')
  }
  const showGuidance = () => {
    setGuidanceOpen(true)
    requestAnimationFrame(() => { if (lifetime.current) {
      const heading = document.getElementById('profile-debrief-title')
      heading?.setAttribute('tabindex', '-1'); heading?.focus()
    } })
  }
  const prepare = () => {
    const includedMaterials = materials.snapshot?.state === 'ready'
      ? materials.snapshot.items.filter(item => item.can_include && selectedMaterials.includes(item.id)) : []
    setDraft(addMaterialsToDraft(prepareProfileDraft(profile, selected, goal, destination, kind), includedMaterials, kind))
    draftRevision.current += 1
    setInputsChanged(false)
    setDetailsOpen(false)
    setCopyStatus('')
    requestAnimationFrame(() => { if (lifetime.current) draftInput.current?.focus() })
  }
  const copy = async () => {
    if (draft === null || !draft.trim() || copying) return
    const revision = draftRevision.current
    setCopying(true)
    setCopyStatus('')
    try {
      if (!navigator.clipboard?.writeText) throw new Error('Clipboard unavailable')
      await navigator.clipboard.writeText(draft)
      if (lifetime.current && revision === draftRevision.current) setCopyStatus('Copied to clipboard. Nothing has been sent.')
    } catch {
      if (lifetime.current && revision === draftRevision.current) setCopyStatus('Clipboard access is unavailable. Select the text below and copy it manually.')
    } finally { if (lifetime.current) setCopying(false) }
  }
  const identity = [athlete.sport, athlete.position, athlete.school, athlete.graduation_year === null ? null : `Class of ${athlete.graduation_year}`].filter(Boolean)

  const selectedCount = selected.length + selectedMaterials.length
  const profileContext = [athlete.sport, athlete.position].filter(Boolean).join(' · ')
  const includedClips = materials.snapshot?.items.filter(item => item.kind === 'footage' && selectedMaterials.includes(item.id)) || []

  return (
    <>
      <header className="flex min-w-0 items-center justify-between gap-4">
        <div className="min-w-0">
          <h1 className="break-words text-base font-semibold tracking-tight">{athlete.name || 'Your athlete profile'}</h1>
          {profileContext && <p className="mt-1 break-words text-xs text-gray-400">{profileContext}</p>}
        </div>
        <button type="button" aria-haspopup="dialog" onClick={() => setProfileOpen(true)} className={`${secondary} shrink-0 rounded-full`}>View profile</button>
      </header>

      <div className={`mx-auto w-full pb-12 pt-8 sm:pt-12 ${composerOpen || guidanceOpen ? 'max-w-3xl' : ''}`}>
        <div hidden={composerOpen}>
          <div hidden={guidanceOpen}>
            <AthleteShowcase profile={profile} snapshot={materials.snapshot} loading={materials.loading} error={materials.error} onUseClip={useClip} onBrowse={() => setProfileOpen(true)} />
            <button ref={askButton} type="button" onClick={showGuidance} className={`${secondary} mt-6`}>Ask about my profile</button>
          </div>
          <div hidden={!guidanceOpen}>
            <button type="button" onClick={() => { setGuidanceOpen(false); requestAnimationFrame(() => { if (lifetime.current) askButton.current?.focus() }) }} className={`mb-6 min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>Back to your content</button>
            <AthleteDebriefPanel key={debriefVersion} onPrepare={openComposer} />
          </div>
          <div className="mt-6 border-t border-white/10 pt-4">
            <button ref={writeButton} type="button" onClick={() => openComposer(draft === null ? 'introduction' : kind, '')} className={`min-h-11 text-sm text-gray-400 transition-colors hover:text-white ${focus}`}>{draft === null ? 'Write an introduction' : 'Return to your draft'}</button>
          </div>
        </div>

        <section hidden={!composerOpen} aria-labelledby="profile-output-title">
          <button type="button" onClick={backToSPARQ} className={`mb-6 min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>Back to SPARQ</button>
          <p className="text-xs font-semibold uppercase tracking-[0.18em] text-sparq-lime">{kind === 'introduction' ? 'Your introduction' : 'Your profile summary'}</p>
          <h2 ref={composerHeading} tabIndex={-1} id="profile-output-title" className="mt-3 text-3xl font-semibold tracking-[-0.035em] outline-none sm:text-5xl">{draft === null ? 'Make the first move.' : 'Make it yours.'}</h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-400">{draft === null ? 'Choose your details. Add your goal. Find your words.' : 'Edit your text, then copy it when you’re ready.'}</p>
          <div className="my-6 flex flex-wrap items-center gap-x-5 gap-y-2 border-y border-white/10 py-3">
            <button type="button" aria-haspopup="dialog" onClick={() => setProfileOpen(true)} className={`inline-flex min-h-11 items-center gap-3 text-sm text-gray-200 ${focus}`}>Choose profile details<span className="rounded-full bg-white/10 px-2.5 py-1 text-xs tabular-nums" aria-label={`${selectedCount} selected`}>{selectedCount}</span></button>
            {draft !== null && <button type="button" aria-expanded={detailsOpen} aria-controls="profile-draft-details" onClick={() => setDetailsOpen(value => !value)} className={`min-h-11 text-sm text-gray-400 hover:text-white ${focus}`}>{detailsOpen ? 'Hide details' : 'Edit details'}</button>}
          </div>
          {includedClips.length > 0 && <div aria-label="Selected footage" className="mb-6 flex flex-wrap gap-2">{includedClips.map(item => <span key={item.id} className="inline-flex max-w-full items-center gap-2 rounded-lg bg-white/[0.04] px-3 py-2 text-xs text-gray-300"><span className="text-sparq-lime">Selected footage</span><span className="min-w-0 break-words">{item.title}</span></span>)}</div>}
          <form id="profile-draft-details" hidden={!detailsOpen} onSubmit={event => { event.preventDefault(); prepare() }}>
            <fieldset><legend className="sr-only">Output format</legend><div className="flex flex-wrap gap-2">{(['summary', 'introduction'] as const).map(value => <label key={value} className="cursor-pointer"><input type="radio" name="profile-output-format" value={value} checked={kind === value} onChange={() => { setKind(value); setDestination(''); changed() }} className="peer sr-only" /><span className="inline-flex min-h-11 items-center rounded-full border border-white/15 px-4 text-sm text-gray-400 transition-colors peer-checked:border-white/40 peer-checked:bg-white/[0.06] peer-checked:text-white peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-4 peer-focus-visible:outline-sparq-lime">{value === 'summary' ? 'Profile summary' : 'Introduction'}</span></label>)}</div></fieldset>
            <label htmlFor="profile-goal" className="mt-6 block text-sm font-medium">What are you working toward?</label><textarea id="profile-goal" value={goal} onChange={event => { setGoal(event.target.value); changed() }} maxLength={600} rows={2} required className={field} placeholder="Your next goal, in your own words" />
            <label htmlFor="profile-destination" className="mt-5 block text-sm font-medium">{kind === 'introduction' ? 'Who is this for?' : 'Intended use (optional)'}</label><input id="profile-destination" value={destination} onChange={event => { setDestination(event.target.value); changed() }} maxLength={200} required={kind === 'introduction'} className={field} placeholder={kind === 'introduction' ? 'A coach or organization you have in mind' : 'Where you plan to use this summary'} />
            <p className="mt-3 text-xs leading-relaxed text-gray-400">{selectedCount ? `${selectedCount} selected ${selectedCount === 1 ? 'record' : 'records'}, plus your profile and goal.` : 'Using your profile and goal. Add recorded results above if you want.'}</p>
            {draft !== null && <p className="mt-3 text-xs text-amber-200">Rebuilding replaces your edits.</p>}
            <button type="submit" disabled={!goal.trim() || (kind === 'introduction' && !destination.trim())} className={`${primary} my-6 w-full sm:w-auto`}>{draft === null ? 'Prepare my text' : 'Rebuild from these details'}</button>
          </form>

          {draft !== null && <div>
            <label htmlFor="profile-draft" className="sr-only">Your text — ready to edit</label>
            {inputsChanged && <p role="status" className="mb-3 text-xs leading-relaxed text-amber-200">Your selections changed. Rebuild to include them, or keep editing this version.</p>}
            <textarea id="profile-draft" ref={draftInput} value={draft} onChange={event => { setDraft(event.target.value); draftRevision.current += 1; setCopyStatus('') }} rows={12} className={`${field} resize-y p-5 leading-7 sm:p-6`} />
            <div className="mt-5 flex flex-wrap items-center gap-3"><button type="button" disabled={copying || !draft.trim()} onClick={() => void copy()} className={primary}>{copying ? 'Copying…' : 'Copy text'}</button><button type="button" onClick={() => { draftInput.current?.focus(); draftInput.current?.select(); setCopyStatus('Text selected. Use your device’s copy command.') }} className={`min-h-11 px-3 text-sm text-gray-400 hover:text-white ${focus}`}>Select all text</button></div>
            <p role="status" aria-live="polite" className="mt-3 text-xs leading-relaxed text-gray-300">{copyStatus}</p>
          </div>}
          <p className="mt-6 text-xs leading-relaxed text-gray-400">Nothing is sent. Copy your draft before refreshing or leaving.</p>
        </section>
      </div>

      <dialog ref={sheet} aria-labelledby="profile-sheet-title" onCancel={() => setProfileOpen(false)} onClose={() => setProfileOpen(false)} className="fixed inset-y-0 left-auto right-0 m-0 ml-auto h-[100dvh] max-h-none w-full max-w-[540px] border-0 bg-sparq-charcoal-light p-0 text-white backdrop:bg-black/70">
        <div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-white/10 bg-sparq-charcoal-light px-5 py-4 sm:px-8">
          <h2 id="profile-sheet-title" className="text-lg font-semibold">Your profile</h2>
          <button type="button" autoFocus onClick={() => setProfileOpen(false)} className={secondary}>Done</button>
        </div>
        <div className="px-5 py-6 sm:px-8">
          <p className="break-words text-2xl font-semibold tracking-tight">{athlete.name || 'Your athlete profile'}</p>
          {identity.length > 0 && <p className="mt-2 break-words text-sm leading-relaxed text-gray-300">{identity.join(' · ')}</p>}
          {(athlete.city || athlete.state) && <p className="mt-1 text-sm text-gray-400">{[athlete.city, athlete.state].filter(Boolean).join(', ')}</p>}
          <section aria-labelledby="profile-evidence-title" className="mt-8">
            <h3 id="profile-evidence-title" className="text-lg font-semibold">What your profile records</h3>
            <p className="mt-2 text-sm leading-relaxed text-gray-400">{profile.evidence.length ? 'Select details to include in your text.' : 'No numeric performance results were returned with this profile.'}</p>
            {profile.evidence.length > 0 && <fieldset className="mt-4"><legend className="sr-only">Evidence to include</legend><div className="divide-y divide-white/10">{(showAllResults ? profile.evidence : profile.evidence.slice(0, 3)).map(item => <label key={item.id} className="flex cursor-pointer items-start gap-4 py-5"><input type="checkbox" checked={selected.includes(item.id)} onChange={event => { setSelected(value => event.target.checked ? [...value, item.id] : value.filter(id => id !== item.id)); changed() }} className={`mt-1 h-5 w-5 shrink-0 accent-sparq-lime ${focus}`} /><span className="min-w-0 flex-1"><span className="block break-words text-sm font-medium text-gray-300">{item.label}</span><span className="mt-1 block break-words text-2xl font-semibold tabular-nums">{evidenceValue(item)}</span><span className="mt-2 block break-words text-xs leading-relaxed text-gray-400">{item.source_label} · {evidenceDate(item.recorded_at)}{item.event_name ? ` · ${item.event_name}` : ''}</span></span><span className="sr-only">Include {item.label}</span></label>)}</div>{profile.evidence.length > 3 && <button type="button" aria-expanded={showAllResults} onClick={() => setShowAllResults(value => !value)} className={`${secondary} mt-3`}>{showAllResults ? 'Show fewer results' : `Show all ${profile.evidence.length} results`}</button>}<p className="mt-3 text-xs leading-relaxed text-gray-400">Recorded results; measurement verification is unconfirmed.</p></fieldset>}
            <details className="my-5"><summary className={`min-h-11 cursor-pointer py-3 text-sm text-gray-400 ${focus}`}>Sources &amp; limitations</summary><p className="text-xs leading-relaxed text-gray-400">Profile read {evidenceDate(profile.fetched_at)}. Recorded results do not confirm eligibility, selection or a coach’s interest.</p>{profile.observations.map((observation, index) => <p key={index} className="mt-3 text-xs leading-relaxed text-gray-400">{observation.detail}</p>)}{profile.limitations.length > 0 && <ul className="mt-3 list-disc space-y-2 pl-4 text-xs leading-relaxed text-gray-400">{profile.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>}<a href="https://gmtm.com" className={`mt-3 inline-flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 ${focus}`}>Open GMTM for your profile and submissions</a></details>
          </section>
          <ProfileMaterialsPanel snapshot={materials.snapshot} loading={materials.loading} error={materials.error} selected={selectedMaterials}
            onToggle={(item, checked) => { setSelectedMaterials(value => checked ? [...value, item.id] : value.filter(id => id !== item.id)); changed() }}
            onRetry={() => { setSelectedMaterials([]); setDebriefVersion(value => value + 1); void materials.reload() }} />
          <div className="mt-8 border-t border-white/10 pt-6">
            <p className="mb-3 text-xs leading-relaxed text-gray-400">Refreshing clears your answer, selections and draft.</p>
            <button type="button" disabled={refreshing} onClick={onRefresh} className={secondary}>{refreshing ? 'Refreshing…' : 'Refresh profile'}</button>
          </div>
        </div>
      </dialog>
    </>
  )
}
