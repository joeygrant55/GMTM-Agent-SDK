'use client'

// Junior colleges (profile surface only). Sourced programs, why each fits, contact
// rules with their sources, and a draft the athlete copies or opens in her own
// email. SPARQ never sends. No fit score is shown or received.
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const primary = `inline-flex min-h-12 items-center justify-center rounded-xl bg-sparq-lime px-6 py-3 text-sm font-bold text-sparq-charcoal hover:bg-sparq-lime-light disabled:cursor-wait disabled:opacity-50 ${focus}`
const secondary = `inline-flex min-h-11 items-center justify-center rounded-xl border border-white/20 px-4 py-2 text-sm font-semibold hover:border-white/40 disabled:cursor-wait disabled:opacity-50 ${focus}`
const textLink = `inline-flex min-h-11 items-center text-sm text-sparq-lime underline underline-offset-4 hover:text-white ${focus}`

export interface CollegeProgram {
  id: string; school: string; city: string; state: string; governing_body: string; level: string
  conference: string | null; program_link: string | null; program_link_label: string; source_links: string[]
  questionnaire_link: string | null; source_checked: string; notes: string | null; reason: string | null
}
export interface ContactRules { governing_body: string; level: string; rules: Array<{ text: string; source_url: string | null; source_label: string | null }> }
export interface CollegeList { eligible: boolean; notice: string | null; built: boolean; programs: CollegeProgram[]; contact_rules: ContactRules[] }
interface Draft { id: number; to_email: string; school: string | null; subject: string; body: string }

const https = (url: string | null | undefined): string | null => (typeof url === 'string' && url.startsWith('https://') ? url : null)
const collegesURL = (userId: string, rest = '') => `${BACKEND_URL}/api/workspace/colleges/${encodeURIComponent(userId)}${rest}`

// Plain words for a 13-year-old. Backend detail text is never shown as is.
const NETWORK = "We can't reach SPARQ right now. Check your internet and try again."
async function readJSON<T>(request: Promise<Response>): Promise<T> {
  let response: Response
  try { response = await request } catch { throw new Error(NETWORK) }
  if (!response.ok) {
    const detail = await response.json().then(body => (typeof body?.detail === 'string' ? body.detail : ''), () => '')
    throw new Error(
      detail === 'parent_notice_required' ? 'A parent needs to read the note on your home page first.'
        : response.status === 401 ? 'Your SPARQ time ran out. Open SPARQ from GMTM again.'
          : response.status === 403 ? "This part of SPARQ isn't open for your account."
            : response.status === 404 ? "We couldn't find that. Go back and try again."
              : response.status === 429 ? "You've done this a lot in the last hour. Take a break and try again later."
                : response.status === 502 ? "We couldn't write that just now. Try again in a minute."
                  : 'Something went wrong on our side. Try again in a minute.')
  }
  try { return await response.json() as T } catch { throw new Error('Something went wrong on our side. Try again in a minute.') }
}

function ExternalLink({ href, children }: { href: string | null; children: React.ReactNode }) {
  const url = https(href)
  if (!url) return null
  return <a href={url} target="_blank" rel="noopener noreferrer" className={textLink}>{children}<span className="sr-only"> (opens in a new tab)</span></a>
}

