// Contract for `GET /api/dashboard/{user_id}`.combine_results (cohort-one spec 1c / 2c).
// The backend field may be missing or empty; every consumer must handle both.

export type TrustTier = 'Remote App-Captured' | 'Official In-Person'

export interface CombineResult {
  event_id: number
  event_name: string
  organization: string
  drill: string
  value: number
  unit: string
  ideal: 'lower' | 'higher'
  video_uri: string | null
  submitted_on: string
  trust_tier: TrustTier
  rank_in_event: number | null
  event_pool_size: number | null
  /** Percentile among every GMTM row with the same drill, 0-100, higher is better. */
  pct_flag_all_time: number | null
  pool_size_all_time: number | null
  /** Percentile among rows from the same organization, 0-100, higher is better. */
  pct_same_org: number | null
}

export function readCombineResults(data: unknown): CombineResult[] {
  const raw = (data as { combine_results?: unknown } | null)?.combine_results
  if (!Array.isArray(raw)) return []
  return raw.filter(
    (r): r is CombineResult =>
      !!r && typeof r === 'object' && typeof (r as CombineResult).drill === 'string' && (r as CombineResult).value != null,
  )
}

export function ordinal(n: number): string {
  const v = n % 100
  if (v >= 11 && v <= 13) return `${n}th`
  switch (n % 10) {
    case 1: return `${n}st`
    case 2: return `${n}nd`
    case 3: return `${n}rd`
    default: return `${n}th`
  }
}

export function formatValue(r: Pick<CombineResult, 'value' | 'unit'>): string {
  const n = Number(r.value)
  const text = Number.isFinite(n) ? (Number.isInteger(n) ? String(n) : n.toFixed(2).replace(/0$/, '')) : String(r.value)
  const unit = (r.unit || '').trim()
  if (!unit) return text
  // Short units hug the number (4.31s); word units get a space (12 reps).
  return unit.length <= 2 ? `${text}${unit}` : `${text} ${unit}`
}

/** "top 18%" from a 0-100 percentile where higher is better. Never shows top 0%. */
export function topPercent(pct: number): number {
  return Math.max(1, Math.round(100 - pct))
}

export function rankLine(r: CombineResult): string | null {
  if (r.rank_in_event == null || r.event_pool_size == null) return null
  return `${ordinal(r.rank_in_event)} of ${r.event_pool_size} in ${r.event_name}`
}

export function percentileLine(r: CombineResult): string | null {
  if (r.pct_flag_all_time == null || r.pool_size_all_time == null) return null
  return `top ${topPercent(r.pct_flag_all_time)}% of ${r.pool_size_all_time} flag athletes`
}

/** First chat line when the athlete has combine results (spec 2c). */
export function combineGreeting(firstName: string, results: CombineResult[]): string | null {
  const r = results[0]
  if (!r) return null
  const where = r.rank_in_event != null && r.event_pool_size != null
    ? `${ordinal(r.rank_in_event)} of ${r.event_pool_size} in ${r.event_name}`
    : `in ${r.event_name}`
  return `What's up ${firstName}! 👋 Your ${r.drill} was ${formatValue(r)}, ${where}. Want to know which programs care about that?`
}

// Local fixture, 3 entries shaped like event 1317 rows. Rendered only when
// NEXT_PUBLIC_COMBINE_FIXTURE=1 and the backend sent no combine_results.
export const COMBINE_FIXTURE: CombineResult[] = [
  {
    event_id: 1317,
    event_name: '2027 U.S. Flag National Team Junior Digital Combine #2',
    organization: 'USA Football',
    drill: '20-Yard Dash',
    value: 2.91,
    unit: 's',
    ideal: 'lower',
    video_uri: 'https://cdn.gmtm.com/example/20yd.mp4',
    submitted_on: '2026-08-29T18:12:00Z',
    trust_tier: 'Remote App-Captured',
    rank_in_event: 4,
    event_pool_size: 87,
    pct_flag_all_time: 82,
    pool_size_all_time: 167,
    pct_same_org: 85,
  },
  {
    event_id: 1317,
    event_name: '2027 U.S. Flag National Team Junior Digital Combine #2',
    organization: 'USA Football',
    drill: '5-10-5 Shuttle',
    value: 4.31,
    unit: 's',
    ideal: 'lower',
    video_uri: 'https://cdn.gmtm.com/example/shuttle.mp4',
    submitted_on: '2026-08-29T18:15:00Z',
    trust_tier: 'Remote App-Captured',
    rank_in_event: 12,
    event_pool_size: 87,
    pct_flag_all_time: 61,
    pool_size_all_time: 1072,
    pct_same_org: null,
  },
  {
    event_id: 1317,
    event_name: '2027 U.S. Flag National Team Junior Digital Combine #2',
    organization: 'USA Football',
    drill: 'Standing Broad Jump',
    value: 8.5,
    unit: 'ft',
    ideal: 'higher',
    video_uri: null,
    submitted_on: '2026-08-29T18:20:00Z',
    trust_tier: 'Remote App-Captured',
    rank_in_event: 20,
    event_pool_size: 80,
    pct_flag_all_time: null,
    pool_size_all_time: null,
    pct_same_org: null,
  },
]
