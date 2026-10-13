'use client'

// Junior colleges (profile surface only). Sourced programs, why each fits, distance
// from her GMTM city, saves, contact rules with their sources, the coach email kit
// (copy or open in her own email) and the Emails list. SPARQ never sends. No fit score.
import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import Link from 'next/link'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'
import { badgeColors, chooseLabels, initials, mapWindow, schoolLabels } from './journey'
import { noteChecklist, openLink, plainEmail, type CheckItem, type NoteKit } from './emailKit'
import { CollegeResearchCards, useCollegeResearch } from './collegeResearch'
import { hostOf } from './collegeResearchText'

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
  similar?: CollegeProgram[]
}
export interface SavedColleges { eligible: boolean; notice: string | null; built: boolean; found: number; saved: CollegeProgram[]; saved_count: number; sent_count: number; origin: Origin | null }
interface Draft { id: number; to_email: string; school: string | null; subject: string; body: string; kit: NoteKit | null }

const https = (url: string | null | undefined): string | null => (typeof url === 'string' && url.startsWith('https://') ? url : null)
const collegesURL = (userId: string, rest = '') => `${BACKEND_URL}/api/workspace/colleges/${encodeURIComponent(userId)}${rest}`
const parentURL = (userId: string) => `${BACKEND_URL}/api/workspace/parent-contact/${encodeURIComponent(userId)}`
export const savedURL = (userId: string, rest = '') => `${BACKEND_URL}/api/workspace/saved-colleges/${encodeURIComponent(userId)}${rest}`
const JSON_POST = (body: unknown): RequestInit => ({ method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })

// Plain words for a 13-year-old. Backend detail text is never shown as is.
// 409 details the backend sends (college_programs.py), in her words.
const CONFLICT: Record<string, string> = {
  'Find your colleges first.': 'Your college list changed. Go to Colleges and tap Check my list again.',
  'Connect your GMTM profile first.': 'Open SPARQ Recruit from your GMTM profile first.',
}
const NETWORK = "We can't reach SPARQ Recruit right now. Check your internet and try again."
export async function readJSON<T>(request: Promise<Response>): Promise<T> {
  const response = await readOK(request)
  try { return await response.json() as T } catch { throw new Error('Something went wrong on our side. Try again in a minute.') }
}
async function readOK(request: Promise<Response>): Promise<Response> {
  let response: Response
  try { response = await request } catch { throw new Error(NETWORK) }
  if (!response.ok) {
    const detail = await response.json().then(body => (typeof body?.detail === 'string' ? body.detail : ''), () => '')
    throw new Error(
      detail === 'parent_notice_required' ? 'A parent needs to read the note on your home page first.'
        : response.status === 401 ? 'Your SPARQ Recruit time ran out. Open SPARQ Recruit from GMTM again.'
          : response.status === 403 ? "This part of SPARQ Recruit isn't open for your account."
            : response.status === 404 ? "We couldn't find that. Go back and try again."
              : response.status === 409 ? (CONFLICT[detail] || 'Write a draft for this college first.')
                : response.status === 429 ? "You've done this a lot in the last hour. Take a break and try again later."
                  : response.status === 502 ? "We couldn't write that just now. Try again in a minute."
                    : 'Something went wrong on our side. Try again in a minute.')
  }
  return response
}

// The build streams one JSON object per line: the list first, then each reason as it is written
// (backend college_programs.build_colleges). A plain JSON reply (e.g. not eligible) is one list.
type BuildLine = ({ type: 'list' } & CollegeList) | { type: 'reason'; id: string; reason: string | null } | { type: 'done' } | { type: 'error' }
const NOT_SAVED = 'We could not save your list. Tap Check my list again.'
async function readBuild(request: Promise<Response>, take: (line: BuildLine) => void): Promise<void> {
  const response = await readOK(request)
  if (!(response.headers.get('content-type') || '').includes('ndjson') || !response.body) {
    take({ type: 'list', ...await response.json() as CollegeList })
    return
  }
  const reader = response.body.getReader()
  const decoder = new TextDecoder()
  let buffer = ''
  let finished = false
  try {
    for (;;) {
      const { value, done } = await reader.read()
      buffer += decoder.decode(value, { stream: !done })
      const lines = buffer.split('\n')
      buffer = lines.pop() || ''
      for (const line of lines) {
        if (!line.trim()) continue
        const parsed = JSON.parse(line) as BuildLine
        if (parsed.type === 'error') throw new Error(NOT_SAVED)
        finished = finished || parsed.type === 'done'
        take(parsed)
      }
      if (done) break
    }
  } catch (e) { throw new Error((e as Error).message === NOT_SAVED ? NOT_SAVED : NETWORK) }
  if (!finished) throw new Error(NETWORK)
}

export const shortDate = (iso: string) => new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric' }).format(new Date(iso))
export const aboutMiles = (mi: number | null) => (mi === null ? null : `about ${mi} mi`)

// `label`: the list's unique label (schoolLabels) when two schools in it share initials.
export function Badge({ program, size = 'md', label }: { program: Pick<CollegeProgram, 'school' | 'primary_color'>; size?: 'sm' | 'md'; label?: string }) {
  const text = label || initials(program.school)
  const long = text.length > 2
  return <span aria-hidden="true" style={badgeColors(program.primary_color)}
    className={`flex shrink-0 items-center justify-center font-bold ${size === 'sm' ? `h-11 w-11 rounded-xl ${long ? 'text-[11px]' : 'text-sm'}` : `h-16 w-16 rounded-2xl ${long ? 'text-base' : 'text-[22px]'}`}`}>{text}</span>
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
      : program.source_links.map((url, index) => <ExternalLink key={url} href={url}>{hostOf(url) || `Source ${index + 1}`}</ExternalLink>)}
    <ExternalLink href={program.questionnaire_link}>Recruit questionnaire</ExternalLink>
  </>
}

