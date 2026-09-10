import { apiFetch } from '@/app/_lib/api'
import { AthleteOpportunitiesResponse, AthleteOpportunity, isOpportunityCurrent } from './opportunityEvidence'

type EngagementKind = 'card_visible' | 'details_opened' | 'outbound_activated'
export interface OpportunityEngagement {
  sync: () => void
  record: (kind: EngagementKind, item: AthleteOpportunity) => void
  destroy: () => void
}

// A mounted result can produce at most three kinds for each of three cards.
// Account-level deduplication across sessions belongs to the server report.
export function createOpportunityEngagement({ result, root, isActive, canObserve }: {
  result: AthleteOpportunitiesResponse
  root: HTMLElement
  isActive: () => boolean
  canObserve: () => boolean
}): OpportunityEngagement | null {
  if (process.env.NEXT_PUBLIC_OPPORTUNITY_ENGAGEMENT_ENABLED !== 'true') return null
  const items = new Map(result.items.slice(0, 3).map(item => [item.id, item]))
  const seen = new Set<string>()
  const pending = new Set<AbortController>()
  const dwell = new Map<string, number>()
  let observer: IntersectionObserver | null = null
  let destroyed = false
  const active = () => !destroyed && isActive() && document.visibilityState === 'visible'
  const observable = () => active() && canObserve() && !document.querySelector('dialog[open]')
  const eligible = (item: AthleteOpportunity) => active() && items.get(item.id) === item && isOpportunityCurrent(item)
  const clearDwell = (id: string) => { const timer = dwell.get(id); if (timer !== undefined) window.clearTimeout(timer); dwell.delete(id) }
  const pause = () => {
    observer?.disconnect(); observer = null
    for (const id of Array.from(dwell.keys())) clearDwell(id)
  }
  const record = (kind: EngagementKind, item: AthleteOpportunity) => {
    const key = `${kind}:${item.id}`
    if (!eligible(item) || kind === 'card_visible' && !observable() || seen.has(key) || seen.size >= 9 || pending.size >= 9) return
    // Unsupported UUID generation simply drops measurement; it never blocks use.
    let eventId: string
    try { eventId = crypto.randomUUID() } catch { return }
    seen.add(key)
    const controller = new AbortController()
    pending.add(controller)
    const finish = () => { window.clearTimeout(timer); pending.delete(controller) }
    const timer = window.setTimeout(() => { controller.abort(); finish() }, 4000)
    controller.signal.addEventListener('abort', finish, { once: true })
    void apiFetch('/api/athlete/opportunities/engagement', {
      method: 'POST', cache: 'no-store', signal: controller.signal,
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ event_id: eventId, opportunity_id: item.id, kind,
        link_revision: result.link_revision, reviewed_at: item.sources[0].checked_at }),
    }).then(response => { void response.body?.cancel().catch(() => {}) }).catch(() => {}).finally(finish)
  }
  const sync = () => {
    if (!observable()) { pause(); return }
    if (observer || typeof IntersectionObserver === 'undefined') return
    const watching = new IntersectionObserver(entries => {
      if (observer !== watching || !observable()) return
      for (const entry of entries) {
        const id = (entry.target as HTMLElement).dataset.opportunityId
        const item = id ? items.get(id) : undefined
        if (!item) continue
        if (!entry.isIntersecting || entry.intersectionRatio < 0.5 || !eligible(item)) { clearDwell(item.id); continue }
        if (seen.has(`card_visible:${item.id}`) || dwell.has(item.id)) continue
        dwell.set(item.id, window.setTimeout(() => {
          dwell.delete(item.id)
          if (observer === watching) record('card_visible', item)
        }, 1000))
      }
    }, { threshold: [0, 0.5, 1] })
    observer = watching
    for (const element of Array.from(root.querySelectorAll<HTMLElement>('[data-opportunity-id]'))) {
      if (items.has(element.dataset.opportunityId || '')) watching.observe(element)
    }
  }
  // A parent draft-confirmation dialog also occludes cards without changing
  // their geometric intersection. Observe only open-attribute changes.
  const modalChanges = new MutationObserver(changes => {
    if (changes.some(change => change.target instanceof HTMLDialogElement)) sync()
  })
  modalChanges.observe(document.body, { subtree: true, attributes: true, attributeFilter: ['open'] })
  document.addEventListener('visibilitychange', sync)
  sync()
  return { sync, record, destroy: () => {
    destroyed = true; pause(); modalChanges.disconnect(); document.removeEventListener('visibilitychange', sync)
    for (const controller of Array.from(pending)) controller.abort()
    pending.clear(); seen.clear(); items.clear()
  } }
}
