// Pure helpers for the junior profile pages (no React): the journey and school badges.

// The four-step recruiting journey on Home, computed from real data only.
// "Save your top 3": three saved colleges (the design said 5; 3 is a reachable first goal for a 13-17 year old).
export const SAVE_TARGET = 3

export interface JourneyInput {
  profileReady: boolean // GMTM has footage or a drill result
  found: number // programs in her built college list
  saved: number
  sent: number // drafts she marked "I sent it"
}

export interface JourneyStep { key: 'profile' | 'colleges' | 'save' | 'email'; title: string; detail: string; done: boolean }

export function journey({ profileReady, found, saved, sent }: JourneyInput) {
  const steps: JourneyStep[] = [
    { key: 'profile', title: 'Profile ready', detail: profileReady ? 'Clip or numbers on GMTM' : 'Add a clip or a result on GMTM', done: profileReady },
    { key: 'colleges', title: found > 0 ? `${found} colleges found` : 'Colleges found', detail: found > 0 ? 'Near you first, every level' : 'See programs that fit you', done: found > 0 },
    { key: 'save', title: `Save your top ${SAVE_TARGET}`, detail: `${Math.min(saved, SAVE_TARGET)} of ${SAVE_TARGET} saved`, done: saved >= SAVE_TARGET },
    { key: 'email', title: 'Email a coach', detail: sent > 0 ? `${sent} sent so far` : '0 sent so far', done: sent > 0 },
  ]
  const done = steps.filter(step => step.done).length
  const current = steps.find(step => !step.done) || null
  // Steps left before the first coach email, counting the email itself.
  const left = sent > 0 ? 0 : steps.filter(step => !step.done).length
  const headline = sent > 0 ? 'You emailed your first coach.' : left === 1 ? 'You’re 1 step from your first coach email.' : `You’re ${left} steps from your first coach email.`
  return { steps, done, current, left, headline, percent: Math.round((done / steps.length) * 100) }
}

// School-color monogram: white or near-black text, whichever contrasts more. Badges use 14px
// text, so both must reach 4.5:1; if neither does, the color is darkened until white does.
// No color: neutral.
function luminance(hex: string) {
  const [r, g, b] = [1, 3, 5].map(i => parseInt(hex.slice(i, i + 2), 16) / 255).map(c => (c <= 0.03928 ? c / 12.92 : ((c + 0.055) / 1.055) ** 2.4))
  return 0.2126 * r + 0.7152 * g + 0.0722 * b
}
export function contrast(a: string, b: string): number {
  const [x, y] = [luminance(a), luminance(b)].sort((m, n) => n - m)
  return (x + 0.05) / (y + 0.05)
}
const darken = (hex: string, factor: number) => '#' + [1, 3, 5].map(i => Math.round(parseInt(hex.slice(i, i + 2), 16) * factor).toString(16).padStart(2, '0')).join('')
export function badgeColors(color: string | null): { background: string; color: string } {
  if (!color || !/^#[0-9A-Fa-f]{6}$/.test(color)) return { background: '#26262C', color: '#F4F4F5' }
  const text = contrast(color, '#FFFFFF') >= contrast(color, '#0B0B0C') ? '#FFFFFF' : '#0B0B0C'
  if (contrast(color, text) >= 4.5) return { background: color, color: text }
  let background = color
  for (let factor = 0.95; contrast(background, '#FFFFFF') < 4.5 && factor > 0; factor -= 0.05) background = darken(color, factor)
  return { background, color: '#FFFFFF' }
}

// Map window (percent of the whole-US map) around her city and her listed programs, padded,
// never smaller than MIN_SPAN so a one-state list stays readable, kept at the map's 8:5 shape.
export interface MapPoint { x: number; y: number }
export const MIN_SPAN = 22 // percent of the US map width (about a few states)
export function mapWindow(points: MapPoint[]): { x: number; y: number; w: number; h: number } {
  if (!points.length) return { x: 0, y: 0, w: 100, h: 100 }
  const xs = points.map(p => p.x), ys = points.map(p => p.y)
  // The window keeps the map's 8:5 shape, so its width and height are the same percent of the map.
  let w = Math.max(Math.max(...xs) - Math.min(...xs), Math.max(...ys) - Math.min(...ys)) * 1.25 + 8
  w = Math.min(100, Math.max(MIN_SPAN, w))
  const h = w // same shape as the full map: equal percent spans keep 8:5
  const cx = (Math.max(...xs) + Math.min(...xs)) / 2, cy = (Math.max(...ys) + Math.min(...ys)) / 2
  const clamp = (v: number, span: number) => Math.min(100 - span, Math.max(0, v - span / 2))
  return { x: clamp(cx, w), y: clamp(cy, h), w, h }
}
export function initials(school: string): string {
  const words = school.replace(/[^A-Za-z\s-]/g, ' ').split(/[\s-]+/).filter(w => w && !/^(of|the|at|and|in)$/i.test(w))
  return (words.slice(0, 2).map(w => w[0]).join('') || '?').toUpperCase()
}

// Up to 4 school labels on the map, none on top of another label or the "You" pin and its text.
// Distances are in percent of the whole map; `view` is the visible window (mapWindow).
// A label is about 16% of the window wide and 8% tall, centered on its point. "You" sits right
// of her dot, so her pin blocks a box from just left of the dot to about 18% of the window right of it.
export function chooseLabels<T extends { map: { x: number; y: number } | null }>(
  placed: T[], origin: { x: number; y: number } | null, view: { w: number; h: number }, max = 4,
): T[] {
  const w = view.w * 0.16, h = view.h * 0.08
  const clearOfYou = (m: { x: number; y: number }) => !origin
    || m.x + w / 2 < origin.x - view.w * 0.03 || m.x - w / 2 > origin.x + view.w * 0.18 || Math.abs(m.y - origin.y) > h
  const out: T[] = []
  for (const p of placed) {
    if (out.length >= max || !p.map) continue
    const m = p.map
    if (clearOfYou(m) && out.every(q => Math.abs(q.map!.x - m.x) > w || Math.abs(q.map!.y - m.y) > h)) out.push(p)
  }
  return out
}