function ProgramCard({ program, open }: { program: CollegeProgram; open?: boolean }) {
  const Title = open ? 'h2' : 'h3'
  return <article className="rounded-xl border border-white/10 bg-sparq-charcoal-light p-5">
    <p className="text-[11px] font-medium uppercase tracking-[0.16em] text-gray-300">{program.level}{program.conference ? ` · ${program.conference}` : ''}</p>
    <Title className="mt-2 break-words text-xl font-semibold tracking-tight">{program.school}</Title>
    <p className="mt-1 text-sm text-gray-400">{program.city}, {program.state}</p>
    {program.reason && <p className="mt-3 break-words text-base leading-relaxed text-gray-200">{program.reason}</p>}
    {open && program.notes && <p className="mt-3 break-words text-sm text-gray-400">{program.notes}</p>}
    <div className="mt-3 flex flex-wrap gap-x-5">
      {program.program_link ? <ExternalLink href={program.program_link}>{program.program_link_label}</ExternalLink>
        : <span className="inline-flex min-h-11 items-center text-sm text-gray-400">{program.program_link_label}</span>}
      {!program.program_link && program.source_links.map((url, index) => <ExternalLink key={url} href={url}>Source {index + 1}</ExternalLink>)}
      <ExternalLink href={program.questionnaire_link}>Recruit questionnaire</ExternalLink>
    </div>
    <p className="mt-1 text-xs text-gray-500">{program.source_checked}</p>
    {!open && <Link href={`/home/colleges/${program.id}`} className={`${secondary} mt-4`}>Open {program.school}</Link>}
  </article>
}

function ContactPanel({ rules }: { rules: ContactRules[] }) {
  if (!rules.length) return null
  return <section aria-labelledby="contact-title" className="mt-8 border-t border-white/15 pt-5">
    <h2 id="contact-title" className="text-xl font-semibold tracking-tight">How college contact works</h2>
    <p className="mt-2 text-sm text-gray-400">These rules say when coaches can reach out to you. If a coach does not answer yet, it can be a rule, not a no.</p>
    <div className="mt-4 grid gap-5 sm:grid-cols-2">
      {rules.map(group => <div key={group.governing_body}>
        <h3 className="font-semibold">{group.level}</h3>
        <ul className="mt-2 space-y-2 text-sm text-gray-300">
          {group.rules.map(rule => <li key={rule.text}>{rule.text}{rule.source_url && <> <ExternalLink href={rule.source_url}>{rule.source_label || 'Source'}</ExternalLink></>}</li>)}
        </ul>
      </div>)}
    </div>
  </section>
}

function NotEligible({ notice, busy, onCheck }: { notice: string | null; busy: boolean; onCheck: () => void }) {
  return <div role="status" className="rounded-xl border border-white/10 bg-sparq-charcoal-light p-6">
    <p className="text-lg">{notice}</p>
    <div className="mt-5 flex flex-wrap gap-3">
      {/* After a fix on GMTM, this reads the GMTM profile again. */}
      <button type="button" onClick={onCheck} disabled={busy} className={secondary}>{busy ? 'Checking…' : 'Check again'}</button>
      <Link href="/home/inbox" className={secondary}>Back to my home</Link>
    </div>
  </div>
}

