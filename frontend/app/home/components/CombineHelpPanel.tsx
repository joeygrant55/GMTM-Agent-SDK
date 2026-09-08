'use client'

import { useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'
import { CombineActivity, CurrentCombine } from './currentCombine'
import { useCombineHelp } from './CombineHelpProvider'
import ActivityRequirements from './ActivityRequirements'

interface HelpMessage { role: 'user' | 'assistant'; content: string }

function boundedHistory(messages: HelpMessage[]): HelpMessage[] {
  const recent = messages.slice(-12).map(m => ({ ...m, content: m.content.trim().slice(0, 2000) }))
  // Keep complete user/assistant pairs so failed/partial responses never become history.
  while (recent.reduce((sum, m) => sum + m.content.length, 0) > 12000) recent.splice(0, 2)
  return recent
}

function httpMessage(status: number): string {
  if (status === 401) return 'Sign in again before asking for combine help.'
  if (status === 404) return 'This event or activity is no longer available. Refresh your combine or check GMTM.'
  if (status === 409) return 'Your athlete connection could not be confirmed. Check your connection or contact your organizer.'
  if (status === 429) return 'Too many questions right now. Wait a moment, then try again.'
  if (status === 422) return 'That question could not be sent. Keep it under 2,000 characters and try again.'
  return 'Combine help is unavailable right now. You can still use the organizer instructions and continue in GMTM.'
}

export default function CombineHelpPanel() {
  const context = useCombineHelp()
  const event = context?.snapshot?.selected_event
  if (!context?.clerkId || !event || !context.snapshot) {
    return (
      <div className="flex h-full min-w-0 flex-col border-l border-white/10 bg-sparq-charcoal p-4 text-white">
        <h2 tabIndex={-1} className="font-bold">Combine help</h2>
        <p className="mt-3 text-sm text-gray-300">{context?.clerkId ? 'Choose a combine and load its activities to ask about your next step. No results are needed.' : 'Sign in to ask about your combine.'}</p>
        <p className="mt-3 text-xs text-gray-400">Your combine card remains the place to choose an event or retry a failed refresh.</p>
      </div>
    )
  }
  const activity = context.snapshot.activities.find(a => a.task_id === context.taskId) ?? null
  return <CombineHelpSession key={`${context.clerkId}:${event.event_id}:${activity?.task_id ?? 'event'}`} snapshot={context.snapshot} activity={activity} />
}

function CombineHelpSession({ snapshot, activity }: { snapshot: CurrentCombine; activity: CombineActivity | null }) {
  const event = snapshot.selected_event!
  const [messages, setMessages] = useState<HelpMessage[]>([])
  const [input, setInput] = useState('')
  const [pendingQuestion, setPendingQuestion] = useState('')
  const [partialAnswer, setPartialAnswer] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [toolStatus, setToolStatus] = useState('')
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const cancelRequest = useRef<(() => void) | null>(null)
  const deadline = useRef<ReturnType<typeof setTimeout> | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const logEnd = useRef<HTMLDivElement>(null)
  useEffect(() => {
    mounted.current = true
    return () => {
      mounted.current = false
      active.current?.abort()
      active.current = null
      cancelRequest.current = null
      if (deadline.current !== null) clearTimeout(deadline.current)
    }
  }, [])
  useEffect(() => { logEnd.current?.scrollIntoView({ block: 'nearest' }) }, [messages, partialAnswer, busy])

  const send = async () => {
    const question = input.trim()
    if (!question || question.length > 2000 || active.current || !mounted.current) return
    const controller = new AbortController()
    active.current = controller
    const current = () => mounted.current && active.current === controller && !controller.signal.aborted
    setBusy(true)
    setError('')
    setToolStatus('Checking your current combine…')
    setPendingQuestion(question)
    setPartialAnswer('')
    setInput('')
    let reader: ReadableStreamDefaultReader<Uint8Array> | undefined
    const stop = (message: string) => {
      if (!current()) return
      controller.abort()
      active.current = null
      cancelRequest.current = null
      if (deadline.current !== null) clearTimeout(deadline.current)
      setBusy(false)
      setToolStatus('')
      setInput(question)
      setError(message)
      void reader?.cancel().catch(() => {})
    }
    cancelRequest.current = () => stop('Answer canceled. You can edit your question and send it again.')
    const timer = setTimeout(() => stop('This answer is taking too long. Try again, or continue with the organizer instructions in GMTM.'), 55000)
    deadline.current = timer
    try {
      const response = await apiFetch('/api/combine/help', {
        method: 'POST', signal: controller.signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ event_id: event.event_id, task_id: activity?.task_id ?? null, message: question, history: boundedHistory(messages) }),
      })
      if (!current()) return
      if (!response.ok) throw new Error(httpMessage(response.status))
      if (!response.body) throw new Error(httpMessage(503))
      reader = response.body.getReader()
      const decoder = new TextDecoder()
      let buffer = '', answer = '', done = false
      const parseFrame = (frame: string) => {
        const data = frame.split('\n').filter(line => line.startsWith('data:')).map(line => line.slice(5).trimStart()).join('\n')
        if (!data) return
        const chunk = JSON.parse(data)
        if (chunk.type === 'error' || done) throw new Error(httpMessage(503))
        if (chunk.type === 'text' && typeof chunk.text === 'string') {
          answer += chunk.text
          if (answer.length > 24000) throw new Error(httpMessage(503))
          setPartialAnswer(answer)
          setToolStatus('')
        } else if (chunk.type === 'tool' && chunk.name === 'get_current_combine') {
          setToolStatus('Checking your current combine…')
        } else if (chunk.type === 'done') done = true
        else throw new Error(httpMessage(503))
      }
      while (true) {
        const part = await reader.read()
        if (!current()) return
        buffer += part.done ? decoder.decode() : decoder.decode(part.value, { stream: true })
        buffer = buffer.replace(/\r\n/g, '\n')
        let boundary: number
        while ((boundary = buffer.indexOf('\n\n')) >= 0) {
          parseFrame(buffer.slice(0, boundary))
          buffer = buffer.slice(boundary + 2)
        }
        if (part.done) break
      }
      if (buffer.trim()) parseFrame(buffer)
      if (!done || !answer.trim()) throw new Error('The answer was interrupted. Try again, or use the organizer instructions in GMTM.')
      if (!current()) return
      setMessages(previous => [...previous, { role: 'user', content: question }, { role: 'assistant', content: answer }])
      setPendingQuestion('')
      setPartialAnswer('')
    } catch (e) {
      if (current()) {
        setError(e instanceof Error && !(e instanceof SyntaxError) && !(e instanceof TypeError) ? e.message : httpMessage(503))
        setInput(question)
      }
    } finally {
      clearTimeout(timer)
      void reader?.cancel().catch(() => {})
      if (active.current === controller) {
        active.current = null
        cancelRequest.current = null
        if (mounted.current) { setBusy(false); setToolStatus('') }
      }
    }
  }

  const starters = ['What should I do next?', ...(activity ? ['Help me record this activity'] : []), 'What is still missing?']
  return (
    <div className="flex h-full min-h-0 min-w-0 flex-col border-l border-white/10 bg-sparq-charcoal text-white">
      <header className="shrink-0 border-b border-white/10 p-4">
        <h2 tabIndex={-1} className="font-bold">Combine help</h2>
        <p className="mt-2 break-words text-sm font-semibold">{activity?.title ?? event.name}</p>
        {activity && <p className="mt-1 break-words text-xs text-gray-400">{event.name}</p>}
        <a className="mt-2 inline-flex min-h-11 items-center text-sm font-bold text-sparq-lime underline" href={event.continuation_url}>Continue in GMTM</a>
      </header>
      <div className="min-h-0 flex-1 overflow-y-auto p-4">
        {snapshot.athlete_id === null && <p className="mb-3 text-sm text-gray-300">Personal progress is unavailable. You can still ask for help with the public checklist here.</p>}
        {activity && <>
          <p className="mb-2 text-sm text-gray-300">{activity.submission_state === 'unavailable'
            ? 'Saved progress for this activity could not be checked.'
            : activity.submission_state === 'not_submitted'
              ? 'No saved attempt is visible for this activity.'
              : activity.evidence_state === 'fields_present'
                ? 'A saved attempt has the required information. Validity and organizer acceptance are not confirmed here.'
                : activity.evidence_state === 'missing_fields'
                  ? 'A saved attempt is visible, with required information still missing.'
                  : 'A saved attempt is visible. Its required information could not be checked.'}</p>
          <ActivityRequirements activity={activity} />
        </>}
        {activity && (
          <details className="mb-4 rounded-lg border border-white/15 p-3 text-sm">
            <summary className="cursor-pointer py-2 font-semibold text-sparq-lime">Organizer instructions</summary>
            <p className="mt-2 whitespace-pre-wrap break-words leading-relaxed text-gray-300">{activity.description || 'Open GMTM to read this activity’s organizer instructions.'}</p>
          </details>
        )}
        <p className="mb-3 text-xs text-gray-400">Ask about this {activity ? 'activity' : 'combine'}. Each question checks current GMTM information. This conversation lasts only while you stay in this help context.</p>
        <div className="mb-4 flex flex-col gap-2">
          {starters.map(prompt => <button key={prompt} disabled={busy} type="button" onClick={() => { setInput(prompt); inputRef.current?.focus() }} className="min-h-11 rounded-lg border border-white/15 px-3 py-2 text-left text-sm disabled:opacity-50">{prompt}</button>)}
        </div>
        <div role="log" aria-label="Combine conversation" aria-live="polite" className="space-y-3">
          {messages.map((message, index) => <p key={index} className={`whitespace-pre-wrap break-words rounded-lg p-3 text-sm ${message.role === 'user' ? 'bg-sparq-lime/10' : 'bg-white/5'}`}><span className="sr-only">{message.role === 'user' ? 'You: ' : 'SPARQ: '}</span>{message.content}</p>)}
          {pendingQuestion && <p className="whitespace-pre-wrap break-words rounded-lg bg-sparq-lime/10 p-3 text-sm"><span className="sr-only">You: </span>{pendingQuestion}</p>}
          {partialAnswer && <div className="rounded-lg bg-white/5 p-3 text-sm"><p className="whitespace-pre-wrap break-words">{partialAnswer}</p>{error && <p className="mt-2 text-xs text-amber-200">Incomplete answer</p>}</div>}
          {toolStatus && <p role="status" className="text-xs text-gray-400">{toolStatus}</p>}
          {error && <p role="alert" className="rounded-lg border border-amber-200/30 p-3 text-sm text-amber-200">{error}</p>}
          <div ref={logEnd} />
        </div>
      </div>
      <form className="shrink-0 border-t border-white/10 p-3" onSubmit={e => { e.preventDefault(); void send() }}>
        <label className="sr-only" htmlFor="combine-help-question">Your combine question</label>
        <textarea id="combine-help-question" ref={inputRef} value={input} maxLength={2000} disabled={busy} onChange={e => setInput(e.target.value)} placeholder="Ask about your combine…" rows={2} className="block w-full min-w-0 resize-none rounded-lg border border-white/15 bg-white/5 p-3 text-sm disabled:opacity-50" />
        <div className="mt-2 flex items-center justify-between gap-2"><span className="text-xs text-gray-400">{input.length}/2,000</span>{busy ? <button key="cancel" type="button" onClick={e => { e.preventDefault(); cancelRequest.current?.() }} className="min-h-11 rounded-lg border border-white/20 px-4 text-sm font-bold">Cancel answer</button> : <button key="send" type="submit" disabled={!input.trim() || input.trim().length > 2000} className="min-h-11 rounded-lg bg-sparq-lime px-5 text-sm font-bold text-sparq-charcoal disabled:opacity-50">Send</button>}</div>
      </form>
    </div>
  )
}
