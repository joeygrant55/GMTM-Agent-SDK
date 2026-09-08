'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import { useRouter, useSearchParams } from 'next/navigation'
import Link from 'next/link'
import { apiFetch } from '@/app/_lib/api'
import { CombineActivity, CurrentCombine, PROGRAM_SOURCE, readCurrentCombine, supportedCombineEvent } from './currentCombine'
import { useCombineHelp } from './CombineHelpProvider'
import ActivityRequirements from './ActivityRequirements'

const button = 'inline-flex min-h-11 items-center justify-center rounded-xl px-4 py-3 text-sm font-bold focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'

export default function CurrentCombineCard() {
  const { user, isLoaded } = useUser()
  const params = useSearchParams()
  const rawEvent = params.get('event_id')
  const eventId = rawEvent && /^\d+$/.test(rawEvent) ? supportedCombineEvent(Number(rawEvent)) : null
  if (!isLoaded) return <p role="status">Loading your account…</p>
  if (!user?.id) return null
  return <CombineSession key={`${user.id}:${rawEvent ?? ''}`} clerkId={user.id} eventId={eventId} invalidEvent={rawEvent !== null && eventId === null} />
}

function CombineSession({ clerkId, eventId, invalidEvent }: { clerkId: string; eventId: number | null; invalidEvent: boolean }) {
  const router = useRouter()
  const [snapshot, setSnapshot] = useState<CurrentCombine | null>(null)
  const [refreshing, setRefreshing] = useState(true)
  const [error, setError] = useState('')
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const lastAutomaticRead = useRef(0)
  const help = useCombineHelp()
  const publishSnapshot = help?.publishSnapshot
  useEffect(() => { publishSnapshot?.(snapshot) }, [publishSnapshot, snapshot])
  useEffect(() => () => { publishSnapshot?.(null) }, [publishSnapshot])

  const refresh = useCallback(async (manual = false) => {
    if (!mounted.current || active.current) return
    const now = Date.now()
    if (!manual && now - lastAutomaticRead.current < 1000) return
    lastAutomaticRead.current = now
    const controller = new AbortController()
    active.current = controller
    setRefreshing(true)
    setError('')
    try {
      const res = await apiFetch(`/api/combine/current${eventId ? `?event_id=${eventId}` : ''}`, { signal: controller.signal, cache: 'no-store' })
      if (controller.signal.aborted || !mounted.current) return
      if (!res.ok) throw new Error(res.status === 401 ? 'Sign in again to refresh your combine progress.' : 'We could not refresh your combine progress. Try again or check your entry in GMTM.')
      const data = await res.json()
      if (controller.signal.aborted || !mounted.current) return
      const confirmed = readCurrentCombine(data, clerkId, eventId)
      // An invalid URL must show the public choices, even if a saved claim suggests an event.
      setSnapshot(invalidEvent ? { ...confirmed, state: confirmed.athlete_id === null ? 'link_required' : 'choose_event', selected_event: null, activities: [], counts: { activities: 0, submitted: null, fields_present: null } } : confirmed)
    } catch (e) {
      if (!controller.signal.aborted && mounted.current) setError(e instanceof Error ? e.message : 'We could not refresh your combine progress.')
    } finally {
      if (active.current === controller) {
        active.current = null
        if (mounted.current) setRefreshing(false)
      }
    }
  }, [clerkId, eventId, invalidEvent])

  useEffect(() => {
    mounted.current = true
    // StrictMode cleanup may abort the first read; the next setup must start afresh.
    lastAutomaticRead.current = 0
    void refresh()
    const onFocus = () => { if (document.visibilityState === 'visible') void refresh() }
    const onPageShow = () => { void refresh() }
    window.addEventListener('focus', onFocus)
    window.addEventListener('pageshow', onPageShow)
    document.addEventListener('visibilitychange', onFocus)
    return () => {
      mounted.current = false
      active.current?.abort()
      active.current = null
      window.removeEventListener('focus', onFocus)
      window.removeEventListener('pageshow', onPageShow)
      document.removeEventListener('visibilitychange', onFocus)
    }
  }, [refresh])

  const selectEvent = (id: string) => {
    const selected = supportedCombineEvent(Number(id))
    if (selected) router.push(`/home/inbox?event_id=${selected}`)
  }
  const event = snapshot?.selected_event
  const activities = snapshot ? [...snapshot.activities].sort((a, b) => a.order - b.order) : []
  const next = activities.find(a => a.submission_state === 'not_submitted' || a.evidence_state === 'missing_fields')
  const hasPersonalProgress = snapshot?.athlete_id !== null && snapshot?.athlete_id !== undefined

  return (
    <section aria-labelledby="current-combine-title" className="min-w-0 rounded-2xl border border-sparq-lime/30 bg-gradient-to-br from-sparq-lime/10 to-transparent p-5 sm:p-7">
      <p className="text-xs font-bold uppercase tracking-widest text-sparq-lime">Your current combine</p>
      <h2 id="current-combine-title" className="mt-3 break-words text-2xl font-black">{event?.name || 'Choose your USA Football combine'}</h2>
      <p className="mt-3 text-sm leading-relaxed text-gray-300">See the organizer’s activities, continue your entry in GMTM, and return here to check saved progress. Results are not needed to start.</p>
      {event && (
          <div className="mt-5">
            <p className="font-semibold">{next ? `Next: ${next.title}` : hasPersonalProgress ? 'Review your entry in GMTM' : 'Start or continue your entry in GMTM'}</p>
            <a href={event.continuation_url} className={`${button} mt-3 bg-sparq-lime text-sparq-charcoal`}>Continue in GMTM <span aria-hidden className="ml-2">→</span></a>
            <p className="mt-2 text-xs text-gray-400">Submit in GMTM, then return here to check your progress.</p>
          </div>
      )}
      {invalidEvent && <p role="alert" className="mt-3 text-sm text-amber-200">That combine is not available here. Choose one of the current combines below.</p>}
      {snapshot && (
        <div className="mt-4">
          <label htmlFor="combine-event" className="block text-sm font-semibold">Combine division</label>
          <select id="combine-event" value={event?.event_id ?? ''} onChange={e => selectEvent(e.target.value)} className="mt-2 min-h-11 w-full min-w-0 rounded-lg border border-white/20 bg-sparq-charcoal p-3 text-white">
            <option value="" disabled>Choose a combine</option>
            {snapshot.events.map(e => <option key={e.event_id} value={e.event_id}>{e.division} — {e.name}</option>)}
          </select>
          {!event && <p className="mt-2 text-sm text-gray-400">Choose the event you are entering. We do not select a division from your results or age.</p>}
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button type="button" onClick={() => void refresh(true)} disabled={refreshing} className={`${button} border border-white/20 disabled:opacity-50`}>{refreshing ? 'Refreshing…' : 'Refresh progress'}</button>
        <p role="status" aria-live="polite" className="text-xs text-gray-400">{snapshot ? `Last checked ${new Date(snapshot.fetched_at).toLocaleString()}` : refreshing ? 'Loading combine activities…' : 'No progress snapshot available'}</p>
      </div>
      {error && <p role="alert" className="mt-3 rounded-lg border border-amber-300/30 bg-amber-300/5 p-3 text-sm text-amber-200">{error}{snapshot ? ' Showing the last successful check; progress may have changed.' : ''}</p>}
      {snapshot?.state === 'link_required' && (
        <div className="mt-4 rounded-xl border border-white/15 p-4 text-sm">
          <p>Personal progress is unavailable until your GMTM athlete profile is connected. You can still read each activity’s required fields, ask for help here, and continue in GMTM.</p>
          <p className="mt-2 text-gray-300">Use your organizer’s secure invitation to link a profile.</p>
          <Link href={event ? `/connect?event_id=${event.event_id}` : '/connect'} className="mt-2 inline-flex min-h-11 items-center font-bold text-sparq-lime underline">Check an existing connection</Link>
        </div>
      )}
      {snapshot && event && (
        <>
          <p className="mt-4 text-sm text-gray-300">Published deadline: <strong>{event.deadline_display}</strong>. <a className="underline text-sparq-lime" href={event.deadline_source_url}>USA Football program details</a></p>
          <div className="mt-5 rounded-xl bg-white/[0.04] p-4">
            <p className="font-bold">{hasPersonalProgress ? `${snapshot.counts.submitted} of ${snapshot.counts.activities} activities submitted` : `${snapshot.counts.activities} organizer activities · personal progress unavailable`}</p>
            {hasPersonalProgress && <p className="mt-2 text-sm text-gray-300">Required information saved for {snapshot.counts.fields_present} activities</p>}
            <p className="mt-2 text-sm text-gray-400">USA Football reviews entries and confirms eligibility separately.</p>
          </div>

          <ol aria-label="Combine activities" className="mt-6 space-y-3">
            {activities.map(activity => <ActivityRow key={activity.task_id} activity={activity} onHelp={help ? () => help.openHelp(activity.task_id) : undefined} />)}
          </ol>
          <p className="mt-4 text-sm text-gray-400">Athlete ID validity is not checked here. See <a href={PROGRAM_SOURCE} className="text-sparq-lime underline">USA Football’s Athlete ID and program requirements</a>.</p>
          {hasPersonalProgress && snapshot.counts.submitted === snapshot.counts.activities && snapshot.counts.activities > 0 && (
            <div className="mt-5 border-t border-white/10 pt-4 text-sm">
              <p>Your listed activities have submissions. You can review your performance evidence below and keep your athlete profile current while any organizer review takes place.</p>
              <Link href="/home/profile" className="mt-2 inline-flex min-h-11 items-center font-bold text-sparq-lime underline">Review your athlete profile</Link>
            </div>
          )}
        </>
      )}
    </section>
  )
}

function ActivityRow({ activity: a, onHelp }: { activity: CombineActivity; onHelp?: () => void }) {
  const submitted = a.submission_state === 'submitted'
  const status = a.submission_state === 'unavailable' ? 'Progress unavailable' : submitted ? 'Submitted' : 'Not submitted'
  // Known organizer label bug: keep the source field identity intact; teach the actual activity distance.
  const missingLabels = a.missing_fields.map(label => a.event_id === 1318 && a.task_id === 4907 && label === '40 Yard Dash Time' ? '20-yard dash time' : label)
  return (
    <li className="min-w-0 rounded-xl border border-white/10 bg-sparq-charcoal/40 p-4">
      <div className="flex flex-wrap items-start justify-between gap-2">
        <h3 className="min-w-0 break-words font-bold">{a.order + 1}. {a.title}</h3>
        <span className={`text-xs font-semibold ${submitted ? 'text-sparq-lime' : 'text-gray-400'}`}>{status}</span>
      </div>
      {a.kind === 'highlight' && <p className="mt-2 text-sm text-gray-300">Additional playing footage, separate from the exercise videos and background form.</p>}
      {a.evidence_state === 'missing_fields' && missingLabels.length > 0 && <p className="mt-2 break-words text-sm text-amber-200">Still needed: {missingLabels.join('; ')}</p>}
      {a.evidence_state === 'fields_present' && <p className="mt-2 text-sm text-gray-300">Saved information found</p>}
      {a.evidence_state === 'unknown' && submitted && <p className="mt-2 text-sm text-gray-300">Submission found. Some saved information could not be checked; review it in GMTM.</p>}
      {onHelp && <button type="button" onClick={onHelp} className="mt-3 min-h-11 rounded-lg border border-sparq-lime/30 px-3 text-sm font-bold text-sparq-lime">Help with this activity</button>}
      <details className="mt-3 text-sm">
        <summary className="min-h-11 cursor-pointer py-3 font-semibold text-sparq-lime">Organizer instructions</summary>
        <ActivityRequirements activity={a} />
        <p className="whitespace-pre-wrap break-words leading-relaxed text-gray-300">{a.description || 'Open the activity in GMTM to read the organizer’s instructions.'}</p>
        <a href={a.continuation_url} className="mt-2 inline-flex min-h-11 items-center font-bold text-sparq-lime underline">Open this combine in GMTM</a>
      </details>
    </li>
  )
}
