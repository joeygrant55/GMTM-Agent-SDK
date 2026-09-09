'use client'

import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'
import { AthleteDebrief, DebriefParagraph, DebriefTrack, debriefFailure, readAthleteDebrief } from './athleteDebrief'
import { evidenceDate, ProfileDraftKind } from './profileEvidence'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const primary = `inline-flex min-h-12 w-full items-center justify-center rounded-2xl bg-sparq-lime px-5 py-3 text-sm font-bold text-sparq-charcoal hover:bg-sparq-lime-light disabled:cursor-not-allowed disabled:opacity-40 motion-safe:transition-colors motion-reduce:transition-none ${focus}`
const intents: { track: DebriefTrack; label: string; question: string }[] = [
  { track: 'profile', label: 'Understand my profile', question: 'How can I use my profile to create more opportunities?' },
  { track: 'national_team', label: 'USA Football (adult)', question: 'What happens after my adult USA Football digital combine?' },
  { track: 'outreach', label: 'Introduce myself', question: 'How can I introduce myself to a coach using my profile?' },
]

export default function AthleteDebriefPanel({ onPrepare, expectedOwnerScope, onScopeMismatch }: { onPrepare: (kind: ProfileDraftKind, question: string) => void; expectedOwnerScope?: string; onScopeMismatch?: () => void }) {
  const [track, setTrack] = useState<DebriefTrack>('profile')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AthleteDebrief | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const [editing, setEditing] = useState(true)
  const questionInput = useRef<HTMLTextAreaElement>(null)
  const answerHeading = useRef<HTMLHeadingElement>(null)
  const sourcesSummary = useRef<HTMLElement>(null)
  const focusQuestion = useRef(false)
  const currentInput = useRef({ track, question: question.trim() })
  currentInput.current = { track, question: question.trim() }
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [])
  useEffect(() => {
    if (editing && focusQuestion.current) {
      focusQuestion.current = false
      questionInput.current?.focus()
    } else if (answer && !editing) answerHeading.current?.focus()
  }, [answer, editing])
  useEffect(() => { if (sourcesOpen) sourcesSummary.current?.focus() }, [sourcesOpen])

  const ask = async () => {
    if (!mounted.current || active.current || !question.trim() || question.trim().length > 1000) return
    const request = { track, question: question.trim() }
    const controller = new AbortController()
    active.current = controller
    setLoading(true)
    setError(null)
    const timer = window.setTimeout(() => {
      controller.abort()
      if (mounted.current && active.current === controller) {
        active.current = null
        setLoading(false)
        setError('SPARQ took too long to answer. Please try again. Your profile and draft have not been changed.')
      }
    }, 60000)
    controller.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const response = await apiFetch('/api/athlete/debrief', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request), cache: 'no-store', signal: controller.signal })
      if (!mounted.current || controller.signal.aborted) return
      if (!response.ok) {
        let code: string | undefined
        try {
          const body: unknown = await response.json()
          if (body && typeof body === 'object' && 'code' in body && typeof body.code === 'string') code = body.code
        } catch { /* HTTP status still provides a safe message for a non-JSON failure. */ }
        if (mounted.current && !controller.signal.aborted) {
          setError(debriefFailure(response.status, code))
          if ([401, 403, 409].includes(response.status)) { setAnswer(null); onScopeMismatch?.() }
        }
        return
      }
      const result = readAthleteDebrief(await response.json(), request)
      if (!mounted.current || controller.signal.aborted) return
      if (expectedOwnerScope && result.owner_scope !== expectedOwnerScope) {
        setAnswer(null)
        setError('Your profile connection changed. Reload before asking again.')
        onScopeMismatch?.()
        return
      }
      setAnswer(result)
      setSourcesOpen(false)
      setEditing(result.track !== currentInput.current.track || result.question !== currentInput.current.question)
    } catch {
      if (mounted.current && active.current === controller && !controller.signal.aborted) setError('SPARQ could not confirm that answer. Please try again. Your profile and draft have not been changed.')
    } finally {
      window.clearTimeout(timer)
      if (active.current === controller) {
        active.current = null
        if (mounted.current) setLoading(false)
      }
    }
  }
  const changed = answer !== null && (answer.track !== track || answer.question !== question.trim())
  const previous = !!answer && (changed || loading || !!error)
  const chooseIntent = (intent: typeof intents[number]) => { setTrack(intent.track); setQuestion(intent.question) }
  const editQuestion = () => { focusQuestion.current = true; setEditing(true) }
  const revealSources = () => { if (sourcesOpen) sourcesSummary.current?.focus(); else setSourcesOpen(true) }
  const paragraph = (part: DebriefParagraph, label: string, prominent = false) => <p className={`break-words ${prominent ? 'text-xl leading-relaxed text-white sm:text-2xl' : 'text-sm leading-relaxed text-gray-300'}`}>
    {part.text}{' '}<button type="button" aria-label={`Show sources for ${label}`} onClick={revealSources} className={`inline-flex min-h-11 min-w-11 items-center justify-center align-middle px-1 text-xs font-medium text-sparq-lime underline underline-offset-4 ${focus}`}>[{part.refs.map(id => (answer?.references.findIndex(ref => ref.id === id) ?? -1) + 1).join(', ')}]</button>
  </p>

  return <section aria-labelledby="profile-debrief-title" className="min-w-0">
    {editing && <>
      <h2 id="profile-debrief-title" className="text-4xl font-semibold tracking-[-0.045em] sm:text-5xl">What’s your next move?</h2>
      <p className="mt-3 text-base leading-relaxed text-gray-400">Make your profile work for you.</p>
      <form className="mt-7" onSubmit={event => { event.preventDefault(); void ask() }}>
        <fieldset><legend className="sr-only">Your focus</legend><div className="flex flex-wrap gap-2">
          {intents.map(intent => <label key={intent.track} className="relative inline-flex cursor-pointer">
            <input type="radio" name="debrief-track" value={intent.track} checked={track === intent.track} onChange={() => chooseIntent(intent)} onClick={() => { if (track === intent.track) chooseIntent(intent) }} className="peer absolute inset-0 m-0 h-full w-full cursor-pointer opacity-0" />
            <span className="inline-flex min-h-11 items-center rounded-full border border-white/15 px-4 py-2 text-xs font-medium text-gray-300 peer-checked:border-sparq-lime/60 peer-checked:bg-sparq-lime/[0.06] peer-checked:text-sparq-lime peer-focus-visible:outline peer-focus-visible:outline-2 peer-focus-visible:outline-offset-4 peer-focus-visible:outline-sparq-lime motion-safe:transition-colors motion-reduce:transition-none">{intent.label}</span>
          </label>)}
        </div></fieldset>
        <label htmlFor="debrief-question" className="sr-only">What would you like to figure out?</label>
        <textarea id="debrief-question" ref={questionInput} value={question} onChange={event => setQuestion(event.target.value)} maxLength={1000} rows={3} required className="mt-4 block min-h-32 w-full min-w-0 resize-y rounded-2xl border border-white/20 bg-white/[0.025] px-5 py-4 text-base leading-relaxed text-white placeholder:text-gray-500 focus:border-sparq-lime focus:outline-none" placeholder="Tell SPARQ what you’re working toward…" />
        <button type="submit" disabled={loading || !question.trim() || question.trim().length > 1000} className={`${primary} mt-4`}>{loading ? 'Asking SPARQ…' : 'Ask SPARQ'}</button>
      </form>
      <details className="mt-3 text-xs leading-relaxed text-gray-400"><summary className={`inline-flex min-h-11 cursor-pointer items-center ${focus}`}>How SPARQ uses your profile</summary><p className="max-w-xl pb-3">Ask SPARQ uses AI with your question and available public profile evidence, independent of your draft selections. It does not contact anyone or analyze footage.</p></details>
    </>}
    {loading && <p role="status" className="mt-4 text-sm text-gray-300">Reviewing your profile…</p>}
    {error && <p role="alert" className="mt-4 text-sm leading-relaxed text-amber-200">{error}</p>}
    {answer && <div className={editing ? 'mt-8 border-t border-white/10 pt-7' : ''} aria-label="SPARQ answer">
      {previous && <p role="status" className="mb-4 text-xs leading-relaxed text-amber-200">Previous answer — {loading ? 'your new request is still running.' : error ? 'the latest request did not produce a new answer.' : 'ask again for your updated question or focus.'}</p>}
      <div className="mb-6 flex items-start justify-between gap-4">
        {editing ? <h3 className="min-w-0 break-words text-sm leading-relaxed text-gray-400">{answer.question}</h3> : <h2 id="profile-debrief-title" ref={answerHeading} tabIndex={-1} className="min-w-0 break-words pt-2 text-sm font-medium leading-relaxed text-gray-400 focus:outline-none">{answer.question}</h2>}
        {!editing && <button type="button" onClick={editQuestion} className={`inline-flex min-h-11 shrink-0 items-center text-xs font-medium text-gray-300 underline underline-offset-4 ${focus}`}>Edit question</button>}
      </div>
      {paragraph(answer.answer, 'the answer', true)}
      {answer.unknowns.length > 0 && <div className="mt-5 border-l-2 border-white/20 pl-4" aria-label="What remains unknown"><ul className="space-y-2">{answer.unknowns.map((item, index) => <li key={index}>{paragraph(item, `unknown ${index + 1}`)}</li>)}</ul></div>}
      <div className="mt-6">{answer.next_action.kind === 'open_source'
        ? previous ? <span aria-disabled="true" className={`${primary} pointer-events-none opacity-40`}>{answer.next_action.label}</span> : <a href={answer.next_action.href!} target="_blank" rel="noopener noreferrer" className={primary}>{answer.next_action.label}</a>
        : <button type="button" disabled={previous} onClick={() => onPrepare(answer.next_action.kind === 'prepare_introduction' ? 'introduction' : 'summary', question.trim())} className={primary}>{answer.next_action.label}</button>}</div>
      <div className="mt-6 border-t border-white/10 pt-2">
        <details><summary className={`min-h-11 cursor-pointer py-3 text-sm text-gray-400 ${focus}`}>Why this answer?</summary>
          {answer.insights.length > 0 && <div className="pb-4"><h3 className="mb-2 text-xs font-medium text-gray-400">Supporting evidence</h3><ul className="space-y-2">{answer.insights.map((item, index) => <li key={index}>{paragraph(item, `observation ${index + 1}`)}</li>)}</ul></div>}
          <div className="pb-4"><h3 className="mb-2 text-xs font-medium text-gray-400">Why this step</h3>{paragraph(answer.next_action.reason, 'the next step')}</div>
        </details>
        <details open={sourcesOpen} onToggle={event => setSourcesOpen(event.currentTarget.open)}><summary ref={sourcesSummary} className={`min-h-11 cursor-pointer py-3 text-sm text-gray-400 ${focus}`}>Sources for this answer</summary><p className="mb-3 text-xs leading-relaxed text-gray-400">Profile read {evidenceDate(answer.fetched_at)}. Your draft selections stay unchanged.</p><ol className="list-decimal space-y-4 pl-5 text-xs leading-relaxed text-gray-400">{answer.references.map(ref => <li key={ref.id}><p className="break-words font-medium text-gray-300">{ref.label}</p><p className="mt-1 break-words">{ref.detail}</p>{ref.kind === 'official' && ref.checked_at && <p className="mt-1">Source reviewed {evidenceDate(ref.checked_at)}.</p>}{ref.href && <a href={ref.href} target="_blank" rel="noopener noreferrer" className={`mt-1 inline-flex min-h-11 items-center text-gray-300 underline underline-offset-4 ${focus}`}>Open source: {ref.label}</a>}</li>)}</ol></details>
      </div>
    </div>}
  </section>
}
