export interface ProfileAthlete {
  name: string | null
  sport: string | null
  position: string | null
  school: string | null
  city: string | null
  state: string | null
  graduation_year: number | null
}

export interface ProfileEvidenceItem {
  id: string
  label: string
  value: number
  unit: string
  recorded_at: string | null
  source_label: string
  verification: 'unconfirmed'
  event_name?: string
}

export interface ProfileEvidence {
  owner_scope?: string | null
  state: 'ready' | 'unlinked' | 'source_unavailable'
  athlete: ProfileAthlete | null
  evidence: ProfileEvidenceItem[]
  observations: { title: string; detail: string; evidence_ids: string[] }[]
  limitations: string[]
  fetched_at: string
}

const record = (value: unknown): value is Record<string, unknown> => !!value && typeof value === 'object' && !Array.isArray(value)
const text = (value: unknown, max = 2000): value is string => typeof value === 'string' && value.length <= max
const hasZone = (value: string) => /(?:Z|[+-]\d{2}:\d{2})$/.test(value)
function date(value: unknown): value is string {
  if (!text(value, 40) || !/^\d{4}-\d{2}-\d{2}(?:[T ](?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|[+-]\d{2}:\d{2})?)?$/.test(value)) return false
  const calendar = new Date(`${value.slice(0, 10)}T00:00:00Z`)
  return Number.isFinite(calendar.getTime()) && calendar.toISOString().slice(0, 10) === value.slice(0, 10)
    && Number.isFinite(Date.parse(value.length === 10 ? value : hasZone(value) ? value : `${value.replace(' ', 'T')}Z`))
}

// Unknown or contradictory data is a failed read, never an invented empty profile.
export function readProfileEvidence(value: unknown): ProfileEvidence {
  const invalid = () => new Error('Your profile could not be confirmed. Please try again.')
  if (!record(value) || !['ready', 'unlinked', 'source_unavailable'].includes(String(value.state))
    || !(value.owner_scope === undefined || value.owner_scope === null || typeof value.owner_scope === 'string' && /^[a-f0-9]{64}$/.test(value.owner_scope))
    || !date(value.fetched_at) || !/(?:Z|\+00:00)$/.test(value.fetched_at)
    || !Array.isArray(value.evidence) || value.evidence.length > 20 || !Array.isArray(value.observations) || value.observations.length > 20
    || !Array.isArray(value.limitations) || value.limitations.length > 20 || !value.limitations.every(item => text(item))) throw invalid()
  if (value.athlete !== null) {
    const athlete = value.athlete
    if (!record(athlete)
      || !['name', 'sport', 'position', 'school', 'city', 'state'].every(key => athlete[key] === null || text(athlete[key], key === 'name' ? 201 : 160))
      || !(athlete.graduation_year === null || Number.isSafeInteger(athlete.graduation_year) && Number(athlete.graduation_year) >= 1900 && Number(athlete.graduation_year) <= 2200)) throw invalid()
  }
  if (value.state === 'ready' ? value.athlete === null : value.athlete !== null || value.evidence.length > 0 || value.observations.length > 0) throw invalid()
  const ids = new Set<string>()
  for (const item of value.evidence) {
    if (!record(item) || !text(item.id, 100) || !item.id.trim() || ids.has(item.id)
      || !text(item.label, 75) || !item.label.trim() || typeof item.value !== 'number' || !Number.isFinite(item.value)
      || !text(item.unit, 25) || !text(item.source_label, 160) || !item.source_label.trim()
      || item.verification !== 'unconfirmed' || !(item.recorded_at === null || date(item.recorded_at))
      || !(item.event_name === undefined || text(item.event_name, 300))) throw invalid()
    ids.add(item.id)
  }
  if (!value.observations.every(item => record(item) && text(item.title, 160) && text(item.detail)
    && Array.isArray(item.evidence_ids) && item.evidence_ids.length <= 20 && item.evidence_ids.every(id => text(id, 100) && ids.has(id)))) throw invalid()
  return value as unknown as ProfileEvidence
}

export function evidenceDate(value: string | null): string {
  if (!value) return 'Date not recorded'
  // A naive MySQL datetime has no confirmed timezone: retain its calendar date.
  const instant = hasZone(value) ? value : `${value.slice(0, 10)}T00:00:00Z`
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(instant))
}

export function evidenceValue(item: ProfileEvidenceItem): string {
  return `${item.value}${item.unit ? ` ${item.unit}` : ''}`
}

// GMTM's generic "All Sports" (or no sport) is not shown as a subtitle.
export function knownSport(sport: string | null | undefined): string | null {
  const value = sport?.trim()
  return value && value.toLowerCase() !== 'all sports' ? value : null
}

// One key per drill across GMTM spellings: "Max. Push-Ups" = "Push-Ups", "5-10-5 Shuttle Run" = "5-10-5 Shuttle".
export function drillKey(label: string): string {
  return label.trim().toLowerCase().replace(/^max\.?\s*/, '').replace(/\s*run$/, '').replace(/[^a-z0-9]/g, '')
}

// Height and weight are body size, not combine results.
export function isBodySize(label: string): boolean {
  return ['height', 'weight'].includes(drillKey(label))
}
