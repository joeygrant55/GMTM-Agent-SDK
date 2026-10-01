export const COMBINE_EVENT_IDS = [1317, 1318] as const

export function supportedCombineEvent(value: unknown): number | null {
  return COMBINE_EVENT_IDS.includes(value as 1317 | 1318) ? value as number : null
}

export interface CombineEvent {
  event_id: number
  name: string
  division: string
  continuation_url: string
}

export interface CombineActivity {
  task_id: number
  event_id: number
  title: string
  order: number
  kind: 'background' | 'highlight' | 'exercise'
  description: string
  continuation_url: string
  submission_state: 'not_submitted' | 'submitted' | 'unavailable'
  evidence_state: 'missing_fields' | 'fields_present' | 'unknown'
  missing_fields: string[]
  required_field_count: number
  required_fields?: { type: string; title: string }[] | null
  submitted_at: string | null
}

export interface CurrentCombine {
  schema_version: 1
  clerk_id: string
  athlete_id: number | null
  state: 'ready' | 'choose_event' | 'link_required'
  events: CombineEvent[]
  selected_event: (CombineEvent & {
    deadline_display: string
    deadline_source_url: string
    configured_end: string | null
  }) | null
  activities: CombineActivity[]
  counts: { activities: number; submitted: number | null; fields_present: number | null }
  fetched_at: string
  athlete_id_status: 'unknown'
}

export const PROGRAM_SOURCE = 'https://usafootball.com/national-team/digital-combine'

function validEvent(event: CombineEvent): boolean {
  return !!event && supportedCombineEvent(event.event_id) !== null
    && typeof event.name === 'string' && typeof event.division === 'string'
    && event.continuation_url === `https://gmtm.com/virtuals/${event.event_id}`
}

// Treat malformed or foreign-account snapshots as failed reads, never as empty progress.
export function readCurrentCombine(value: unknown, ownerId: string, eventId: number | null): CurrentCombine {
  const data = value as CurrentCombine
  const count = (v: unknown) => Number.isSafeInteger(v) && Number(v) >= 0
  if (!data || data.schema_version !== 1 || data.clerk_id !== ownerId
    || !['ready', 'choose_event', 'link_required'].includes(data.state)
    || !(data.athlete_id === null || (count(data.athlete_id) && data.athlete_id > 0))
    || !Array.isArray(data.events) || !data.events.every(validEvent)
    || new Set(data.events.map(e => e.event_id)).size !== data.events.length
    || !Array.isArray(data.activities) || !data.activities.every(a => !!a && typeof a === 'object' && !Array.isArray(a)) || !data.counts
    || (data.selected_event !== null && (!data.selected_event || typeof data.selected_event !== 'object' || Array.isArray(data.selected_event)))
    || !count(data.counts.activities) || data.counts.activities !== data.activities.length
    || ![data.counts.submitted, data.counts.fields_present].every(v => v === null || (count(v) && v <= data.counts.activities))
    || typeof data.fetched_at !== 'string' || !Number.isFinite(Date.parse(data.fetched_at))
    || data.athlete_id_status !== 'unknown') throw new Error('Combine progress was not confirmed')
  const event = data.selected_event
  if ((eventId !== null && event?.event_id !== eventId)
    || (event && (!validEvent(event) || !data.events.some(e => e.event_id === event.event_id)
      || typeof event.deadline_display !== 'string' || event.deadline_source_url !== PROGRAM_SOURCE))
    || (!event && data.activities.length > 0)
    || new Set(data.activities.map(a => a.task_id)).size !== data.activities.length) throw new Error('Combine event was not confirmed')
  for (const a of data.activities) {
    if (!a || !count(a.task_id) || a.task_id <= 0 || a.event_id !== event?.event_id
      || typeof a.title !== 'string' || !count(a.order) || typeof a.description !== 'string'
      || a.continuation_url !== event?.continuation_url
      || !['background', 'highlight', 'exercise'].includes(a.kind)
      || !['not_submitted', 'submitted', 'unavailable'].includes(a.submission_state)
      || !['missing_fields', 'fields_present', 'unknown'].includes(a.evidence_state)
      || !Array.isArray(a.missing_fields) || !a.missing_fields.every(f => typeof f === 'string')
      || !count(a.required_field_count)
      || (a.required_fields != null && (!Array.isArray(a.required_fields)
        || a.required_fields.length !== a.required_field_count || a.required_fields.length > 100
        || !a.required_fields.every(f => f && typeof f === 'object' && !Array.isArray(f)
          && typeof f.type === 'string' && f.type.length > 0 && f.type.length <= 100
          && typeof f.title === 'string' && f.title.trim().length > 0 && f.title.length <= 2000)))
      || (a.submitted_at !== null && (typeof a.submitted_at !== 'string' || !Number.isFinite(Date.parse(a.submitted_at))))) throw new Error('Combine activities were not confirmed')
  }
  if (data.athlete_id === null) {
    if (data.state !== 'link_required' || data.counts.submitted !== null || data.counts.fields_present !== null
      || data.activities.some(a => a.submission_state !== 'unavailable' || a.evidence_state !== 'unknown'
        || a.missing_fields.length > 0 || a.submitted_at !== null)) throw new Error('Personal progress was not confirmed')
  } else if (!event) {
    if (data.state !== 'choose_event' || data.counts.submitted !== null || data.counts.fields_present !== null) throw new Error('Combine choice was not confirmed')
  } else if (data.counts.submitted !== data.activities.filter(a => a.submission_state === 'submitted').length
    || data.counts.fields_present !== data.activities.filter(a => a.evidence_state === 'fields_present').length
    || data.activities.some(a => a.submission_state === 'unavailable'
      || (a.evidence_state === 'fields_present' && (a.submission_state !== 'submitted' || a.required_field_count === 0 || a.missing_fields.length > 0)))
    || data.state !== (event ? 'ready' : 'choose_event')) throw new Error('Progress counts were not confirmed')
  return data
}
