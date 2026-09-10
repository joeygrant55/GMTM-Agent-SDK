'use client'

import { useEffect, useId, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'
import { AthleteOpportunity, AthleteOpportunitiesResponse, OpportunityCategory, OpportunityFormat, OpportunityScopeError, isOpportunityCurrent, readAthleteOpportunities } from './opportunityEvidence'

export interface AthleteOpportunitiesProps {
  ownerScope: string
  linkRevision: string
  goal: string | null
  active: boolean
  onPrepare: (item: AthleteOpportunity) => void
  onScopeLost: () => void
}

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime'
const primary = `inline-flex min-h-12 items-center justify-center rounded-xl bg-sparq-lime px-5 py-3 text-sm font-semibold text-sparq-charcoal transition-colors hover:bg-sparq-lime-light disabled:cursor-wait disabled:opacity-40 ${focus}`
const secondary = `inline-flex min-h-11 items-center text-sm text-gray-300 underline underline-offset-4 hover:text-white ${focus}`
const field = 'min-h-12 w-full rounded-xl border border-white/20 bg-sparq-charcoal-light px-4 py-3 text-sm text-white focus:border-sparq-lime focus:outline-none disabled:opacity-50'
const categories: { value: OpportunityCategory; label: string }[] = [{ value: 'unspecified', label: 'Not specified' }, { value: 'men', label: 'Men’s' }, { value: 'women', label: 'Women’s' }]
const formats: { value: OpportunityFormat; label: string }[] = [{ value: 'any', label: 'Any format' }, { value: 'remote', label: 'Remote' }, { value: 'in_person', label: 'In person' }]
const statusLabels = { registration_open: 'Registration published as open', published_route: 'Published route', check_details: 'Confirm details' }
const RESPONSE_LIMIT = 128 * 1024
const date = (value: string) => new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(value))

async function readBoundedResponse(response: Response): Promise<unknown> {
  const length = response.headers.get('content-length')
  if (length && (!/^\d+$/.test(length) || Number(length) > RESPONSE_LIMIT)) throw new Error('Response limit')
  if (!response.body) throw new Error('Missing response')
  const reader = response.body.getReader()
  const chunks: Uint8Array[] = []
  let size = 0
  try {
    while (true) {
      const { done, value } = await reader.read()
      if (done) break
      size += value.byteLength
      if (size > RESPONSE_LIMIT) throw new Error('Response limit')
      chunks.push(value)
    }
    const bytes = new Uint8Array(size)
    let offset = 0
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength }
    return JSON.parse(new TextDecoder('utf-8', { fatal: true }).decode(bytes))
  } finally {
    void reader.cancel().catch(() => {})
    reader.releaseLock()
  }
}

