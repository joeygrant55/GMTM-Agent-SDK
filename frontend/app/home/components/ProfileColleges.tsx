'use client'

// Junior colleges (profile surface only). Sourced programs, why each fits, distance
// from her GMTM city, saves, contact rules with their sources, and a draft she copies
// or opens in her own email. SPARQ never sends. No fit score is shown or received.
import { useCallback, useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'
import { badgeColors, initials, mapWindow } from './journey'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-jr-lime'
export const primary = `inline-flex min-h-12 items-center justify-center rounded-[14px] bg-jr-lime px-6 py-3 text-base font-bold text-jr-ground hover:bg-jr-lime-hover disabled:cursor-wait disabled:opacity-50 ${focus}`
export const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-jr-edge px-4 py-2 text-sm font-semibold text-jr-text hover:border-jr-muted disabled:cursor-wait disabled:opacity-50 ${focus}`
const small = `inline-flex min-h-11 items-center justify-center rounded-xl px-3.5 text-sm ${focus}`
const textLink = `inline-flex min-h-11 items-center text-sm text-jr-lime underline underline-offset-4 hover:text-jr-lime-hover ${focus}`

export interface CollegeProgram {
  id: string; school: string; city: string; state: string; governing_body: string; level: string
  conference: string | null; program_link: string | null; program_link_label: string; source_links: string[]
  questionnaire_link: string | null; source_checked: string; notes: string | null; reason: string | null
  starts: string | null; primary_color: string | null; map: { x: number; y: number } | null
  distance_mi: number | null; saved: boolean; sent_at: string | null
}
export interface ContactRules { governing_body: string; level: string; rules: Array<{ text: string; source_url: string | null; source_label: string | null }> }
export interface Origin { city: string | null; state: string | null; map: { x: number; y: number } | null }
export interface CollegeList {
  eligible: boolean; notice: string | null; built: boolean; programs: CollegeProgram[]; contact_rules: ContactRules[]
  origin: Origin | null; saved_count: number; sent_count: number
}
export interface SavedColleges { eligible: boolean; notice: string | null; built: boolean; found: number; saved: CollegeProgram[]; saved_count: number; sent_count: number; origin: Origin | null }
interface Draft { id: number; to_email: string; school: string | null; subject: string; body: string }

const https = (url: string | null | undefined): string | null => (typeof url === 'string' && url.startsWith('https://') ? url : null)
const collegesURL = (userId: string, rest = '') => `${BACKEND_URL}/api/workspace/colleges/${encodeURIComponent(userId)}${rest}`
export const savedURL = (userId: string, rest = '') => `${BACKEND_URL}/api/workspace/saved-colleges/${encodeURIComponent(userId)}${rest}`
const JSON_POST = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// Plain words for a 13-year-old. Backend detail text is never shown as is.
const NETWORK = "We can't reach SPARQ right now. Check your internet and try again."
export async function readJSON<T>(request: Promise<Response>): Promise<T> {
  let response: Response
  try { response = await request } catch { throw new Error(NETWORK) }
  if (!response.ok) {
    const detail = await response.json().then(body => (typeof body?.detail === 'string' ? body.detail : ''), () => '')
    throw new Error(
      detail === 'parent_notice_required' ? 'A parent needs to read the note on your home page first.'
        : response.status === 401 ? 'Your SPARQ time ran out. Open SPARQ from GMTM again.'
          : response.status === 403 ? "This part of SPARQ isn't open for your account."
            : response.status === 404 ? "We couldn't find that. Go back and try again."
              : response.status === 409 ? 'Write a draft for this college first.'
                : response.status === 429 ? "You've done this a lot in the last hour. Take a break and try again later."
                  : response.status === 502 ? "We couldn't write that just now. Try again in a minute."
                    : 'Something went wrong on our side. Try again in a minute.')
  }
  try { return await response.json() as T } catch { throw new Error('Something went wrong on our side. Try again in a minute.') }
}

export const shortDate = (iso: string) => new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date(iso))
export const aboutMiles = (mi: number | null) => (mi === null ? null : `about ${mi} mi`)

export function Badge({ program, size = 'md' }: { program: Pick<CollegeProgram, 'school' | 'primary_color'>; size?: 'sm' | 'md' }) {
  return <span aria-hidden="true" style={badgeColors(program.primary_color)}
    className={`flex shrink-0 items-center justify-center font-bold ${size === 'sm' ? 'h-11 w-11 rounded-xl text-sm' : 'h-16 w-16 rounded-2xl text-[22px]'}`}>{initials(program.school)}</span>
}

function HeartIcon({ on }: { on: boolean }) {
  return <svg width="22" height="22" viewBox="0 0 24 24" aria-hidden="true" fill={on ? '#CAFD00' : 'none'} stroke={on ? '#CAFD00' : '#D4D4DA'} strokeWidth="2"><path d="M12 21s-7-4.4-9.5-9A5.5 5.5 0 0 1 12 6a5.5 5.5 0 0 1 9.5 6c-2.5 4.6-9.5 9-9.5 9z" /></svg>
}
export function HeartButton({ program, busy, onToggle }: { program: CollegeProgram; busy: boolean; onToggle: () => void }) {
  return <button type="button" aria-pressed={program.saved} aria-label={program.saved ? `Saved: ${program.school}. Tap to remove.` : `Save ${program.school}`}
    disabled={busy} onClick={onToggle}
    className={`flex h-11 w-11 shrink-0 items-center justify-center rounded-xl disabled:opacity-50 ${focus} ${program.saved ? 'bg-jr-done' : 'border border-jr-edge'}`}><HeartIcon on={program.saved} /></button>
}

// Saves are optimistic and roll back if the server says no.
export function useSave(userId: string | undefined, apply: (id: string, saved: boolean) => void) {
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const toggle = useCallback(async (program: CollegeProgram) => {
    if (!userId || busy) return
    const next = !program.saved
    setBusy(program.id); setError(''); apply(program.id, next)
    try { await readJSON(apiFetch(savedURL(userId, `/${program.id}`), JSON_POST({ saved: next }))) } catch (e) { apply(program.id, !next); setError((e as Error).message) } finally { setBusy(null) }
  }, [userId, busy, apply])
  return { busy, error, toggle }
}

function ExternalLink({ href, children }: { href: string | null; children: React.ReactNode }) {
  const url = https(href)
  if (!url) return null
  return <a href={url} target="_blank" rel="noopener noreferrer" className={textLink}>{children}<span className="sr-only"> (opens in a new tab)</span></a>
}

function ProgramLinks({ program }: { program: CollegeProgram }) {
  return <>
    {program.program_link ? <ExternalLink href={program.program_link}>{program.program_link_label}</ExternalLink>
      : program.source_links.map((url, index) => <ExternalLink key={url} href={url}>Source {index + 1}</ExternalLink>)}
    <ExternalLink href={program.questionnaire_link}>Recruit questionnaire</ExternalLink>
  </>
}

function Meta({ program }: { program: CollegeProgram }) {
  return <p className="text-sm text-jr-muted">
    {program.city}, {program.state}{program.distance_mi !== null && <> · <b className="font-semibold text-jr-text">{aboutMiles(program.distance_mi)}</b></>} · {program.level}
    {program.starts && <span className="ml-2 inline-block rounded-full bg-jr-track px-2.5 py-0.5 text-xs text-jr-text">{program.starts}</span>}
  </p>
}

function ProgramCard({ program, busy, onToggle }: { program: CollegeProgram; busy: boolean; onToggle: () => void }) {
  return <article className={`flex gap-4 rounded-[20px] bg-jr-card p-4 sm:p-[18px] ${program.saved ? 'border-2 border-jr-lime' : 'border border-jr-line'}`}>
    <Badge program={program} />
    <div className="flex min-w-0 flex-1 flex-col gap-1.5">
      <div className="flex justify-between gap-3">
        <h3 className="break-words text-lg font-bold leading-snug sm:text-xl">{program.school}</h3>
        <HeartButton program={program} busy={busy} onToggle={onToggle} />
      </div>
      <Meta program={program} />
      {program.reason && <p className="mt-1 break-words text-[15px] leading-normal text-[#D4D4DA]">{program.reason}</p>}
      <div className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1">
        <Link href={`/home/colleges/${program.id}`} className={`${small} bg-jr-lime font-bold text-jr-ground hover:bg-jr-lime-hover`}>Email the coach<span className="sr-only">: {program.school}</span></Link>
        {program.sent_at && <span className="rounded-full bg-jr-done px-2.5 py-1 text-xs font-semibold text-jr-lime">Emailed {shortDate(program.sent_at)}</span>}
        <ProgramLinks program={program} />
      </div>
    </div>
  </article>
}

// Bundled continental-US outline + markers placed by the server's map projection. No tile server.
// The view zooms to her city and the listed programs (pure CSS on the same local SVG).
function CollegeMap({ programs, origin }: { programs: CollegeProgram[]; origin: Origin | null }) {
  const placed = programs.filter(p => p.map)
  const view = mapWindow([...placed.map(p => p.map!), ...(origin?.map ? [origin.map] : [])])
  // Percent of the whole map -> percent of the visible window.
  const at = (m: { x: number; y: number }) => ({ left: `${((m.x - view.x) / view.w) * 100}%`, top: `${((m.y - view.y) / view.h) * 100}%` })
  // Up to 4 text labels, skipping any that would sit on top of one already placed (or on "You").
  const labelled: CollegeProgram[] = []
  for (const p of placed) {
    const taken = [...labelled.map(q => q.map!), ...(origin?.map ? [origin.map] : [])]
    if (labelled.length < 4 && taken.every(m => Math.abs(m.x - p.map!.x) > view.w * 0.16 || Math.abs(m.y - p.map!.y) > view.h * 0.08)) labelled.push(p)
  }
  return <div className="flex flex-col overflow-hidden rounded-3xl border border-jr-line bg-[#101318]">
    <div className="relative aspect-[8/5] w-full overflow-hidden">
      <img src="/us-states.svg" alt="" aria-hidden="true" className="absolute max-w-none"
        style={{ width: `${10000 / view.w}%`, height: `${10000 / view.h}%`, left: `${(-view.x / view.w) * 100}%`, top: `${(-view.y / view.h) * 100}%` }} />
      <ul aria-label="Colleges on the map">
        {placed.map(p => <li key={p.id} className="absolute -translate-x-1/2 -translate-y-1/2" style={at(p.map!)}>
          <Link href={`/home/colleges/${p.id}`} aria-label={`${p.school}${p.distance_mi !== null ? `, ${aboutMiles(p.distance_mi)}` : ''}`}
            style={badgeColors(p.primary_color)} className={`block rounded-lg font-bold shadow ${focus} ${labelled.includes(p) ? 'px-2 py-1 text-xs' : 'h-3 w-3 rounded-full ring-2 ring-[#101318]'}`}>
            {labelled.includes(p) ? `${initials(p.school)}${p.distance_mi !== null ? ` · ${p.distance_mi} mi` : ''}` : ''}
          </Link>
        </li>)}
      </ul>
      {origin?.map && <div className="pointer-events-none absolute -translate-x-1/2 -translate-y-1/2" style={at(origin.map)}>
        <span className="block h-4 w-4 rounded-full bg-jr-lime shadow-[0_0_0_8px_rgba(202,253,0,0.18)]" />
        <span className="absolute left-6 top-[-2px] text-[13px] font-semibold text-jr-lime">You</span>
      </div>}
      {placed.length > labelled.length && <span className="absolute bottom-3 right-3 rounded-lg bg-jr-track px-2.5 py-1 text-xs font-semibold">+{placed.length - labelled.length} more</span>}
    </div>
    <p className="border-t border-jr-line px-5 py-3 text-sm text-jr-muted">
      {origin?.city && origin.state ? `Distances from ${origin.city}, ${origin.state} (your GMTM city)` : 'Add your city on GMTM to see distances.'}
    </p>
  </div>
}

function ContactPanel({ rules }: { rules: ContactRules[] }) {
  if (!rules.length) return null
  return <section aria-labelledby="contact-title" className="mt-10 border-t border-jr-line pt-6">
    <h2 id="contact-title" className="text-xl font-bold">How college contact works</h2>
    <p className="mt-2 text-sm text-jr-muted">These rules say when coaches can reach out to you. If a coach does not answer yet, it can be a rule, not a no.</p>
    <div className="mt-4 grid gap-5 sm:grid-cols-2">
      {rules.map(group => <div key={group.governing_body}>
        <h3 className="font-semibold">{group.level}</h3>
        <ul className="mt-2 space-y-2 text-sm text-jr-soft">
          {group.rules.map(rule => <li key={rule.text}>{rule.text}{rule.source_url && <> <ExternalLink href={rule.source_url}>{rule.source_label || 'Source'}</ExternalLink></>}</li>)}
        </ul>
      </div>)}
    </div>
  </section>
}

function NotEligible({ notice, busy, onCheck }: { notice: string | null; busy: boolean; onCheck: () => void }) {
  return <div role="status" className="rounded-[20px] border border-jr-line bg-jr-card p-6">
    <p className="text-lg">{notice}</p>
    <div className="mt-5 flex flex-wrap gap-3">
      {/* After a fix on GMTM, this reads the GMTM profile again. */}
      <button type="button" onClick={onCheck} disabled={busy} className={secondary}>{busy ? 'Checking…' : 'Check again'}</button>
    </div>
  </div>
}

type Level = 'All' | 'NCAA' | 'NAIA' | 'NJCAA'
const LEVELS: Level[] = ['All', 'NCAA', 'NAIA', 'NJCAA']
const NEAR_MI = 150
const chip = (on: boolean) => `inline-flex min-h-11 items-center rounded-full border px-4 text-[15px] ${focus} ${on ? 'border-jr-lime bg-jr-done font-semibold text-jr-lime' : 'border-jr-edge text-[#D4D4DA] hover:border-jr-muted'}`

export function ProfileColleges() {
  const { user, isLoaded } = useSparqSession()
  const [list, setList] = useState<CollegeList | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [level, setLevel] = useState<Level>('All')
  const [near, setNear] = useState(false)
  const [savedOnly, setSavedOnly] = useState(false)
  const [mapOpen, setMapOpen] = useState(false)
  const userId = user?.id

  useEffect(() => {
    if (!userId) return
    let live = true
    readJSON<CollegeList>(apiFetch(collegesURL(userId))).then(body => { if (live) setList(body) }, e => { if (live) setError(e.message) })
    return () => { live = false }
  }, [userId])

  const build = useCallback(async () => {
    if (!userId) return
    setBusy(true); setError('')
    try {
      setList(await readJSON<CollegeList>(apiFetch(`${BACKEND_URL}/api/workspace/trigger-matching/${encodeURIComponent(userId)}`, { method: 'POST' })))
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }, [userId])

  const apply = useCallback((id: string, saved: boolean) => setList(current => {
    if (!current) return current
    const changed = current.programs.some(p => p.id === id && p.saved !== saved)
    return { ...current, saved_count: current.saved_count + (changed ? (saved ? 1 : -1) : 0), programs: current.programs.map(p => (p.id === id ? { ...p, saved } : p)) }
  }), [])
  const save = useSave(userId, apply)

  const shown = useMemo(() => (list?.programs || []).filter(p =>
    (level === 'All' || p.level.startsWith(level)) && (!near || (p.distance_mi !== null && p.distance_mi <= NEAR_MI)) && (!savedOnly || p.saved)), [list, level, near, savedOnly])
  const hasDistances = !!list?.programs.some(p => p.distance_mi !== null)

  if (!isLoaded || (!list && !error)) return <p role="status" className="py-16 text-center text-jr-muted">Loading your colleges…</p>
  return <div className="pb-12 pt-8">
    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 className="text-[34px] font-bold leading-tight tracking-[-1px] sm:text-[44px]">College flag football</h1>
        {list?.eligible && list.built && <p className="mt-2 text-[17px] text-jr-soft">{list.programs.length} programs that fit you. {hasDistances ? 'Closest first. ' : ''}Tap the heart to save.</p>}
      </div>
      {list?.eligible && list.built && list.programs.length > 0 && <div role="group" aria-label="Filter colleges" className="flex flex-wrap gap-2">
        {LEVELS.map(l => <button key={l} type="button" aria-pressed={level === l} onClick={() => setLevel(l)} className={chip(level === l)}>{l === 'All' ? 'All levels' : l}</button>)}
        {hasDistances && <button type="button" aria-pressed={near} onClick={() => setNear(v => !v)} className={chip(near)}>Within {NEAR_MI} mi</button>}
        <button type="button" aria-pressed={savedOnly} onClick={() => setSavedOnly(v => !v)} className={chip(savedOnly)}>Saved ({list.saved_count})</button>
      </div>}
    </div>
    {error && <p role="alert" className="mt-4 text-red-300">{error}</p>}
    {save.error && <p role="alert" className="mt-4 text-red-300">{save.error}</p>}
    {list && !list.eligible ? <div className="mt-6"><NotEligible notice={list.notice} busy={busy} onCheck={() => void build()} /></div>
      : list && <>
        {!list.built && <div className="mt-6 rounded-[20px] border border-jr-line bg-jr-card p-6">
          <p className="max-w-2xl text-jr-soft">Programs near you first, at every level. Each one comes from a school, conference or governing body page.</p>
          <button type="button" onClick={() => void build()} disabled={busy} className={`${primary} mt-5`}>{busy ? 'Finding colleges…' : 'Find my colleges'}</button>
        </div>}
        {list.built && !list.programs.length && <p className="mt-6 text-jr-muted">No programs to show right now.</p>}
        {list.built && list.programs.length > 0 && <>
          <button type="button" aria-expanded={mapOpen} aria-controls="college-map" onClick={() => setMapOpen(v => !v)} className={`${secondary} mt-6 w-full md:hidden`}>{mapOpen ? 'Hide map' : 'Map'}</button>
          <div className="mt-4 grid items-start gap-6 md:mt-6 md:grid-cols-2">
            <div className="flex flex-col gap-3.5">
              {shown.length ? shown.map(program => <ProgramCard key={program.id} program={program} busy={save.busy === program.id} onToggle={() => void save.toggle(program)} />)
                : <p className="rounded-[20px] border border-jr-line bg-jr-card p-6 text-jr-soft">{savedOnly ? 'No saved colleges yet. Tap a heart to save one.' : 'No colleges match these filters.'}</p>}
            </div>
            <div id="college-map" className={`${mapOpen ? 'block' : 'hidden'} order-first md:sticky md:top-6 md:order-none md:block`}>
              <CollegeMap programs={shown} origin={list.origin} />
            </div>
          </div>
          <div className="mt-6"><button type="button" onClick={() => void build()} disabled={busy} className={secondary}>{busy ? 'Checking…' : 'Check my list again'}</button></div>
        </>}
        <ContactPanel rules={list.contact_rules} />
      </>}
  </div>
}

export function ProfileCollegeDetail({ programId }: { programId: string }) {
  const { user } = useSparqSession()
  const userId = user?.id
  const [detail, setDetail] = useState<{ program: CollegeProgram; contact_rules: ContactRules[] } | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  // The draft as SPARQ wrote it; any difference means the athlete edited it.
  const [written, setWritten] = useState<Draft | null>(null)
  const [confirmReplace, setConfirmReplace] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')

  useEffect(() => {
    if (!userId) return
    let live = true
    Promise.all([
      readJSON<{ program: CollegeProgram; contact_rules: ContactRules[] }>(apiFetch(collegesURL(userId, `/${programId}`))),
      readJSON<{ draft: Draft | null }>(apiFetch(collegesURL(userId, `/${programId}/outreach-draft`))),
    ]).then(([d, saved]) => { if (live) { setDetail(d); setDraft(saved.draft); setWritten(saved.draft) } }, e => { if (live) setError(e.message) })
    return () => { live = false }
  }, [userId, programId])

  const apply = useCallback((id: string, saved: boolean) => setDetail(d => d && d.program.id === id ? { ...d, program: { ...d.program, saved } } : d), [])
  const save = useSave(userId, apply)
  const edited = !!draft && !!written && (draft.to_email !== written.to_email || draft.subject !== written.subject || draft.body !== written.body)
  const write = async (replace = false) => {
    if (!userId || busy) return
    if (edited && !replace) { setConfirmReplace(true); return }
    setConfirmReplace(false); setBusy(true); setError(''); setCopied('')
    try {
      const next = (await readJSON<{ draft: Draft }>(apiFetch(collegesURL(userId, `/${programId}/outreach-draft`), { method: 'POST' }))).draft
      setDraft(next); setWritten(next)
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const copy = async () => {
    if (!draft || busy) return
    try {
      await navigator.clipboard.writeText(draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body)
      setCopied('Copied. Nothing has been sent.')
    } catch { setCopied('Copy is not available. Select the text and copy it.') }
  }
  // "I sent it": only a date is kept, never the email text.
  const markSent = async (sent: boolean) => {
    if (!userId || busy) return
    setBusy(true); setError('')
    try {
      const result = await readJSON<{ sent_at: string | null }>(apiFetch(collegesURL(userId, `/${programId}/sent`), JSON_POST({ sent })))
      setDetail(d => d && { ...d, program: { ...d.program, sent_at: result.sent_at } })
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  // One plain address only: no commas, semicolons, % or other mailto header tricks.
  const mailto = (d: Draft) => {
    const to = /^[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/.test(d.to_email.trim()) ? d.to_email.trim() : ''
    return `mailto:${to}?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`
  }
  const field = 'mt-1 block w-full rounded-xl border border-jr-edge bg-jr-well px-4 py-3 text-sm text-jr-text focus:border-jr-lime focus:outline-none'
  const back = <Link href="/home/colleges" className={`inline-flex min-h-11 items-center text-[15px] text-jr-lime hover:text-jr-lime-hover ${focus}`}>← Colleges</Link>

  if (error && !detail) return <div className="pb-12 pt-6">{back}<p role="alert" className="mt-6 text-red-300">{error}</p></div>
  if (!detail) return <p role="status" className="py-16 text-center text-jr-muted">Loading…</p>
  const program = detail.program
  return <div className="max-w-3xl pb-12 pt-6">
    {back}
    <article className="mt-4 flex gap-4 rounded-[20px] border border-jr-line bg-jr-card p-5">
      <Badge program={program} />
      <div className="flex min-w-0 flex-1 flex-col gap-1.5">
        <div className="flex justify-between gap-3">
          <h1 className="break-words text-2xl font-bold sm:text-[28px]">{program.school}</h1>
          <HeartButton program={program} busy={save.busy === program.id} onToggle={() => void save.toggle(program)} />
        </div>
        <Meta program={program} />
        {program.conference && <p className="text-sm text-jr-muted">{program.conference}</p>}
        {program.reason && <p className="mt-2 break-words text-base leading-relaxed text-[#D4D4DA]">{program.reason}</p>}
        {program.notes && <p className="mt-2 break-words text-sm text-jr-muted">{program.notes}</p>}
        <div className="mt-1 flex flex-wrap gap-x-5"><ProgramLinks program={program} /></div>
        <p className="text-xs text-jr-dim">{program.source_checked}</p>
      </div>
    </article>
    {save.error && <p role="alert" className="mt-3 text-red-300">{save.error}</p>}
    <section aria-labelledby="draft-title" className="mt-8">
      <h2 id="draft-title" className="text-xl font-bold">Email the coach</h2>
      <p className="mt-2 text-sm text-jr-muted">SPARQ writes a draft. You read it, change it, and send it from your own email. A parent can help. SPARQ never sends it.</p>
      {error && <p role="alert" className="mt-3 text-red-300">{error}</p>}
      {!draft ? <button type="button" onClick={() => void write()} disabled={busy} className={`${primary} mt-4`}>{busy ? 'Writing…' : 'Write a draft'}</button>
        : <div className="mt-4 rounded-[20px] border border-jr-line bg-jr-card p-5">
          <label className="block text-xs uppercase tracking-wide text-jr-muted">To<input type="email" value={draft.to_email} onChange={e => setDraft({ ...draft, to_email: e.target.value })} placeholder="Add the coach's email from the school site" className={field} /></label>
          <label className="mt-3 block text-xs uppercase tracking-wide text-jr-muted">Subject<input value={draft.subject} onChange={e => setDraft({ ...draft, subject: e.target.value })} className={field} /></label>
          <label className="mt-3 block text-xs uppercase tracking-wide text-jr-muted">Email<textarea value={draft.body} onChange={e => setDraft({ ...draft, body: e.target.value })} rows={Math.max(8, draft.body.split('\n').length + 1)} className={field} /></label>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => void copy()} disabled={busy} className={primary}>Copy</button>
            <a href={mailto(draft)} className={secondary}>Open in my email</a>
            <button type="button" onClick={() => void write()} disabled={busy || confirmReplace} className={`min-h-11 px-3 text-sm text-jr-muted hover:text-white ${focus}`}>{busy ? 'Writing…' : 'Write a new draft'}</button>
          </div>
          {confirmReplace && <div role="alertdialog" aria-labelledby="replace-edits" className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-amber-200/40 p-3">
            <p id="replace-edits" className="text-sm text-amber-100">Replace your edits?</p>
            <button type="button" autoFocus onClick={() => setConfirmReplace(false)} className={secondary}>Keep my edits</button>
            <button type="button" onClick={() => void write(true)} className={secondary}>Replace</button>
          </div>}
          {copied && <p role="status" className="mt-2 text-sm text-jr-soft">{copied}</p>}
          <div className="mt-5 flex flex-wrap items-center gap-3 border-t border-jr-line pt-4">
            {program.sent_at ? <>
              <p role="status" className="text-sm font-semibold text-jr-lime">You marked this sent on {shortDate(program.sent_at)}.</p>
              <button type="button" onClick={() => void markSent(false)} disabled={busy} className={`min-h-11 px-3 text-sm text-jr-muted hover:text-white ${focus}`}>Undo</button>
            </> : <>
              <p className="text-sm text-jr-muted">Sent it from your email?</p>
              <button type="button" onClick={() => void markSent(true)} disabled={busy} className={secondary}>I sent it</button>
            </>}
          </div>
        </div>}
    </section>
    <ContactPanel rules={detail.contact_rules} />
  </div>
}
