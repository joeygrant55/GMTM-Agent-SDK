'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'
import { apiFetch } from '@/app/_lib/api'
import { evidenceDate, evidenceValue, prepareProfileDraft, ProfileDraftKind, ProfileEvidence, readProfileEvidence } from './profileEvidence'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold transition-colors hover:border-white/40 disabled:cursor-wait disabled:opacity-50 ${focus}`
const field = `mt-2 block w-full min-w-0 rounded-xl border border-white/15 bg-black/20 px-4 py-3 text-sm leading-relaxed text-white placeholder:text-gray-400 focus:border-sparq-lime focus:outline-none`

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
    <div className="mx-auto max-w-6xl px-5 py-10 sm:px-8 sm:py-14">
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
  const [showAllResults, setShowAllResults] = useState(false)
  const [kind, setKind] = useState<ProfileDraftKind>('summary')
  const [goal, setGoal] = useState('')
  const [destination, setDestination] = useState('')
  const [draft, setDraft] = useState<string | null>(null)
  const [inputsChanged, setInputsChanged] = useState(false)
  const [copyStatus, setCopyStatus] = useState('')
  const [copying, setCopying] = useState(false)
  const draftInput = useRef<HTMLTextAreaElement>(null)
  const lifetime = useRef(false)
  const draftRevision = useRef(0)
  useEffect(() => { lifetime.current = true; return () => { lifetime.current = false } }, [])
  const changed = () => { if (draft !== null) setInputsChanged(true); setCopyStatus('') }
  const prepare = () => {
    setDraft(prepareProfileDraft(profile, selected, goal, destination, kind))
    draftRevision.current += 1
    setInputsChanged(false)
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

  return (
    <>
      <header className="mb-10 flex flex-wrap items-start justify-between gap-5 border-b border-white/10 pb-8">
        <div className="min-w-0 max-w-2xl"><p className="text-xs font-semibold uppercase tracking-[0.18em] text-sparq-lime">Your experience, ready to use</p><h1 className="mt-4 break-words text-4xl font-bold tracking-tight sm:text-5xl">{athlete.name || 'Your athlete profile'}</h1>{identity.length > 0 && <p className="mt-4 break-words text-sm leading-relaxed text-gray-300">{identity.join(' · ')}</p>}{(athlete.city || athlete.state) && <p className="mt-1 text-sm text-gray-400">{[athlete.city, athlete.state].filter(Boolean).join(', ')}</p>}</div>
        <button type="button" disabled={refreshing} onClick={onRefresh} className={secondary}>{refreshing ? 'Refreshing…' : 'Refresh profile'}</button>
      </header>

      <div className="grid min-w-0 gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.05fr)] lg:gap-12">
        <section aria-labelledby="profile-evidence-title" className="min-w-0">
          <h2 id="profile-evidence-title" className="text-2xl font-semibold tracking-tight">What your profile records</h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-400">{profile.evidence.length ? 'Choose the results you want to include. Each keeps its source and date.' : 'Your profile details are available. No numeric performance results were returned with this profile.'}</p>
          {profile.evidence.length > 0 ? <fieldset className="mt-6"><legend className="sr-only">Evidence to include</legend><div className="divide-y divide-white/10 rounded-2xl border border-white/10 bg-white/[0.02]">{(showAllResults ? profile.evidence : profile.evidence.slice(0, 3)).map(item => <label key={item.id} className="flex cursor-pointer items-start gap-4 p-4 sm:p-5"><input type="checkbox" checked={selected.includes(item.id)} onChange={event => { setSelected(value => event.target.checked ? [...value, item.id] : value.filter(id => id !== item.id)); changed() }} className={`mt-1 h-5 w-5 shrink-0 accent-sparq-lime ${focus}`} /><span className="min-w-0 flex-1"><span className="block break-words text-sm font-medium text-gray-300">{item.label}</span><span className="mt-1 block break-words text-2xl font-semibold tabular-nums">{evidenceValue(item)}</span><span className="mt-2 block break-words text-xs leading-relaxed text-gray-400">{item.source_label} · {evidenceDate(item.recorded_at)}{item.event_name ? ` · ${item.event_name}` : ''}</span></span><span className="sr-only">Include {item.label}</span></label>)}</div>{profile.evidence.length > 3 && <button type="button" aria-expanded={showAllResults} onClick={() => setShowAllResults(value => !value)} className={`${secondary} mt-3`}>{showAllResults ? 'Show fewer results' : `Show all ${profile.evidence.length} results`}</button>}<p className="mt-3 text-xs leading-relaxed text-gray-400">Recorded results; measurement verification is unconfirmed.</p></fieldset> : <div className="mt-6 rounded-2xl border border-dashed border-white/20 p-6"><p className="text-sm leading-relaxed text-gray-300">You can still prepare a summary from your profile and goal. We won’t fill in results or infer measurements from uploads.</p></div>}

          {profile.observations.length > 0 && <div className="mt-8 space-y-5">{profile.observations.map((observation, index) => <article key={index}><h3 className="text-sm font-semibold">{observation.title}</h3><p className="mt-2 text-sm leading-relaxed text-gray-300">{observation.detail}</p>{observation.evidence_ids.length > 0 && <p className="mt-2 text-xs leading-relaxed text-gray-400">Based on: {observation.evidence_ids.map(id => profile.evidence.find(item => item.id === id)?.label).join(', ')}</p>}</article>)}</div>}
          <details className="mt-7 border-t border-white/10 pt-2"><summary className={`min-h-11 cursor-pointer py-3 text-sm text-gray-400 ${focus}`}>Sources &amp; limitations</summary><p className="text-xs leading-relaxed text-gray-400">Profile read {evidenceDate(profile.fetched_at)}. Recorded results do not confirm eligibility, selection or a coach’s interest.</p>{profile.limitations.length > 0 && <ul className="mt-3 list-disc space-y-2 pl-4 text-xs leading-relaxed text-gray-400">{profile.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul>}<a href="https://gmtm.com" className={`mt-3 inline-flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 ${focus}`}>Open GMTM for your profile and submissions</a></details>
        </section>

        <section aria-labelledby="profile-output-title" className="min-w-0 rounded-2xl border border-white/15 bg-sparq-charcoal-light p-5 sm:p-7">
          <h2 id="profile-output-title" className="text-2xl font-semibold tracking-tight">Put your profile to work.</h2><p className="mt-3 text-sm leading-relaxed text-gray-400">Prepare a factual summary for a real use. Make it yours before copying.</p>
          <form className="mt-6" onSubmit={event => { event.preventDefault(); prepare() }}>
            <label htmlFor="profile-goal" className="text-sm font-medium">What are you working toward?</label><textarea id="profile-goal" value={goal} onChange={event => { setGoal(event.target.value); changed() }} maxLength={600} rows={2} required className={field} placeholder="Your next goal, in your own words" />
            <fieldset className="mt-5"><legend className="sr-only">Output format</legend><div className="flex flex-wrap gap-4">{(['summary', 'introduction'] as const).map(value => <label key={value} className="flex min-h-11 cursor-pointer items-center gap-2 text-sm"><input type="radio" name="profile-output-format" value={value} checked={kind === value} onChange={() => { setKind(value); setDestination(''); changed() }} className={`h-4 w-4 accent-sparq-lime ${focus}`} />{value === 'summary' ? 'Profile summary' : 'Introduction'}</label>)}</div></fieldset>
            <label htmlFor="profile-destination" className="mt-3 block text-sm font-medium">{kind === 'introduction' ? 'Who is this for?' : 'Intended use (optional)'}</label><input id="profile-destination" value={destination} onChange={event => { setDestination(event.target.value); changed() }} maxLength={200} required={kind === 'introduction'} className={field} placeholder={kind === 'introduction' ? 'A real recipient you already have in mind' : 'Where you plan to use this summary'} />
            <p className="mt-3 text-xs leading-relaxed text-gray-400">{selected.length ? `${selected.length} recorded ${selected.length === 1 ? 'result' : 'results'} selected.` : 'No results selected; your summary will use profile details and your goal.'}{kind === 'introduction' ? ' This does not find or contact a recipient.' : ''}</p>
            <button type="submit" disabled={!goal.trim() || (kind === 'introduction' && !destination.trim())} className={`mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-sparq-lime px-5 py-3 text-sm font-bold text-sparq-charcoal transition-colors hover:bg-sparq-lime-light disabled:cursor-not-allowed disabled:opacity-40 ${focus}`}>{draft === null ? 'Prepare my text' : 'Rebuild from these details'}</button>
          </form>

          {draft !== null && <div className="mt-7 border-t border-white/10 pt-6"><label htmlFor="profile-draft" className="text-sm font-semibold">Your text — ready to edit</label><p className="mt-2 text-xs leading-relaxed text-gray-400">Assembled from your selected facts and words. Review the details before using them. Rebuilding replaces your edits.</p>{inputsChanged && <p role="status" className="mt-3 text-xs text-amber-200">Your selections changed. Rebuild to include them, or keep editing this version.</p>}<textarea id="profile-draft" ref={draftInput} value={draft} onChange={event => { setDraft(event.target.value); draftRevision.current += 1; setCopyStatus('') }} rows={12} className={`${field} resize-y`} /><div className="mt-4 flex flex-wrap gap-3"><button type="button" disabled={copying || !draft.trim()} onClick={() => void copy()} className={secondary}>{copying ? 'Copying…' : 'Copy text'}</button><button type="button" onClick={() => { draftInput.current?.focus(); draftInput.current?.select(); setCopyStatus('Text selected. Use your device’s copy command.') }} className={secondary}>Select all text</button></div><p role="status" aria-live="polite" className="mt-3 text-xs leading-relaxed text-gray-300">{copyStatus}</p></div>}
          <p className="mt-6 text-xs leading-relaxed text-gray-400">Private to this page. Nothing is sent or published. Refreshing or leaving clears your draft.</p>
        </section>
      </div>
    </>
  )
}