function Meta({ program }: { program: CollegeProgram }) {
  return <p className="text-sm text-jr-muted">
    {program.city}, {program.state}{program.distance_mi !== null && <> · <b className="font-semibold text-jr-text">{aboutMiles(program.distance_mi)}</b></>} · <span className="whitespace-nowrap">{program.level}</span>
    {program.starts && <span className="ml-2 inline-block rounded-full bg-jr-track px-2.5 py-0.5 text-xs text-jr-text">{program.starts}</span>}
  </p>
}

function ProgramCard({ program, busy, onToggle, label, writing }: { program: CollegeProgram; busy: boolean; onToggle: () => void; label?: string; writing?: boolean }) {
  return <article className={`flex gap-4 rounded-[20px] bg-jr-card p-4 sm:p-[18px] ${program.saved ? 'border-2 border-jr-lime' : 'border border-jr-line'}`}>
    <Badge program={program} label={label} />
    <div className="flex min-w-0 flex-1 flex-col gap-1.5">
      <div className="flex justify-between gap-3">
        <h3 className="break-words text-lg font-bold leading-snug sm:text-xl">{program.school}</h3>
        <HeartButton program={program} busy={busy} onToggle={onToggle} />
      </div>
      <Meta program={program} />
      {program.reason ? <p className="mt-1 break-words text-[15px] leading-normal text-[#D4D4DA]">{program.reason}</p>
        : writing && <p aria-hidden="true" className="mt-1 text-[15px] italic text-jr-muted motion-safe:animate-pulse">Writing why it fits you…</p>}
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
function CollegeMap({ programs, origin, labels }: { programs: CollegeProgram[]; origin: Origin | null; labels: Record<string, string> }) {
  const placed = programs.filter(p => p.map)
  const view = mapWindow([...placed.map(p => p.map!), ...(origin?.map ? [origin.map] : [])])
  // Percent of the whole map -> percent of the visible window.
  const at = (m: { x: number; y: number }) => ({ left: `${((m.x - view.x) / view.w) * 100}%`, top: `${((m.y - view.y) / view.h) * 100}%` })
  // Up to 4 text labels, none on another label or on the "You" pin and its text; the rest are dots.
  const labelled = chooseLabels(placed, origin?.map || null, view)
  return <div className="flex flex-col overflow-hidden rounded-3xl border border-jr-line bg-[#101318]">
    <div className="relative aspect-[8/5] w-full overflow-hidden">
      <img src="/us-states.svg" alt="" aria-hidden="true" className="absolute max-w-none"
        style={{ width: `${10000 / view.w}%`, height: `${10000 / view.h}%`, left: `${(-view.x / view.w) * 100}%`, top: `${(-view.y / view.h) * 100}%` }} />
      <ul aria-label="Colleges on the map">
        {/* Labels sit above the dots, so a nearby dot never covers a label's text. */}
        {placed.map(p => <li key={p.id} className={`absolute -translate-x-1/2 -translate-y-1/2 ${labelled.includes(p) ? 'z-10' : ''}`} style={at(p.map!)}>
          <Link href={`/home/colleges/${p.id}`} aria-label={`${p.school}${p.distance_mi !== null ? `, ${aboutMiles(p.distance_mi)}` : ''}`}
            style={badgeColors(p.primary_color)} className={`block rounded-lg font-bold shadow ${focus} ${labelled.includes(p) ? 'px-2 py-1 text-xs' : 'h-3 w-3 rounded-full ring-2 ring-[#101318]'}`}>
            {labelled.includes(p) ? `${labels[p.school] || initials(p.school)}${p.distance_mi !== null ? ` · ${p.distance_mi} mi` : ''}` : ''}
          </Link>
        </li>)}
      </ul>
      {origin?.map && <div className="pointer-events-none absolute z-20 -translate-x-1/2 -translate-y-1/2" style={at(origin.map)}>
        <span className="block h-4 w-4 rounded-full bg-jr-lime shadow-[0_0_0_8px_rgba(202,253,0,0.18)]" />
        <span className="absolute left-6 top-[-2px] text-[13px] font-semibold text-jr-lime">You</span>
      </div>}
      {placed.length > labelled.length && <span className="absolute bottom-3 right-3 z-30 rounded-lg bg-jr-track px-2.5 py-1 text-xs font-semibold">+{placed.length - labelled.length} more</span>}
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
// Shown until the list arrives (about 1 s: GMTM reads and ranking). Reasons then fill in card by card.
function FindingColleges() {
  // The tapped button unmounts; move focus here so keyboard and screen reader users are not dropped.
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => ref.current?.focus(), [])
  return <div ref={ref} tabIndex={-1} className="mt-6 flex items-center gap-4 rounded-[20px] border border-jr-line bg-jr-card p-6 outline-none">
    <span aria-hidden="true" className="h-7 w-7 shrink-0 rounded-full border-[3px] border-jr-edge border-t-jr-lime motion-safe:animate-spin" />
    <p role="status" className="font-semibold text-jr-text">Finding programs that fit you…</p>
  </div>
}

// Her 3 taps (option B). Only facts we have; the server filters with the same values (college_programs.Prefs).
interface Prefs { distance: 'near' | 'region' | 'anywhere'; school: '4' | '2' | 'either'; level: 'ncaa' | 'naia' | 'any' }
const NO_PREFS: Prefs = { distance: 'anywhere', school: 'either', level: 'any' }
const QUESTIONS: Array<{ key: keyof Prefs; ask: string; options: Array<[string, string]> }> = [
  { key: 'distance', ask: 'How far from home?', options: [['near', 'Near me (300 mi)'], ['region', 'My part of the country'], ['anywhere', 'Anywhere']] },
  { key: 'school', ask: 'What kind of college?', options: [['4', '4-year'], ['2', '2-year (NJCAA)'], ['either', 'Either']] },
  { key: 'level', ask: 'Which level?', options: [['ncaa', 'NCAA'], ['naia', 'NAIA'], ['any', 'Either']] },
]
// Per athlete and per device (a convenience): null when this device has not seen her answers.
const prefsKey = (userId: string) => `sparq-college-prefs:${userId}`
function loadPrefs(userId: string): Prefs | null {
  try {
    const saved = JSON.parse(localStorage.getItem(prefsKey(userId)) || 'null')
    return QUESTIONS.every(q => q.options.some(([value]) => value === saved?.[q.key])) ? saved as Prefs : null
  } catch { return null }
}
const summary = (prefs: Prefs) => QUESTIONS.filter(q => q.key !== 'level' || prefs.school === '4')
  .map(q => q.options.find(([value]) => value === prefs[q.key])![1]).join(' · ')

function Answers({ prefs, onChange }: { prefs: Prefs; onChange: (next: Prefs) => void }) {
  return <div className="flex flex-col gap-4">
    {QUESTIONS.filter(q => q.key !== 'level' || prefs.school === '4').map(q => <div key={q.key} role="group" aria-label={q.ask}>
      <p className="mb-2 text-[15px] font-semibold text-jr-text">{q.ask}</p>
      <div className="flex flex-wrap gap-2">
        {q.options.map(([value, label]) => <button key={value} type="button" aria-pressed={prefs[q.key] === value}
          onClick={() => onChange({ ...prefs, [q.key]: value })} className={chip(prefs[q.key] === value)}>{label}</button>)}
      </div>
    </div>)}
  </div>
}

const LEVELS: Level[] = ['All', 'NCAA', 'NAIA', 'NJCAA']
const NEAR_MI = 150
const PAGE = 24
const seg = (on: boolean) => `inline-flex min-h-11 flex-1 items-center justify-center rounded-full px-5 text-[15px] sm:flex-none ${focus} ${on ? 'bg-jr-lime font-bold text-jr-ground' : 'text-[#D4D4DA] hover:text-white'}`
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
  // "See all" (Joey 2026-10-13): her 12 first, every sourced program one tap away. No model call.
  const [view, setView] = useState<'mine' | 'all'>('mine')
  const [all, setAll] = useState<CollegeList | null>(null)
  const [search, setSearch] = useState('')
  const [limit, setLimit] = useState(PAGE)
  const [loadingAll, setLoadingAll] = useState(false)
  const [prefs, setPrefs] = useState<Prefs>(NO_PREFS)
  // The answers her list was built from, if this device knows them.
  const [builtFrom, setBuiltFrom] = useState<Prefs | null>(null)
  const [editing, setEditing] = useState(false)
  // Program ids whose reason is still being written in this build.
  const [writing, setWriting] = useState<string[]>([])
  const heading = useRef<HTMLHeadingElement>(null)
  // Leaving the page stops the build (the server then saves nothing), so a quick return cannot double-build.
  const stop = useRef<AbortController | null>(null)
  useEffect(() => () => stop.current?.abort(), [])
  const userId = user?.id

  useEffect(() => { if (userId) { const saved = loadPrefs(userId); setBuiltFrom(saved); setPrefs(saved || NO_PREFS) } }, [userId])

  useEffect(() => {
    if (!userId) return
    let live = true
    readJSON<CollegeList>(apiFetch(collegesURL(userId))).then(body => { if (live) setList(body) }, e => { if (live) setError(e.message) })
    return () => { live = false }
  }, [userId])

  const build = useCallback(async () => {
    if (!userId) return
    setBusy(true); setError('')
    const controller = new AbortController()
    stop.current = controller
    try {
      await readBuild(apiFetch(`${BACKEND_URL}/api/workspace/trigger-matching/${encodeURIComponent(userId)}`, {
        method: 'POST', headers: { Accept: 'application/x-ndjson', 'Content-Type': 'application/json' }, body: JSON.stringify(prefs), signal: controller.signal,
      }), line => {
        if (line.type === 'list') {
          const { type: _, ...next } = line
          // Nothing matches: keep her last list on screen (the server did not replace it either).
          if (next.eligible && !next.programs.length) { setError('No programs match those answers. Try Anywhere or Either.'); return }
          try { localStorage.setItem(prefsKey(userId), JSON.stringify(prefs)) } catch { /* a convenience only */ }
          setBuiltFrom(prefs)
          setList(next)
          setAll(null); setView('mine'); setEditing(false)  // the full list carries her 12's reasons: refetch after a rebuild
          setWriting(next.programs.filter(p => !p.reason).map(p => p.id))
          if (next.built) requestAnimationFrame(() => heading.current?.focus())
        } else if (line.type === 'reason') {
          setList(current => current && { ...current, programs: current.programs.map(p => (p.id === line.id ? { ...p, reason: line.reason } : p)) })
          setWriting(ids => ids.filter(id => id !== line.id))
        }
      })
    } catch (e) { if (!controller.signal.aborted) setError((e as Error).message) } finally { setBusy(false); setWriting([]) }
  }, [userId, prefs])

  const apply = useCallback((id: string, saved: boolean) => {
    const mark = (current: CollegeList | null) => {
      if (!current) return current
      const changed = current.programs.some(p => p.id === id && p.saved !== saved)
      // A college outside her 12 still counts in her 12's "Saved (n)".
      const outside = !current.programs.some(p => p.id === id)
      return { ...current, saved_count: current.saved_count + (changed || outside ? (saved ? 1 : -1) : 0), programs: current.programs.map(p => (p.id === id ? { ...p, saved } : p)),
        similar: current.similar?.map(p => (p.id === id ? { ...p, saved } : p)) }
    }
    setList(mark); setAll(mark)
  }, [])
  const save = useSave(userId, apply)

  const openAll = useCallback(async () => {
    setView('all'); setLimit(PAGE)
    if (all || !userId || loadingAll) return
    setLoadingAll(true); setError('')
    try { setAll(await readJSON<CollegeList>(apiFetch(collegesURL(userId, '/all')))) } catch (e) { setError((e as Error).message); setView('mine') } finally { setLoadingAll(false) }
  }, [all, userId, loadingAll])

  const current = view === 'all' && all ? all : list
  const showingAll = view === 'all' && !!all
  const words = search.trim().toLowerCase()
  const shown = useMemo(() => (current?.programs || []).filter(p =>
    (level === 'All' || p.level.startsWith(level)) && (!near || (p.distance_mi !== null && p.distance_mi <= NEAR_MI)) && (!savedOnly || p.saved)
    && (!showingAll || !words || `${p.school} ${p.city} ${p.state} ${p.conference || ''}`.toLowerCase().includes(words))), [current, level, near, savedOnly, words, showingAll])
  const hasDistances = !!current?.programs.some(p => p.distance_mi !== null)
  // Same labels as the map, so a badge and its map pin match (e.g. DSC / DSU, not DS twice).
  const labels = useMemo(() => schoolLabels([...(current?.programs || []), ...(current?.similar || [])].map(p => p.school)), [current])
  // The map shows the same colleges as the cards (one page of the full list, not all 187 pins).
  const page = showingAll ? shown.slice(0, limit) : shown

  if (!isLoaded || (!list && !error)) return <p role="status" className="py-16 text-center text-jr-muted">Loading your colleges…</p>
  return <div className="pb-12 pt-8">
    <div className="flex flex-col gap-5 lg:flex-row lg:items-end lg:justify-between">
      <div>
        <h1 ref={heading} tabIndex={-1} className="text-[34px] font-bold leading-tight tracking-[-1px] outline-none sm:text-[44px]">College flag football</h1>
        {list?.eligible && list.built && <p className="mt-2 text-[17px] text-jr-soft">{showingAll
          ? `All ${all!.programs.length} college flag football programs we track. ${hasDistances ? 'Closest first. ' : ''}Tap the heart to save.`
          : `${list.programs.length} programs to start with. ${hasDistances ? 'Closest first. ' : ''}Tap the heart to save.`}</p>}
        {writing.length > 0 && list?.programs.length ? <p className="mt-1 text-[15px] text-jr-muted"><span role="status">Writing why each one fits you…</span> <span aria-hidden="true">{list.programs.length - writing.length} of {list.programs.length} done</span></p> : null}
      </div>
      {list?.eligible && list.built && list.programs.length > 0 && <div className="flex flex-col gap-3 lg:items-end">
      <div role="group" aria-label="Which colleges" className="flex w-full rounded-full border border-jr-edge p-1 sm:w-auto">
        <button type="button" aria-pressed={!showingAll} onClick={() => setView('mine')} className={`${seg(!showingAll)}`}>My {list.programs.length}</button>
        <button type="button" aria-pressed={showingAll} onClick={() => void openAll()} disabled={loadingAll} className={`${seg(showingAll)}`}>{loadingAll ? 'Loading…' : `See all${all ? ` ${all.programs.length}` : ''}`}</button>
      </div>
      <div role="group" aria-label="Filter colleges" className="flex flex-wrap gap-2">
        {LEVELS.map(l => <button key={l} type="button" aria-pressed={level === l} onClick={() => setLevel(l)} className={chip(level === l)}>{l === 'All' ? 'All levels' : l === 'NJCAA' ? 'NJCAA (2-year)' : l}</button>)}
        {hasDistances && <button type="button" aria-pressed={near} onClick={() => setNear(v => !v)} className={chip(near)}>Within {NEAR_MI} mi</button>}
        <button type="button" aria-pressed={savedOnly} onClick={() => setSavedOnly(v => !v)} className={chip(savedOnly)}>Saved ({showingAll ? all!.saved_count : list.programs.filter(p => p.saved).length})</button>
      </div>
      {showingAll && <label className="w-full text-sm text-jr-muted">Search by school, city or state
        <input type="search" value={search} onChange={e => { setSearch(e.target.value); setLimit(PAGE) }} placeholder="e.g. Ottawa or TX"
          className={`mt-1.5 block min-h-11 w-full rounded-xl border border-jr-edge bg-jr-well px-4 text-base text-jr-text placeholder:text-jr-dim ${focus}`} />
      </label>}
      </div>}
    </div>
    {loadingAll && <p role="status" className="mt-4 text-jr-muted">Loading all colleges…</p>}
    {error && <p role="alert" className="mt-4 text-red-300">{error}</p>}
    {save.error && <p role="alert" className="mt-4 text-red-300">{save.error}</p>}
    {list && !list.eligible ? <div className="mt-6"><NotEligible notice={list.notice} busy={busy} onCheck={() => void build()} /></div>
      : list && <>
        {/* First build only: a rebuild is usually a cache hit and keeps its in-place "Checking…". */}
        {busy && !list.built && <FindingColleges />}
        {!list.built && !busy && <div className="mt-6 rounded-[20px] border border-jr-line bg-jr-card p-6">
          <p className="max-w-2xl text-jr-soft">Tap your answers. We pick up to 12 programs that match and tell you why each one could fit. Each one comes from a school, conference or governing body page.</p>
          <div className="mt-5"><Answers prefs={prefs} onChange={setPrefs} /></div>
          <button type="button" onClick={() => void build()} className={`${primary} mt-6`}>Find my colleges</button>
        </div>}
        {list.built && !showingAll && <div className="mt-6 rounded-[20px] border border-jr-line bg-jr-card p-4 sm:p-5">
          {editing ? <>
            <Answers prefs={prefs} onChange={setPrefs} />
            <div className="mt-5 flex flex-wrap gap-3">
              <button type="button" onClick={() => void build()} disabled={busy} className={primary}>{busy ? 'Updating…' : 'Update my list'}</button>
              <button type="button" onClick={() => { setPrefs(builtFrom || NO_PREFS); setEditing(false) }} className={secondary}>Cancel</button>
            </div>
          </> : <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-[15px] text-jr-soft">{builtFrom ? <><span className="font-semibold text-jr-text">Your answers: </span>{summary(builtFrom)}</> : 'Pick how far, what kind of college and which level.'}</p>
            <button type="button" onClick={() => setEditing(true)} className={secondary}>Change my answers</button>
          </div>}
          {builtFrom && list.programs.length < 12 && !editing && <p className="mt-3 text-[15px] text-jr-muted">Only {list.programs.length} {list.programs.length === 1 ? 'program matches' : 'programs match'} your answers. Pick Anywhere or Either to see more, or tap See all.</p>}
        </div>}
        {list.built && !list.programs.length && <p className="mt-6 text-jr-muted">No programs to show right now.</p>}
        {list.built && list.programs.length > 0 && <>
          <button type="button" aria-expanded={mapOpen} aria-controls="college-map" onClick={() => setMapOpen(v => !v)} className={`${secondary} mt-6 w-full md:hidden`}>{mapOpen ? 'Hide map' : 'Show map'}</button>
          <div className="mt-4 grid items-start gap-6 md:mt-6 md:grid-cols-2">
            <div className="flex flex-col gap-3.5">
              {page.length ? page.map(program => <ProgramCard key={program.id} program={program} writing={writing.includes(program.id)} label={labels[program.school]} busy={save.busy === program.id} onToggle={() => void save.toggle(program)} />)
                : <p className="rounded-[20px] border border-jr-line bg-jr-card p-6 text-jr-soft">{savedOnly ? 'No saved colleges yet. Tap a heart to save one.' : 'No colleges match these filters.'}</p>}
              {showingAll && shown.length > limit && <button type="button" onClick={() => setLimit(n => n + PAGE)} className={secondary}>Show more ({shown.length - limit} left)</button>}
            </div>
            <div id="college-map" className={`${mapOpen ? 'block' : 'hidden'} order-first md:sticky md:top-6 md:order-none md:block`}>
              <CollegeMap programs={page} origin={list.origin} labels={labels} />
            </div>
          </div>
          {!showingAll && !!list.similar?.length && <section aria-labelledby="similar-title" className="mt-8">
            <h2 id="similar-title" className="text-xl font-bold">More like the ones you saved</h2>
            <p className="mt-1 text-[15px] text-jr-muted">Same level, closest to the colleges you saved.</p>
            <div className="mt-4 grid gap-3.5 md:grid-cols-2">
              {list.similar.map(program => <ProgramCard key={program.id} program={program} label={labels[program.school]} busy={save.busy === program.id} onToggle={() => void save.toggle(program)} />)}
            </div>
          </section>}
          {!showingAll && <div className="mt-6 flex flex-wrap gap-3">
            <button type="button" onClick={() => void openAll()} disabled={loadingAll} className={secondary}>{loadingAll ? 'Loading…' : 'See all colleges'}</button>
            <button type="button" onClick={() => void build()} disabled={busy} className={secondary}>{busy ? 'Checking…' : 'Check my list again'}</button>
          </div>}
        </>}
        <ContactPanel rules={(current || list).contact_rules} />
      </>}
  </div>
}