export function ProfileColleges() {
  const { user, isLoaded } = useSparqSession()
  const [list, setList] = useState<CollegeList | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
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

  if (!isLoaded || (!list && !error)) return <p role="status" className="py-16 text-center text-gray-400">Loading your colleges…</p>
  return <div className="pb-12 pt-8">
    <Link href="/home/inbox" className={textLink}>Back to my home</Link>
    <h1 className="mt-4 text-4xl font-semibold tracking-[-0.04em]">College flag football</h1>
    {error && <p role="alert" className="mt-4 text-red-300">{error}</p>}
    {list && !list.eligible ? <div className="mt-6"><NotEligible notice={list.notice} busy={busy} onCheck={() => void build()} /></div>
      : list && <>
        <p className="mt-2 max-w-2xl text-gray-400">Programs near you first, at every level. Each one comes from a school, conference or governing body page.</p>
        <div className="mt-5 flex flex-wrap gap-3">
          <button type="button" onClick={() => void build()} disabled={busy} className={list.built ? secondary : primary}>{busy ? 'Finding colleges…' : list.built ? 'Check my list again' : 'Find my colleges'}</button>
        </div>
        {list.built && !list.programs.length && <p className="mt-6 text-gray-400">No programs to show right now.</p>}
        <div className="mt-6 grid gap-4 md:grid-cols-2">{list.programs.map(program => <ProgramCard key={program.id} program={program} />)}</div>
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
  // One plain address only: no commas, semicolons, % or other mailto header tricks.
  const mailto = (d: Draft) => {
    const to = /^[A-Za-z0-9._+-]+@[A-Za-z0-9-]+(\.[A-Za-z0-9-]+)+$/.test(d.to_email.trim()) ? d.to_email.trim() : ''
    return `mailto:${to}?subject=${encodeURIComponent(d.subject)}&body=${encodeURIComponent(d.body)}`
  }
  const field = 'mt-1 block w-full rounded-xl border border-white/15 bg-white/[0.03] px-4 py-3 text-sm text-white focus:border-sparq-lime focus:outline-none'

  if (error && !detail) return <div className="pb-12 pt-8"><Link href="/home/colleges" className={textLink}>Back to colleges</Link><p role="alert" className="mt-6 text-red-300">{error}</p></div>
  if (!detail) return <p role="status" className="py-16 text-center text-gray-400">Loading…</p>
  return <div className="max-w-3xl pb-12 pt-8">
    <Link href="/home/colleges" className={textLink}>Back to colleges</Link>
    <div className="mt-4"><ProgramCard program={detail.program} open /></div>
    <section aria-labelledby="draft-title" className="mt-8">
      <h2 id="draft-title" className="text-xl font-semibold tracking-tight">Email the coach</h2>
      <p className="mt-2 text-sm text-gray-400">SPARQ writes a draft. You read it, change it, and send it from your own email. A parent can help. SPARQ never sends it.</p>
      {error && <p role="alert" className="mt-3 text-red-300">{error}</p>}
      {!draft ? <button type="button" onClick={() => void write()} disabled={busy} className={`${primary} mt-4`}>{busy ? 'Writing…' : 'Write a draft'}</button>
        : <div className="mt-4 rounded-xl border border-white/10 bg-sparq-charcoal-light p-5">
          <label className="block text-xs uppercase tracking-wide text-gray-400">To<input type="email" value={draft.to_email} onChange={e => setDraft({ ...draft, to_email: e.target.value })} placeholder="Add the coach's email from the school site" className={field} /></label>
          <label className="mt-3 block text-xs uppercase tracking-wide text-gray-400">Subject<input value={draft.subject} onChange={e => setDraft({ ...draft, subject: e.target.value })} className={field} /></label>
          <label className="mt-3 block text-xs uppercase tracking-wide text-gray-400">Email<textarea value={draft.body} onChange={e => setDraft({ ...draft, body: e.target.value })} rows={Math.max(8, draft.body.split('\n').length + 1)} className={field} /></label>
          <div className="mt-4 flex flex-wrap items-center gap-3">
            <button type="button" onClick={() => void copy()} disabled={busy} className={primary}>Copy</button>
            <a href={mailto(draft)} className={secondary}>Open in my email</a>
            <button type="button" onClick={() => void write()} disabled={busy || confirmReplace} className={`min-h-11 px-3 text-sm text-gray-400 hover:text-white ${focus}`}>{busy ? 'Writing…' : 'Write a new draft'}</button>
          </div>
          {confirmReplace && <div role="alertdialog" aria-labelledby="replace-edits" className="mt-3 flex flex-wrap items-center gap-3 rounded-xl border border-amber-200/40 p-3">
            <p id="replace-edits" className="text-sm text-amber-100">Replace your edits?</p>
            <button type="button" autoFocus onClick={() => setConfirmReplace(false)} className={secondary}>Keep my edits</button>
            <button type="button" onClick={() => void write(true)} className={secondary}>Replace</button>
          </div>}
          {copied && <p role="status" className="mt-2 text-sm text-gray-300">{copied}</p>}
        </div>}
    </section>
    <ContactPanel rules={detail.contact_rules} />
  </div>
}