export default function AthleteOpportunities({ ownerScope, linkRevision, goal, active, onPrepare, onScopeLost }: AthleteOpportunitiesProps) {
  const [category, setCategory] = useState<OpportunityCategory>('unspecified')
  const [format, setFormat] = useState<OpportunityFormat>('any')
  const [result, setResult] = useState<{ data: AthleteOpportunitiesResponse; category: OpportunityCategory; format: OpportunityFormat } | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [detailsId, setDetailsId] = useState<string | null>(null)
  const [clock, setClock] = useState(() => Date.now())
  const controller = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const current = useRef({ ownerScope, linkRevision, active })
  current.current = { ownerScope, linkRevision, active }
  const scopeLost = useRef(onScopeLost)
  scopeLost.current = onScopeLost
  const dialog = useRef<HTMLDialogElement>(null)
  const returnFocus = useRef<HTMLElement | null>(null)
  const id = useId()

  const sameScope = result?.data.owner_scope === ownerScope && result.data.link_revision === linkRevision
  const sameOptions = result?.category === category && result.format === format
  const response = sameScope && sameOptions ? result!.data : null
  const items = response?.items.filter(item => isOpportunityCurrent(item)) || []
  const selected = active ? items.find(item => item.id === detailsId) || null : null

  useEffect(() => {
    mounted.current = true
    return () => { mounted.current = false; controller.current?.abort(); controller.current = null }
  }, [])
  useEffect(() => {
    controller.current?.abort(); controller.current = null
    setResult(null); setError(null); setLoading(false); setDetailsId(null)
    setCategory('unspecified'); setFormat('any')
  }, [ownerScope, linkRevision])
  useEffect(() => {
    if (!active) setDetailsId(null)
    else setClock(Date.now())
  }, [active])
  useEffect(() => {
    if (!response || !active) return
    const now = Date.now()
    const next = response.items.flatMap(item => [Date.parse(item.valid_until), ...item.sources.map(source => Date.parse(source.expires_at))]).filter(time => time > now)
    if (!next.length) return
    const timer = window.setTimeout(() => setClock(Date.now()), Math.min(Math.max(1, Math.min(...next) - now + 1), 2147483647))
    return () => window.clearTimeout(timer)
  }, [response, active, clock])
  useEffect(() => {
    if (!selected || !active || !dialog.current) return
    const element = dialog.current
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    element.showModal()
    return () => {
      element.close(); document.body.style.overflow = previousOverflow
      if (current.current.active && returnFocus.current?.isConnected) returnFocus.current.focus()
    }
  }, [selected, active])

  const search = async () => {
    if (!mounted.current || !active || controller.current || !categories.some(option => option.value === category)
      || !formats.some(option => option.value === format) || !/^[a-f0-9]{64}$/.test(ownerScope) || !/^[a-f0-9]{64}$/.test(linkRevision)) return
    const identity = { ownerScope, linkRevision }
    const request = { pathway: 'adult_flag', category, format, link_revision: linkRevision }
    const pending = new AbortController()
    controller.current = pending
    setLoading(true); setError(null); setDetailsId(null)
    const isCurrent = () => mounted.current && controller.current === pending && !pending.signal.aborted
      && current.current.ownerScope === identity.ownerScope && current.current.linkRevision === identity.linkRevision
    const timer = window.setTimeout(() => {
      if (!isCurrent()) return
      pending.abort(); controller.current = null; setLoading(false)
      setError('The search took too long. Your profile and draft are unchanged. Try again when you’re ready.')
    }, 30000)
    pending.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const fetched = await apiFetch('/api/athlete/opportunities', { method: 'POST', cache: 'no-store', signal: pending.signal,
        headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(request) })
      if (!isCurrent()) return
      if ([401, 403, 409].includes(fetched.status)) throw new OpportunityScopeError('Your profile connection changed. Reload before searching again.')
      if (!fetched.ok) throw new Error(fetched.status === 429 ? 'limit' : 'unavailable')
      const payload = await readBoundedResponse(fetched)
      if (!isCurrent()) return
      const data = readAthleteOpportunities(payload, identity)
      setResult({ data, category: request.category, format: request.format }); setClock(Date.now())
    } catch (failure) {
      if (!isCurrent()) return
      if (failure instanceof OpportunityScopeError) {
        setResult(null); setError(failure.message); scopeLost.current()
      } else setError(failure instanceof Error && failure.message === 'limit'
        ? 'Please try again later. Your profile and draft are unchanged.'
        : 'We couldn’t confirm these opportunities. Your profile and draft are unchanged. Please try again.')
    } finally {
      window.clearTimeout(timer)
      if (controller.current === pending) { controller.current = null; if (mounted.current) setLoading(false) }
    }
  }
  const actionCurrent = (item: AthleteOpportunity) => {
    const valid = current.current.active && response?.owner_scope === current.current.ownerScope
      && response.link_revision === current.current.linkRevision && sameOptions && !loading && !error && isOpportunityCurrent(item)
    if (!valid) setClock(Date.now())
    return valid
  }
  const showDetails = (item: AthleteOpportunity, button: HTMLButtonElement) => {
    if (!isOpportunityCurrent(item)) { setClock(Date.now()); return }
    returnFocus.current = button; setDetailsId(item.id)
  }

  return <section hidden={!active} aria-labelledby={`${id}-title`} className="max-w-5xl py-8 sm:py-12">
    <p className="text-xs font-semibold uppercase tracking-[0.16em] text-sparq-lime">Your opportunities</p>
    <h1 id={`${id}-title`} className="mt-3 text-3xl font-semibold tracking-[-0.035em] sm:text-5xl">Find your next move.</h1>
    <p className="mt-4 max-w-2xl text-base leading-relaxed text-gray-400">Explore adult flag pathways and the people who can help.</p>
    {goal && <p className="mt-5 max-w-2xl border-l-2 border-sparq-lime/60 pl-4 text-sm leading-relaxed text-gray-300"><span className="text-gray-500">Your goal: </span>{goal}</p>}
    <form onSubmit={event => { event.preventDefault(); void search() }} className="mt-7 rounded-2xl border border-white/15 bg-white/[0.025] p-5 sm:p-6">
      <p className="text-sm font-medium">Adult flag football <span className="ml-2 text-xs font-normal text-gray-500">First collection</span></p>
      <div className="mt-4 grid grid-cols-2 items-end gap-4 sm:grid-cols-[1fr_1fr_auto]">
        <div><label htmlFor={`${id}-category`} className="mb-2 block text-xs text-gray-400">Competition category (optional)</label><select id={`${id}-category`} value={category} disabled={loading} onChange={event => { setCategory(event.target.value as OpportunityCategory); setDetailsId(null); setError(null) }} className={field}>{categories.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
        <div><label htmlFor={`${id}-format`} className="mb-2 block text-xs text-gray-400">Format</label><select id={`${id}-format`} value={format} disabled={loading} onChange={event => { setFormat(event.target.value as OpportunityFormat); setDetailsId(null); setError(null) }} className={field}>{formats.map(option => <option key={option.value} value={option.value}>{option.label}</option>)}</select></div>
        <button type="submit" disabled={loading} className={`${primary} col-span-2 sm:col-span-1`}>{loading ? 'Finding opportunities…' : 'Find opportunities'}</button>
      </div>
    </form>
    {loading && <p role="status" className="mt-5 text-sm text-gray-300">Checking the reviewed collection…</p>}
    {error && <p role="alert" className="mt-5 max-w-2xl text-sm leading-relaxed text-amber-200">{error}</p>}
    {!loading && !error && !response && <p className="mt-6 text-sm leading-relaxed text-gray-400">{result && sameScope ? 'Find opportunities again to use these search options.' : 'Choose your options, then find a few useful places to start.'}</p>}
    {response && <div className="mt-7" aria-label="Opportunity results">
      {(loading || error) && <p className="mb-4 text-xs text-gray-400">Previous results. Complete a new search before taking the next step.</p>}
      {items.length === 0 ? <div className="rounded-2xl border border-white/15 p-6"><h2 className="text-xl font-semibold">No current options in this collection.</h2><p className="mt-3 max-w-xl text-sm leading-relaxed text-gray-400">{format === 'in_person' ? 'No upcoming in-person opportunity is confirmed here. Try another format to see published pathways.' : 'No source-backed options are current for this search. Try different options or check back later.'}</p></div>
        : <div className="grid gap-4 lg:grid-cols-2">{items.map(item => <article key={item.id} className="flex min-w-0 flex-col rounded-2xl border border-white/15 bg-white/[0.025] p-5 sm:p-6" aria-labelledby={`${id}-item-${item.id}`}>
          <div className="flex flex-wrap items-center justify-between gap-2"><p className="text-xs font-medium text-gray-400">{item.organization}</p><span className="rounded-full border border-white/15 px-2.5 py-1 text-[10px] text-gray-300">{statusLabels[item.status]}</span></div>
          <h2 id={`${id}-item-${item.id}`} className="mt-4 break-words text-2xl font-semibold leading-tight tracking-tight">{item.title}</h2>
          <p className="mt-3 text-sm leading-relaxed text-gray-300">{item.relevance}</p>
          <dl className="mt-5 space-y-3 border-y border-white/10 py-4">{(item.kind === 'contact' ? ['contact'] as const : ['dates', 'location', 'cost'] as const).map(key => {
            const fact = item.facts.find(value => value.key === key)!
            return <div key={key} className="grid grid-cols-[4rem_1fr] gap-3 text-sm"><dt className="text-gray-500">{key === 'dates' ? 'Dates' : key === 'location' ? 'Place' : key === 'contact' ? 'Contact' : 'Cost'}</dt><dd className="min-w-0 break-words leading-relaxed text-gray-300">{fact.value ?? 'Not confirmed'}</dd></div>
          })}</dl>
          <div className="mt-auto pt-5">{item.action.kind === 'prepare_introduction'
            ? <button type="button" disabled={loading || !!error} onClick={() => { if (actionCurrent(item)) onPrepare(item) }} className={`${primary} w-full`}>{item.action.label}</button>
            : loading || error ? <span aria-disabled="true" className={`${primary} w-full opacity-40`}>{item.action.label}</span>
              : <a href={item.action.href} target="_blank" rel="noopener noreferrer" onClick={event => { if (!actionCurrent(item)) event.preventDefault() }} onAuxClick={event => { if (!actionCurrent(item)) event.preventDefault() }} onContextMenu={event => { if (!actionCurrent(item)) event.preventDefault() }} className={`${primary} w-full`}>{item.action.label}</a>}
            <button type="button" aria-haspopup="dialog" onClick={event => showDetails(item, event.currentTarget)} className={`${secondary} mt-2`}>Details &amp; sources<span className="sr-only"> for {item.title}</span></button>
          </div>
        </article>)}</div>}
      {response.limitations.length > 0 && <details className="mt-4"><summary className={`min-h-11 cursor-pointer py-3 text-xs text-gray-400 ${focus}`}>About this collection</summary><ul className="max-w-2xl space-y-2 pb-2 text-xs leading-relaxed text-gray-400">{response.limitations.map((limit, index) => <li key={index}>{limit}</li>)}</ul><p className="text-xs text-gray-500">Prepared {date(response.generated_at)} UTC. No one has been contacted.</p></details>}
    </div>}
    <dialog ref={dialog} aria-labelledby={`${id}-details-title`} onCancel={() => setDetailsId(null)} onClose={() => setDetailsId(null)} className="fixed inset-y-0 left-auto right-0 m-0 ml-auto h-[100dvh] max-h-none w-full max-w-xl border-0 bg-sparq-charcoal-light p-0 text-white backdrop:bg-black/70">
      {selected && <><div className="sticky top-0 z-10 flex items-center justify-between gap-4 border-b border-white/10 bg-sparq-charcoal-light px-5 py-4 sm:px-8"><h2 id={`${id}-details-title`} className="text-lg font-semibold">Opportunity details</h2><button type="button" autoFocus onClick={() => setDetailsId(null)} className={secondary}>Done</button></div>
        <div className="px-5 py-6 sm:px-8"><p className="text-xs text-gray-400">{selected.organization}</p><h3 className="mt-3 break-words text-2xl font-semibold tracking-tight">{selected.title}</h3><p className="mt-4 text-sm leading-relaxed text-gray-300">{selected.summary}</p>
          <dl className="mt-6 divide-y divide-white/10">{selected.facts.map(fact => <div key={fact.key} className="py-4"><dt className="text-xs font-medium text-gray-400">{fact.label}</dt><dd className="mt-2 break-words text-sm leading-relaxed text-gray-200">{fact.value ?? 'Not confirmed'}{fact.source_ids.length > 0 && <span className="mt-1 block text-xs text-gray-500">Sources {fact.source_ids.map(sourceId => selected.sources.findIndex(source => source.id === sourceId) + 1).join(', ')}</span>}</dd></div>)}</dl>
          <h3 className="mt-7 text-lg font-semibold">Official sources</h3><ol className="mt-3 list-decimal space-y-5 pl-5">{selected.sources.map(source => <li key={source.id} className="text-xs text-gray-400"><a href={source.url} target="_blank" rel="noopener noreferrer" onClick={event => { if (!actionCurrent(selected)) event.preventDefault() }} onAuxClick={event => { if (!actionCurrent(selected)) event.preventDefault() }} onContextMenu={event => { if (!actionCurrent(selected)) event.preventDefault() }} className={`${secondary} break-words`}>{source.title}</a><p>Checked {date(source.checked_at)} UTC · Review due {date(source.expires_at)} UTC</p></li>)}</ol>
          <p className="mt-7 text-xs leading-relaxed text-gray-500">Source dates and published requirements do not confirm your eligibility, selection or a response. Preparing an introduction does not send it.</p>
        </div></>}
    </dialog>
  </section>
}
