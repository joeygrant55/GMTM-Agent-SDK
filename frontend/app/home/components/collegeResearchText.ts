// Plain text and link rules for "Team now" and "Camps" (no React, so the safety check can load it).
// Only listed counts with the season label. Never "open spots", "need" or "leave".
export interface Roster {
  season: string; by_class: Record<string, number>; by_position: Record<string, number>; total: number; source_url: string
}
export interface Camp {
  name: string; date_text: string; start_date: string; end_date: string; location: string | null; cost_usd: number | null
  eligibility_text: string | null; registration_url: string | null; source_url: string
}
export interface Research { program_id: string; roster: Roster | null; roster_checked: string | null; camps: Camp[]; camps_checked: string | null }

const CLASS_WORDS: Array<[string, string, string]> = [['Fr', 'freshman', 'freshmen'], ['So', 'sophomore', 'sophomores'],
  ['Jr', 'junior', 'juniors'], ['Sr', 'senior', 'seniors'], ['Grad', 'graduate student', 'graduate students'],
  ['Unknown', 'with no class listed', 'with no class listed']]
const POSITIONS = ['QB', 'WR', 'RB', 'C', 'DB', 'LB', 'R', 'Other']
const POSITION_WORDS: Record<string, string> = { R: 'rusher', Other: 'other' }

export const https = (url: string | null | undefined): string | null => {
  if (typeof url !== 'string' || !url.startsWith('https://')) return null
  try { return new URL(url).protocol === 'https:' ? url : null } catch { return null }
}
export const hostOf = (url: string): string => { try { return new URL(url).hostname.replace(/^www\./, '') } catch { return '' } }

// "Oct 2, 2026" from an ISO date (the server already converted to the America/New_York day).
export function checkedLabel(iso: string | null): string | null {
  if (!iso || !/^\d{4}-\d{2}-\d{2}$/.test(iso)) return null
  const [y, m, d] = iso.split('-').map(Number)
  return new Intl.DateTimeFormat('en-US', { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' }).format(new Date(Date.UTC(y, m - 1, d)))
}
export function isOld(iso: string | null, today = new Date()): boolean {
  if (!iso) return true
  return today.getTime() - new Date(`${iso}T12:00:00Z`).getTime() > 14 * 24 * 3600 * 1000
}

// Only listed counts with the season label. No inference about who leaves or what a team needs.
export function teamSentence(roster: Roster): string {
  const parts = CLASS_WORDS.filter(([k]) => roster.by_class[k]).map(([k, one, many]) => `${roster.by_class[k]} ${roster.by_class[k] === 1 ? one : many}`)
  const players = `${roster.total} ${roster.total === 1 ? 'player' : 'players'}`
  return `The ${roster.season} roster lists ${players}${parts.length ? `: ${parts.join(', ')}` : ''}.`
}
export function positionLine(roster: Roster): string | null {
  const parts = POSITIONS.filter(p => roster.by_position[p]).map(p => `${roster.by_position[p]} ${POSITION_WORDS[p] || p}`)
  return parts.length ? `By first listed position: ${parts.join(', ')}.` : null
}
export function campLink(camp: Camp): { href: string; label: string } | null {
  const reg = https(camp.registration_url)
  if (reg) return { href: reg, label: `Register (opens ${hostOf(reg)})` }
  const src = https(camp.source_url)
  return src ? { href: src, label: 'See camp page' } : null
}
export const costLabel = (cost: number | null | undefined) => (typeof cost !== 'number' || !Number.isFinite(cost) ? 'Cost not listed' : cost === 0 ? 'Free' : `$${Math.round(cost)}`)
