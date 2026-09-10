export type OpportunityCategory = 'men' | 'women' | 'unspecified'
export type OpportunityFormat = 'any' | 'remote' | 'in_person'
export type OpportunityFocus = 'national_team' | 'competition' | 'any'
export type OpportunityEntry = 'any' | 'individual' | 'team'
export interface OpportunitySource { id: string; title: string; url: string; checked_at: string; expires_at: string }
export interface OpportunityFact {
  key: 'dates' | 'location' | 'cost' | 'eligibility' | 'contact'
  label: string
  value: string | null
  source_ids: string[]
}
export interface AthleteOpportunity {
  id: string
  title: string
  organization: string
  kind: 'assessment' | 'event' | 'contact' | 'pathway'
  participation: 'individual' | 'team' | 'information'
  summary: string
  relevance: string
  status: 'registration_open' | 'published_route' | 'check_details'
  valid_until: string
  facts: OpportunityFact[]
  action: { kind: 'open_source' | 'prepare_introduction'; label: string; href: string; recipient: string | null; purpose: string | null; source_ids: string[] }
  sources: OpportunitySource[]
}
export interface AthleteOpportunitiesResponse {
  state: 'ready'
  owner_scope: string
  link_revision: string
  generated_at: string
  items: AthleteOpportunity[]
  limitations: string[]
}

export class OpportunityScopeError extends Error {}
const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const exact = (value: unknown, keys: string[]): value is Record<string, unknown> => record(value) && Object.keys(value).length === keys.length && keys.every(key => Object.hasOwn(value, key))
const invalidText = new RegExp('[\\u0000-\\u001f\\u007f\\uD800-\\uDFFF]', 'u')
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max && !!value.trim()
  && value === value.trim() && !invalidText.test(value)
const scope = (value: unknown): value is string => typeof value === 'string' && /^[a-f0-9]{64}$/.test(value)
const hosts = new Set(['usafootball.com', 'www.usafootball.com', 'gmtm.com', 'events.usafootball.com', 'iflag.org', 'www.iflag.org'])

