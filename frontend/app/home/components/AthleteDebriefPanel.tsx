'use client'

import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'
import { AthleteDebrief, DebriefParagraph, DebriefTrack, debriefFailure, debriefTracks, readAthleteDebrief } from './athleteDebrief'
import { evidenceDate, ProfileDraftKind } from './profileEvidence'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const field = 'mt-2 block w-full min-w-0 rounded-xl border border-white/15 bg-black/20 px-4 py-3 text-sm leading-relaxed text-white placeholder:text-gray-400 focus:border-sparq-lime focus:outline-none'

export default function AthleteDebriefPanel({ onPrepare }: { onPrepare: (kind: ProfileDraftKind, question: string) => void }) {
  const [track, setTrack] = useState<DebriefTrack>('profile')
  const [question, setQuestion] = useState('')
  const [answer, setAnswer] = useState<AthleteDebrief | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [sourcesOpen, setSourcesOpen] = useState(false)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [])

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
        if (mounted.current && !controller.signal.aborted) setError(debriefFailure(response.status, code))
        return
      }
      const result = readAthleteDebrief(await response.json(), request)
      if (!mounted.current || controller.signal.aborted) return
      setAnswer(result)
      setSourcesOpen(false)
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
  const paragraph = (part: DebriefParagraph, label: string) => <p className="break-words text-sm leading-relaxed text-gray-200">{part.text}{' '}<button type="button" aria-label={`Show sources for ${label}`} onClick={() => setSourcesOpen(true)} className={`inline-flex min-h-8 items-center px-1 text-xs text-sparq-lime underline underline-offset-4 ${focus}`}>[{part.refs.map(id => (answer?.references.findIndex(ref => ref.id === id) ?? -1) + 1).join(', ')}]</button></p>

  return <section aria-labelledby="profile-debrief-title">
    <h2 id="profile-debrief-title" className="text-2xl font-semibold tracking-tight">What comes next for you?</h2>
    <p className="mt-3 text-sm leading-relaxed text-gray-400">Ask about your recorded evidence and a useful next step.</p>
    <form className="mt-6" onSubmit={event => { event.preventDefault(); void ask() }}>
      <label htmlFor="debrief-track" className="text-sm font-medium">Your focus</label>
      <select id="debrief-track" value={track} onChange={event => setTrack(event.target.value as DebriefTrack)} className={field}>{debriefTracks.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select>
      <label htmlFor="debrief-question" className="mt-5 block text-sm font-medium">What would you like to figure out?</label>
      <textarea id="debrief-question" value={question} onChange={event => setQuestion(event.target.value)} maxLength={1000} rows={3} required className={field} placeholder="How can I use the profile I’ve built to introduce myself to a coach?" />
      <p className="mt-3 text-xs leading-relaxed text-gray-400">Ask SPARQ uses AI with your question and available public profile evidence, independent of your draft selections. It does not contact anyone or analyze footage.</p>
      <button type="submit" disabled={loading || !question.trim() || question.trim().length > 1000} className={`mt-5 inline-flex min-h-12 w-full items-center justify-center rounded-xl bg-sparq-lime px-5 py-3 text-sm font-bold text-sparq-charcoal hover:bg-sparq-lime-light disabled:cursor-not-allowed disabled:opacity-40 ${focus}`}>{loading ? 'Asking SPARQ…' : 'Ask SPARQ'}</button>
    </form>
    {loading && <p role="status" className="mt-4 text-sm text-gray-300">Reading your current evidence and preparing an answer…</p>}
    {error && <p role="alert" className="mt-4 text-sm leading-relaxed text-amber-200">{error}</p>}
    {answer && <div className="mt-7 space-y-5 border-t border-white/10 pt-6" aria-label="SPARQ answer">
      {previous && <p role="status" className="text-xs leading-relaxed text-amber-200">Previous answer — this belongs to the question below. {loading ? 'Your latest request is still running.' : error ? 'The latest request did not produce a new answer.' : 'Ask again to answer your changed question or focus.'}</p>}
      <div><p className="mb-2 text-xs font-medium text-gray-400">{debriefTracks.find(option => option.value === answer.track)?.label}</p><p className="mb-4 break-words text-sm text-gray-400">“{answer.question}”</p>{paragraph(answer.answer, 'the answer')}</div>
      {answer.insights.length > 0 && <div><h3 className="mb-3 text-sm font-semibold">What your evidence supports</h3><ul className="space-y-3">{answer.insights.map((item, index) => <li key={index}>{paragraph(item, `observation ${index + 1}`)}</li>)}</ul></div>}
      {answer.unknowns.length > 0 && <div><h3 className="mb-3 text-sm font-semibold">What remains unknown</h3><ul className="space-y-3">{answer.unknowns.map((item, index) => <li key={index}>{paragraph(item, `unknown ${index + 1}`)}</li>)}</ul></div>}
      <div className="rounded-xl border border-white/15 p-4"><h3 className="mb-2 text-sm font-semibold">One next step</h3>{paragraph(answer.next_action.reason, 'the next step')}{answer.next_action.kind === 'open_source'
        ? previous ? <span className="mt-3 inline-flex min-h-11 items-center text-sm text-gray-500">{answer.next_action.label}</span> : <a href={answer.next_action.href!} target="_blank" rel="noopener noreferrer" className={`mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-sparq-lime underline underline-offset-4 ${focus}`}>{answer.next_action.label}</a>
        : <button type="button" disabled={previous} onClick={() => onPrepare(answer.next_action.kind === 'prepare_introduction' ? 'introduction' : 'summary', question.trim())} className={`mt-3 inline-flex min-h-11 items-center text-sm font-semibold text-sparq-lime underline underline-offset-4 disabled:cursor-not-allowed disabled:text-gray-500 ${focus}`}>{answer.next_action.label}</button>}</div>
      <details open={sourcesOpen} onToggle={event => setSourcesOpen(event.currentTarget.open)} className="border-t border-white/10 pt-2"><summary className={`min-h-11 cursor-pointer py-3 text-sm text-gray-400 ${focus}`}>Sources for this answer</summary><p className="mb-3 text-xs leading-relaxed text-gray-400">Based on a fresh profile read {evidenceDate(answer.fetched_at)}. The facts you select for your draft remain your choice.</p><ol className="list-decimal space-y-4 pl-5 text-xs leading-relaxed text-gray-400">{answer.references.map(ref => <li key={ref.id}><p className="break-words font-medium text-gray-300">{ref.label}</p><p className="mt-1 break-words">{ref.detail}</p>{ref.kind === 'official' && ref.checked_at && <p className="mt-1">Source reviewed {evidenceDate(ref.checked_at)}.</p>}{ref.href && <a href={ref.href} target="_blank" rel="noopener noreferrer" className={`mt-1 inline-flex min-h-11 items-center text-gray-300 underline underline-offset-4 ${focus}`}>Open source: {ref.label}</a>}</li>)}</ol></details>
    </div>}
  </section>
}
