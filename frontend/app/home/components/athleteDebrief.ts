export type DebriefTrack = 'national_team' | 'profile' | 'outreach'
export interface DebriefParagraph { text: string; refs: string[] }
export interface DebriefReference {
  id: string
  kind: 'evidence' | 'coverage' | 'official'
  label: string
  detail: string
  href: string | null
  checked_at: string | null
}
export interface AthleteDebrief {
  state: 'ready'
  track: DebriefTrack
  question: string
  answer: DebriefParagraph
  insights: DebriefParagraph[]
  unknowns: DebriefParagraph[]
  next_action: { id: string; kind: 'prepare_summary' | 'prepare_introduction' | 'open_source'; label: string; href: string | null; reason: DebriefParagraph }
  references: DebriefReference[]
  fetched_at: string
}

export const debriefTracks: { value: DebriefTrack; label: string }[] = [
  { value: 'profile', label: 'Understand my profile' },
  { value: 'national_team', label: 'USA Football adult pathway' },
  { value: 'outreach', label: 'Prepare an introduction' },
]

const officialSources: Record<string, string> = {
  o1: 'https://www.usafootball.com/national-team/digital-combine',
  o2: 'https://www.usafootball.com/contact-us',
  o3: 'https://usafootball.com/resources/app',
  o4: 'https://usafootball.com/national-team/adult-talent-id-camp',
}
const actions: Record<string, { kind: string; href: string | null; source: string | null }> = {
  prepare_summary: { kind: 'prepare_summary', href: null, source: null },
  prepare_introduction: { kind: 'prepare_introduction', href: null, source: null },
  usaf_support: { kind: 'open_source', href: officialSources.o2, source: 'o2' },
  usaf_development: { kind: 'open_source', href: officialSources.o3, source: 'o3' },
}
const object = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const exact = (value: unknown, keys: string[]): value is Record<string, unknown> => object(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key))
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max && !!value.trim()
const destination = /(?:[a-z][a-z0-9+.-]{1,20}:\/\/|\b(?:mailto|javascript|data|tel):|\bwww\.)|(?:[^\s@]+@[^\s@]+\.[^\s@]+)|(?:\b[a-z0-9][a-z0-9-]*(?:\.[a-z0-9-]+)*\.[a-z]{2,63}\b)/i
const control = /[\u0000-\u0008\u000b-\u001f]/
function utc(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(value)) return false
  const parsed = new Date(value)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value.slice(0, 10)
}

// A whole response must be trusted structurally before any generated text is shown.
// This checks provenance references, not whether the prose is a sound interpretation.
export function readAthleteDebrief(value: unknown, request: { track: DebriefTrack; question: string }): AthleteDebrief {
  const invalid = () => new Error('SPARQ could not confirm that answer. Please try again.')
  if (!exact(value, ['state', 'track', 'question', 'answer', 'insights', 'unknowns', 'next_action', 'references', 'fetched_at'])
    || value.state !== 'ready' || value.track !== request.track || value.question !== request.question
    || !debriefTracks.some(track => track.value === value.track) || !text(value.question, 1000) || value.question !== value.question.trim()
    || !utc(value.fetched_at) || !Array.isArray(value.references) || value.references.length < 1 || value.references.length > 55
    || !Array.isArray(value.insights) || value.insights.length > 3 || !Array.isArray(value.unknowns) || value.unknowns.length > 2) throw invalid()
  const refs = new Set<string>()
  for (const ref of value.references) {
    if (!exact(ref, ['id', 'kind', 'label', 'detail', 'href', 'checked_at']) || !text(ref.id, 20) || refs.has(ref.id)
      || !text(ref.label, 300) || !text(ref.detail, 700) || !(ref.checked_at === null || utc(ref.checked_at))) throw invalid()
    if (ref.kind === 'official') {
      if (request.track !== 'national_team' || !Object.hasOwn(officialSources, ref.id) || ref.href !== officialSources[ref.id] || ref.checked_at === null) throw invalid()
    } else if (ref.kind === 'coverage') {
      if (ref.id !== 'coverage' || ref.href !== null) throw invalid()
    } else if (ref.kind === 'evidence') {
      if (!/^f(?:[1-9]|[1-4]\d|50)$/.test(ref.id) || !(ref.href === null || typeof ref.href === 'string' && /^https:\/\/gmtm\.com\/film\/[1-9]\d*$/.test(ref.href) && Number.isSafeInteger(Number(ref.href.split('/').at(-1))))) throw invalid()
    } else throw invalid()
    refs.add(ref.id)
  }
  const used = new Set<string>()
  const paragraph = (part: unknown) => {
    if (!exact(part, ['text', 'refs']) || !text(part.text, 700) || destination.test(part.text) || control.test(part.text)
      || !Array.isArray(part.refs) || part.refs.length < 1 || part.refs.length > 6
      || new Set(part.refs).size !== part.refs.length || !part.refs.every(id => typeof id === 'string' && refs.has(id))) throw invalid()
    part.refs.forEach(id => used.add(id as string))
  }
  paragraph(value.answer)
  value.insights.forEach(paragraph)
  value.unknowns.forEach(paragraph)
  const action = value.next_action
  if (!exact(action, ['id', 'kind', 'label', 'href', 'reason']) || !text(action.id, 40) || !Object.hasOwn(actions, action.id) || !text(action.label, 700)) throw invalid()
  const expected = actions[action.id]
  if (action.kind !== expected.kind || action.href !== expected.href || expected.source !== null && (request.track !== 'national_team' || !refs.has(expected.source))) throw invalid()
  paragraph(action.reason)
  if (expected.source) used.add(expected.source)
  if (refs.size !== used.size || Array.from(refs).some(id => !used.has(id))) throw invalid()
  return value as unknown as AthleteDebrief
}

export function debriefFailure(status: number, code?: string): string {
  if (code === 'pathway_sources_expired') return 'USA Football sources need a fresh review. You can still ask about your profile or prepare an introduction.'
  if (status === 401) return 'Please sign in again before asking SPARQ.'
  if (status === 403 || status === 409) return 'Your profile connection could not be confirmed for this answer. Check your connection or refresh your profile.'
  if (status === 429) return 'SPARQ is at its request limit. Wait a moment before trying again.'
  if (status === 503) return 'SPARQ is unavailable right now. Your profile and manual text preparation are still available.'
  return 'SPARQ could not complete this answer. Please try again. Your profile and draft have not been changed.'
}