export function isOpportunitySourceURL(value: unknown): value is string {
  if (typeof value !== 'string' || value.length > 2048 || !value.startsWith('https://')
    || /[^\x21-\x7e]|[\\%?#]/.test(value)) return false
  try {
    const url = new URL(value)
    return url.protocol === 'https:' && hosts.has(url.hostname) && !url.username && !url.password && !url.port && !url.hash
      && !url.pathname.includes('//') && !url.pathname.split('/').some(part => part === '.' || part === '..') && url.href === value
  } catch { return false }
}

function utc(value: unknown): value is string {
  if (typeof value !== 'string' || !/^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(value)) return false
  const parsed = new Date(value)
  return Number.isFinite(parsed.getTime()) && parsed.toISOString().slice(0, 10) === value.slice(0, 10)
}

// Freshness is checked again at interaction time. This is source validity,
// never evidence of individual eligibility, ability or a successful application.
export function isOpportunityCurrent(item: AthleteOpportunity, now = Date.now()): boolean {
  return Number.isFinite(now) && Date.parse(item.valid_until) > now && item.sources.length > 0
    && item.sources.every(source => Date.parse(source.checked_at) <= now && Date.parse(source.expires_at) > now)
    && item.action.source_ids.some(id => item.sources.some(source => source.id === id && source.url === item.action.href))
}

export function readAthleteOpportunities(value: unknown, expected: { ownerScope: string; linkRevision: string }, now = Date.now()): AthleteOpportunitiesResponse {
  const invalid = () => new Error('These opportunities could not be confirmed. Please try again.')
  if (!exact(value, ['state', 'owner_scope', 'link_revision', 'generated_at', 'items', 'limitations'])
    || value.state !== 'ready' || !scope(value.owner_scope) || !scope(value.link_revision)
    || !scope(expected.ownerScope) || !scope(expected.linkRevision)) throw invalid()
  if (value.owner_scope !== expected.ownerScope || value.link_revision !== expected.linkRevision) throw new OpportunityScopeError('Your profile connection changed. Reload before searching again.')
  if (!Number.isFinite(now) || !utc(value.generated_at) || Date.parse(value.generated_at) > now
    || !Array.isArray(value.items) || value.items.length > 3 || !Array.isArray(value.limitations)
    || value.limitations.length > 6 || !value.limitations.every(item => text(item, 300))) throw invalid()
  const ids = new Set<string>()
  const items = value.items.map(item => {
    if (!exact(item, ['id', 'title', 'organization', 'kind', 'participation', 'summary', 'relevance', 'status', 'valid_until', 'facts', 'action', 'sources'])
      || !text(item.id, 64) || !/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(item.id) || ids.has(item.id) || !text(item.title, 180) || !text(item.organization, 120)
      || !['assessment', 'event', 'contact', 'pathway'].includes(String(item.kind)) || !text(item.summary, 300) || !text(item.relevance, 300)
      || typeof item.participation !== 'string' || !['individual', 'team', 'information'].includes(item.participation)
      || !['registration_open', 'published_route', 'check_details'].includes(String(item.status)) || !utc(item.valid_until)
      || !Array.isArray(item.sources) || item.sources.length < 1 || item.sources.length > 8
      || !Array.isArray(item.facts) || item.facts.length !== 5) throw invalid()
    ids.add(item.id)
    const sourceIds = new Set<string>()
    const sources = item.sources.map(source => {
      if (!exact(source, ['id', 'title', 'url', 'checked_at', 'expires_at']) || !text(source.id, 64) || sourceIds.has(source.id)
        || !text(source.title, 180) || !isOpportunitySourceURL(source.url) || !utc(source.checked_at) || !utc(source.expires_at)
        || Date.parse(source.checked_at) > now || Date.parse(source.checked_at) > Date.parse(value.generated_at as string)
        || Date.parse(source.expires_at) <= Date.parse(source.checked_at) || Date.parse(item.valid_until as string) > Date.parse(source.expires_at)) throw invalid()
      sourceIds.add(source.id)
      return { ...source } as unknown as OpportunitySource
    })
    const references = (refs: unknown, nonempty: boolean) => Array.isArray(refs) && refs.length <= 8 && (!nonempty || refs.length > 0)
      && new Set(refs).size === refs.length && refs.every(id => typeof id === 'string' && sourceIds.has(id))
    const keys = new Set<string>()
    const facts = item.facts.map(fact => {
      if (!exact(fact, ['key', 'label', 'value', 'source_ids']) || !['dates', 'location', 'cost', 'eligibility', 'contact'].includes(String(fact.key))
        || keys.has(String(fact.key)) || !text(fact.label, 80)
        || !(fact.value === null ? Array.isArray(fact.source_ids) && fact.source_ids.length === 0 : text(fact.value, 600) && references(fact.source_ids, true))) throw invalid()
      keys.add(String(fact.key))
      return { ...fact, source_ids: [...fact.source_ids as string[]] } as unknown as OpportunityFact
    })
    if (item.participation !== 'information' && !facts.some(fact => fact.key === 'eligibility' && fact.value !== null && fact.source_ids.length > 0)) throw invalid()
    const action = item.action
    if (!exact(action, ['kind', 'label', 'href', 'recipient', 'purpose', 'source_ids'])
      || !['open_source', 'prepare_introduction'].includes(String(action.kind)) || !text(action.label, 100)
      || !isOpportunitySourceURL(action.href) || !references(action.source_ids, true)
      || !(action.source_ids as string[]).some(id => sources.some(source => source.id === id && source.url === action.href))
      || (action.kind === 'prepare_introduction' ? !text(action.recipient, 200) || !text(action.purpose, 600) : action.recipient !== null || action.purpose !== null)) throw invalid()
    if (action.kind === 'prepare_introduction' && !facts.some(fact => fact.key === 'contact' && fact.value !== null
      && fact.source_ids.some(id => (action.source_ids as string[]).includes(id)))) throw invalid()
    return { ...item, facts, sources, action: { ...action, source_ids: [...action.source_ids as string[]] } } as unknown as AthleteOpportunity
  })
  return { state: 'ready', owner_scope: value.owner_scope, link_revision: value.link_revision, generated_at: value.generated_at,
    items: items.filter(item => isOpportunityCurrent(item, now)), limitations: [...value.limitations] }
}