// Sourced coach contact (detail route only). Never guessed: empty when the program data has none.
interface Coach { names: string[]; last_name: string | null; role: string | null; email: string | null; staff_page_url: string | null; source_checked: string | null }
interface Detail { program: CollegeProgram; coach: Coach; contact_rules: ContactRules[] }

function Check({ item }: { item: CheckItem }) {
  return <li className={`flex gap-2.5 text-[15px] ${item.done ? 'text-[#D4D4DA]' : 'text-jr-dim'}`}>
    <span aria-hidden="true" className={item.done ? 'text-jr-lime' : ''}>{item.done ? '✓' : '○'}</span>
    <span>{item.label}<span className="sr-only">{item.done ? ' (in your note)' : ' (not in your note)'}</span></span>
  </li>
}

// The coach email kit: To (sourced coach address), CC my parent, subject and note from SPARQ's
// draft, then Open in my email / Copy / I sent it. SPARQ never sends.
export function ProfileCollegeDetail({ programId }: { programId: string }) {
  const { user } = useSparqSession()
  const userId = user?.id
  const [detail, setDetail] = useState<Detail | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  // The draft as SPARQ wrote it; any difference means the athlete edited it.
  const [written, setWritten] = useState<Draft | null>(null)
  const [to, setTo] = useState('')
  const [parent, setParent] = useState('')
  const [savedParent, setSavedParent] = useState('')
  const [cc, setCc] = useState(false)
  const [parentNote, setParentNote] = useState('')
  const [confirmReplace, setConfirmReplace] = useState(false)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [copied, setCopied] = useState('')
  const [saveBusy, setSaveBusy] = useState(false)
  // Fetch research only once a save has reached the server (not during the optimistic flip).
  const research = useCollegeResearch(userId, programId, !!detail?.program.saved && !saveBusy)

  useEffect(() => {
    if (!userId) return
    let live = true
    Promise.all([
      readJSON<Detail>(apiFetch(collegesURL(userId, `/${programId}`))),
      readJSON<{ draft: Draft | null }>(apiFetch(collegesURL(userId, `/${programId}/outreach-draft`))),
      // CC is optional: if the parent address cannot be read, the kit still works.
      readJSON<{ email: string | null }>(apiFetch(parentURL(userId))).catch(() => ({ email: null })),
    ]).then(([d, saved, p]) => {
      if (!live) return
      setDetail(d); setDraft(saved.draft); setWritten(saved.draft)
      setTo(saved.draft?.to_email || d.coach.email || '')
      setParent(p.email || ''); setSavedParent(p.email || ''); setCc(!!p.email)
    }, e => { if (live) setError(e.message) })
    return () => { live = false }
  }, [userId, programId])

  const applySaved = useCallback((id: string, saved: boolean) => setDetail(d => d && d.program.id === id ? { ...d, program: { ...d.program, saved } } : d), [])
  const save = useSave(userId, applySaved)
  useEffect(() => setSaveBusy(save.busy === programId), [save.busy, programId])
  const edited = !!draft && !!written && (draft.subject !== written.subject || draft.body !== written.body)
  const write = async (replace = false) => {
    if (!userId || busy) return
    if (edited && !replace) { setConfirmReplace(true); return }
    setConfirmReplace(false); setBusy(true); setError(''); setCopied('')
    try {
      const next = (await readJSON<{ draft: Draft }>(apiFetch(collegesURL(userId, `/${programId}/outreach-draft`), { method: 'POST' }))).draft
      setDraft(next); setWritten(next)
      setTo(current => current || next.to_email)
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  const copy = async () => {
    if (!draft || busy) return
    try {
      await navigator.clipboard.writeText(draft.subject ? `Subject: ${draft.subject}\n\n${draft.body}` : draft.body)
      setCopied('Copied. Nothing has been sent.')
    } catch { setCopied('Copy is not available. Select the text and copy it.') }
  }
  // "I sent it": only a date is kept, never the email text. Needs a draft first.
  const markSent = async (sent: boolean) => {
    if (!userId || busy || !draft) return
    setBusy(true); setError('')
    try {
      const result = await readJSON<{ sent_at: string | null }>(apiFetch(collegesURL(userId, `/${programId}/sent`), JSON_POST({ sent })))
      setDetail(d => d && { ...d, program: { ...d.program, sent_at: result.sent_at } })
    } catch (e) { setError((e as Error).message) } finally { setBusy(false) }
  }
  // Only the address is stored, per athlete. Saved when she leaves the field.
  const saveParent = async () => {
    const value = parent.trim()
    if (!userId || value === savedParent) return
    if (value && !plainEmail(value)) { setParentNote('Enter one email address, like parent@example.com.'); return }
    try {
      const result = await readJSON<{ email: string | null }>(apiFetch(parentURL(userId), JSON_POST({ email: value })))
      setSavedParent(result.email || ''); setParentNote(result.email ? 'Saved for your next emails.' : 'Removed.')
    } catch (e) { setParentNote((e as Error).message) }
  }

  const field = 'w-full rounded-xl border border-jr-edge bg-[#0F0F12] p-3.5 text-base font-medium text-jr-text focus:border-jr-lime focus:outline-none'
  const label = 'flex flex-col gap-1.5 text-sm text-jr-muted'
  const back = <Link href="/home/colleges" className={`inline-flex min-h-11 items-center self-start text-[15px] text-jr-lime hover:text-jr-lime-hover ${focus}`}>← Colleges</Link>

  if (error && !detail) return <div className="pb-12 pt-6">{back}<p role="alert" className="mt-6 text-red-300">{error}</p></div>
  if (!detail) return <p role="status" className="py-16 text-center text-jr-muted">Loading…</p>
  const { program, coach } = detail
  const ccAddress = cc ? plainEmail(parent) : ''
  const toValid = !to.trim() || !!plainEmail(to)
  // An empty To would open her email app with no recipient.
  const hasTo = !!plainEmail(to)
  const checklist = noteChecklist(draft ? `${draft.subject}\n${draft.body}` : '', draft?.kit || null, ccAddress)
  const rules = detail.contact_rules[0]
  const open = draft ? openLink({ to, cc: ccAddress, subject: draft.subject, body: draft.body }) : null
  return <div className="grid items-start gap-7 pb-12 pt-6 lg:grid-cols-[minmax(0,1.5fr)_minmax(0,1fr)]">
    <section aria-labelledby="kit-title" className="flex min-w-0 flex-col gap-[18px]">
      {back}
      <div className="flex items-center gap-4">
        <Badge program={program} />
        <div className="flex min-w-0 flex-1 flex-col gap-1">
          <h1 id="kit-title" className="break-words text-[28px] font-bold leading-tight sm:text-[32px]">{coach.last_name ? `Email Coach ${coach.last_name}` : 'Email the coach'}</h1>
          <p className="text-[15px] text-jr-muted">
            {coach.names.length === 1 ? `${coach.role} · ${program.school}`
              : coach.names.length > 1 ? `${coach.role}: ${coach.names.join(' and ')} · ${program.school}` : program.school}
          </p>
          {!coach.names.length && <ExternalLink href={coach.staff_page_url}>Find the coach on the staff page</ExternalLink>}
        </div>
        <HeartButton program={program} busy={save.busy === program.id} onToggle={() => void save.toggle(program)} />
      </div>
      {save.error && <p role="alert" className="text-red-300">{save.error}</p>}

      <div className="flex flex-col gap-4 rounded-[20px] border border-jr-line bg-jr-card p-4 sm:p-[22px]">
        <label className={label}>To
          <input type="email" value={to} onChange={e => setTo(e.target.value)} placeholder="Add the coach's email from the staff page"
            aria-invalid={!toValid} aria-describedby="to-help" autoComplete="off" className={field} />
        </label>
        <p id="to-help" className="-mt-2 text-xs text-jr-dim">
          {!toValid ? 'Use one email address, like coach@school.edu.'
            : coach.email && coach.source_checked ? <>From the school&apos;s staff page. {coach.source_checked}. </> : hasTo ? '' : 'Add the coach’s email first. '}
          {coach.staff_page_url && <a href={coach.staff_page_url} target="_blank" rel="noopener noreferrer" className={`underline underline-offset-4 ${focus}`}>Staff page<span className="sr-only"> (opens in a new tab)</span></a>}
        </p>
        <div className="flex flex-col gap-2">
          <label className="flex min-h-11 items-center gap-2.5 text-[15px] text-[#D4D4DA]">
            <input type="checkbox" checked={cc} onChange={e => setCc(e.target.checked)} className="h-5 w-5 accent-jr-lime" />
            CC my parent{cc && ccAddress ? ` (${ccAddress})` : ''}
          </label>
          {cc && <label className={label}>Parent&apos;s email
            <input type="email" value={parent} onChange={e => { setParent(e.target.value); setParentNote('') }} onBlur={() => void saveParent()}
              placeholder="parent@example.com" autoComplete="off" aria-describedby="parent-help" className={field} />
            <span id="parent-help" role="status" className="text-xs text-jr-dim">{parentNote || 'Saved in SPARQ Recruit only for your CC line. SPARQ Recruit never emails your parent.'}</span>
          </label>}
        </div>
        {draft ? <>
          <label className={label}>Subject<input value={draft.subject} onChange={e => setDraft({ ...draft, subject: e.target.value })} className={field} /></label>
          <label className={label}>Your note<textarea value={draft.body} onChange={e => setDraft({ ...draft, body: e.target.value })} rows={Math.max(9, draft.body.split('\n').length + 1)} className={`${field} resize-y font-normal leading-[1.55]`} /></label>
        </> : <div className="rounded-xl border border-dashed border-jr-edge p-4">
          <p className="text-[15px] text-jr-soft">SPARQ Recruit writes a short note from your GMTM profile: your highlights first, then your best numbers. You read it and change anything.</p>
          <button type="button" onClick={() => void write()} disabled={busy} className={`${primary} mt-4`}>{busy ? 'Writing…' : 'Write my note'}</button>
        </div>}
        {error && <p role="alert" className="text-red-300">{error}</p>}
        {open?.long && <p role="status" className="rounded-xl border border-amber-200/40 p-3 text-sm text-amber-100">Your note is long. Use Copy, then open your email and paste it.</p>}
        <div className="flex flex-wrap items-center gap-2.5">
          {open?.long && <button type="button" onClick={() => void copy()} disabled={busy} className={primary}>Copy</button>}
          {open && hasTo ? <a href={open.href} className={open.long ? `${secondary} min-h-12 px-[22px] text-base` : primary}>Open in my email</a>
            : <button type="button" disabled className={primary}>Open in my email</button>}
          {!open?.long && <button type="button" onClick={() => void copy()} disabled={busy || !draft} className={`${secondary} min-h-12 px-[22px] text-base`}>Copy</button>}
          {program.sent_at ? <span className="inline-flex min-h-12 items-center gap-2 rounded-xl border border-jr-done-line bg-jr-done px-4 text-base font-semibold text-jr-lime">
            <span role="status">Sent {shortDate(program.sent_at)} ✓</span>
            <button type="button" onClick={() => void markSent(false)} disabled={busy} className={`min-h-11 px-2 text-sm font-normal text-jr-muted underline hover:text-white ${focus}`}>Undo</button>
          </span> : <button type="button" onClick={() => void markSent(true)} disabled={busy || !draft}
            className={`inline-flex min-h-12 items-center rounded-xl border border-jr-done-line bg-jr-done px-[22px] text-base font-semibold text-jr-lime disabled:cursor-not-allowed disabled:opacity-50 ${focus}`}>I sent it ✓</button>}
          {draft && <button type="button" onClick={() => void write()} disabled={busy || confirmReplace} className={`min-h-11 px-3 text-sm text-jr-muted hover:text-white ${focus}`}>{busy ? 'Writing…' : 'Write a new draft'}</button>}
        </div>
        {confirmReplace && <div role="alertdialog" aria-labelledby="replace-edits" className="flex flex-wrap items-center gap-3 rounded-xl border border-amber-200/40 p-3">
          <p id="replace-edits" className="text-sm text-amber-100">Replace your edits?</p>
          <button type="button" autoFocus onClick={() => setConfirmReplace(false)} className={secondary}>Keep my edits</button>
          <button type="button" onClick={() => void write(true)} className={secondary}>Replace</button>
        </div>}
        {copied && <p role="status" className="text-sm text-jr-soft">{copied}</p>}
        <p className="text-sm text-jr-dim">SPARQ Recruit never sends for you. You send it from your own email.</p>
      </div>
    </section>

    <aside className="flex flex-col gap-4 lg:pt-11">
      <div className="flex flex-col gap-3 rounded-[20px] border border-jr-line bg-jr-card p-5">
        <h2 className="text-lg font-bold">What&apos;s in your note</h2>
        {draft ? <ul className="flex flex-col gap-2.5">{checklist.map(item => <Check key={item.label} item={item} />)}</ul>
          : <p className="text-[15px] text-jr-soft">Write your note to see what it includes.</p>}
      </div>
      {rules && <div className="flex flex-col gap-2.5 rounded-[20px] border border-jr-line bg-jr-card p-5">
        <h2 className="text-lg font-bold">When coaches can reply</h2>
        <p className="text-sm text-jr-muted">{rules.level} rules. If a coach does not answer yet, it can be a rule, not a no.</p>
        <ul className="flex flex-col gap-2 text-[15px] leading-normal text-[#D4D4DA]">
          {rules.rules.map(rule => <li key={rule.text}>{rule.text}{rule.source_url && <> <ExternalLink href={rule.source_url}>{rule.source_label || 'Source'}</ExternalLink></>}</li>)}
        </ul>
      </div>}
      {research && program.saved && <CollegeResearchCards research={research} school={program.school} />}
      <div className="flex flex-col gap-1.5 rounded-[20px] border border-jr-done-line bg-jr-done p-5">
        <span className="text-[15px] font-bold text-jr-lime">Tip</span>
        <p className="text-[15px] leading-normal text-[#E4E4E7]">Short notes get read. {program.questionnaire_link
          ? <>Fill in the questionnaire too: <ExternalLink href={program.questionnaire_link}>{program.school} questionnaire</ExternalLink></>
          : 'Lead with your highlights. Coaches watch film first.'}</p>
      </div>
      <div className="flex flex-wrap gap-x-5 px-1"><ProgramLinks program={program} /></div>
      <p className="px-1 text-xs text-jr-dim">{program.source_checked}</p>
    </aside>
  </div>
}

interface EmailRow { id: string; school: string; city: string; state: string; level: string; primary_color: string | null; status: 'draft' | 'sent'; drafted_at: string | null; sent_at: string | null }

// Emails tab: every college she has a note for, waiting ones first, each opening its kit.
export function ProfileEmails() {
  const { user, isLoaded } = useSparqSession()
  const [data, setData] = useState<{ eligible: boolean; notice: string | null; emails: EmailRow[] } | null>(null)
  const [error, setError] = useState('')
  const userId = user?.id
  useEffect(() => {
    if (!userId) return
    let live = true
    readJSON<{ eligible: boolean; notice: string | null; emails: EmailRow[] }>(apiFetch(`${BACKEND_URL}/api/workspace/college-emails/${encodeURIComponent(userId)}`))
      .then(body => { if (live) setData(body) }, e => { if (live) setError(e.message) })
    return () => { live = false }
  }, [userId])

  const emailLabels = useMemo(() => schoolLabels((data?.emails || []).map(r => r.school)), [data])
  if (!isLoaded || (!data && !error)) return <p role="status" className="py-16 text-center text-jr-muted">Loading your emails…</p>
  return <div className="max-w-3xl pb-12 pt-8">
    <h1 className="text-[34px] font-bold leading-tight tracking-[-1px] sm:text-[44px]">Emails</h1>
    {error && <p role="alert" className="mt-4 text-red-300">{error}</p>}
    {data && !data.eligible && <p role="status" className="mt-6 rounded-[20px] border border-jr-line bg-jr-card p-6 text-lg">{data.notice}</p>}
    {data?.eligible && (data.emails.length ? <>
      <p className="mt-2 text-[17px] text-jr-soft">Your notes to coaches. SPARQ Recruit never sends them; you send each one from your own email.</p>
      <ul className="mt-6 flex flex-col gap-3">
        {data.emails.map(row => <li key={row.id}>
          <Link href={`/home/colleges/${row.id}`} className={`flex items-center gap-4 rounded-[20px] border border-jr-line bg-jr-card p-4 hover:border-jr-edge ${focus}`}>
            <Badge program={row} size="sm" label={emailLabels[row.school]} />
            <span className="flex min-w-0 flex-1 flex-col gap-0.5">
              <span className="break-words text-lg font-bold leading-snug">{row.school}</span>
              <span className="text-sm text-jr-muted">{row.city}, {row.state} · <span className="whitespace-nowrap">{row.level}</span></span>
            </span>
            {row.status === 'sent' && row.sent_at
              ? <span className="shrink-0 rounded-full bg-jr-done px-3 py-1 text-sm font-semibold text-jr-lime">Sent on {shortDate(row.sent_at)}</span>
              : <span className="shrink-0 rounded-full border border-jr-edge px-3 py-1 text-sm font-semibold text-jr-text">Draft</span>}
          </Link>
        </li>)}
      </ul>
    </> : <div className="mt-6 rounded-[20px] border border-jr-line bg-jr-card p-6">
      <p className="text-jr-soft">No emails yet. Pick a college and SPARQ Recruit writes your first note.</p>
      <Link href="/home/colleges" className={`${primary} mt-5`}>Find a college</Link>
    </div>)}
  </div>
}
