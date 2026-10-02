// Pure helpers for "My card" (no React): the card response check and the highlight picker.
import { isProfileThumbnail } from './profileMaterials'
// The backend owner-checks and re-checks every pick; these only keep the page honest.

export const CARD_MAX = 3

export interface CardClip {
  id: string; title: string; source_label: string; recorded_at: string | null
  thumbnail_url: string | null; source_url: string; video_url: string | null; reel: boolean
}
export interface CardData {
  state: 'ready' | 'unlinked' | 'source_unavailable'
  clips: CardClip[]
  order: string[] // her picks (first = lead), or one default clip when she has not picked
  chosen: boolean
  share: { profile_url: string | null; settings_url: string | null } | null // null on Home's lead-only read
}

const FILM_PAGE = /^https:\/\/gmtm\.com\/film\/[1-9][0-9]{0,15}$/
// A direct clip file on GMTM's CDN (the backend path-encodes it): a video file, or an
// extensionless GMTM upload under videos/ (junior Highlight Reels), or a GMTM-processed upload
// (films/<uuid>-processed, users/<id>/uploads/metrics/<uuid>-processed; measured 2026-10-02). Nothing else plays inline.
const VIDEO = /^https:\/\/cdn\.gmtm\.com\/(?:[A-Za-z0-9_+()%][A-Za-z0-9_.+()%/-]*\.(?:mp4|m4v|mov|webm)|videos(?:\/[A-Za-z0-9_-]+){2,9}|(?:films|users\/[1-9][0-9]{0,15}\/uploads\/metrics)\/[0-9a-f]{8}(?:-[0-9a-f]{4}){3}-[0-9a-f]{12}-processed)$/i
const PROFILE = /^https:\/\/gmtm\.com\/athletes\/[1-9][0-9]{0,15}$/
const text = (value: unknown, max: number): value is string => typeof value === 'string' && value.length <= max && !/[\u0000-\u001f\u007f]/.test(value)

export function isCardVideo(value: unknown): value is string {
  return typeof value === 'string' && value.length <= 600 && VIDEO.test(value) && !/(?:^|\/)\.\.?(?:\/|$)|\/\//.test(value.slice(8))
}

// Stored film posters (GMTM CDN or YouTube); the same namespaces as the profile CSP img-src.
export function isCardPoster(value: unknown): value is string {
  return isProfileThumbnail(value)
}

export function readCard(value: unknown): CardData {
  const bad = () => new Error('Your card could not be confirmed.')
  const v = value as Record<string, unknown>
  if (!v || typeof v !== 'object' || !['ready', 'unlinked', 'source_unavailable'].includes(String(v.state))
    || !Array.isArray(v.clips) || v.clips.length > 10 || !Array.isArray(v.order) || v.order.length > CARD_MAX
    || typeof v.chosen !== 'boolean' || (v.share !== null && typeof v.share !== 'object')) throw bad()
  const share = (v.share || { profile_url: null, settings_url: null }) as Record<string, unknown>
  const profile = share.profile_url === null || (typeof share.profile_url === 'string' && PROFILE.test(share.profile_url)) ? share.profile_url as string | null : undefined
  const settings = share.settings_url === null || share.settings_url === 'https://gmtm.com/settings' ? share.settings_url as string | null : undefined
  if (profile === undefined || settings === undefined) throw bad()
  const ids = new Set<string>()
  const clips = v.clips.map((raw): CardClip => {
    const c = raw as Record<string, unknown>
    if (!c || typeof c !== 'object' || !text(c.id, 40) || !/^film-[1-9][0-9]{0,15}$/.test(c.id) || ids.has(c.id)
      || !text(c.title, 300) || !text(c.source_label, 400) || !(c.recorded_at === null || text(c.recorded_at, 40))
      || typeof c.source_url !== 'string' || !FILM_PAGE.test(c.source_url) || typeof c.reel !== 'boolean') throw bad()
    ids.add(c.id)
    return { id: c.id, title: c.title || 'Untitled footage', source_label: c.source_label, recorded_at: c.recorded_at as string | null,
      thumbnail_url: isCardPoster(c.thumbnail_url) ? c.thumbnail_url : null, source_url: c.source_url,
      video_url: isCardVideo(c.video_url) ? c.video_url : null, reel: c.reel }
  })
  if (!v.order.every(id => typeof id === 'string' && ids.has(id)) || new Set(v.order).size !== v.order.length) throw bad()
  return { state: v.state as CardData['state'], clips, order: [...v.order] as string[], chosen: v.chosen,
    share: v.share === null ? null : { profile_url: profile, settings_url: settings } }
}

// Tap to add or remove. Order is kept; the first pick is the lead. A fourth pick is refused.
export function togglePick(picks: string[], id: string): string[] {
  if (picks.includes(id)) return picks.filter(item => item !== id)
  return picks.length >= CARD_MAX ? picks : [...picks, id]
}
