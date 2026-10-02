'use client'

// "My card" (2026-10-02 approved design, Card.dc.html). Her highlight clip leads; name, class,
// position and state follow; combine numbers are a small extra (3 chips). She picks up to 3
// public GMTM clips, in order (first = lead). Private: there is no public card page. The only
// share is her own GMTM profile link, and only when GMTM shows that profile publicly.
import { useCallback, useEffect, useState } from 'react'
import Link from 'next/link'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'
import { ProfileEvidence } from './profileEvidence'
import { ProfileMaterialsSnapshot } from './profileMaterials'
import { drillResults, Poster } from './AthleteCareerHome'
import { primary, readJSON, secondary } from './ProfileColleges'
import { CARD_MAX, CardClip, CardData, readCard, togglePick } from './cardPicker'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-jr-lime'
const stripes = 'bg-[repeating-linear-gradient(135deg,#1A1A1F_0,#1A1A1F_16px,#202027_16px,#202027_32px)]'
export const cardURL = (userId: string) => `${BACKEND_URL}/api/workspace/card/${encodeURIComponent(userId)}`

// `lead`: Home's lightweight read (the lead clip only; no share link, so no GMTM visibility read).
export function useCard(userId: string, lead = false) {
  const [data, setData] = useState<CardData | null>(null)
  const [error, setError] = useState('')
  useEffect(() => {
    let live = true
    readJSON<unknown>(apiFetch(cardURL(userId) + (lead ? '/lead' : ''), { cache: 'no-store' })).then(body => { if (live) setData(readCard(body)) },
      e => { if (live) setError((e as Error).message) })
    return () => { live = false }
  }, [userId, lead])
  return { data, setData, error }
}

export function leadClip(card: CardData | null): CardClip | null {
  return card?.clips.find(clip => clip.id === card.order[0]) || null
}

// Plays inline only when GMTM stores a direct video file on its CDN. Those are often raw uploads
// (81-500 MB measured 2026-10-02), so nothing is fetched until she taps play: poster first, then a video
// element (preload none) that starts on that tap. No file, or a failed one: poster + link to GMTM.
function LeadMedia({ clip }: { clip: CardClip }) {
  const [failed, setFailed] = useState(false)
  const [playing, setPlaying] = useState(false)
  const badge = 'absolute rounded-full bg-[rgba(11,11,12,0.85)] px-2.5 py-1.5 text-xs'
  const inline = !!clip.video_url && !failed
  if (inline && playing) {
    return <div className="relative bg-black">
      <video key={clip.id} controls autoPlay playsInline preload="none" poster={clip.thumbnail_url || undefined}
        src={clip.video_url!} onError={() => { setFailed(true); setPlaying(false) }} aria-label={`Highlight: ${clip.title}`}
        className="aspect-[4/5] max-h-[70vh] w-full object-contain sm:aspect-video" />
    </div>
  }
  const play = <>
    <span className="flex h-[72px] w-[72px] items-center justify-center rounded-full bg-jr-lime">
      <svg width="28" height="28" viewBox="0 0 24 24" fill="#0B0B0C" aria-hidden="true"><path d="M8 5v14l11-7z" /></svg>
    </span>
    {!inline && <span className="rounded-full bg-[rgba(11,11,12,0.85)] px-3 py-1.5 text-sm font-semibold text-white">Watch on GMTM<span className="sr-only">: {clip.title} (opens a new tab)</span></span>}
  </>
  const center = `absolute left-1/2 top-1/2 flex -translate-x-1/2 -translate-y-1/2 flex-col items-center gap-2 ${focus}`
  return <div className={`relative aspect-[4/5] max-h-[70vh] w-full sm:aspect-video ${stripes}`}>
    <Poster key={`${clip.id}:${clip.thumbnail_url || ''}`} clip={clip} />
    <span className={`${badge} left-3.5 top-3.5 max-w-[70%] truncate font-bold text-jr-lime`}>{clip.title}</span>
    {inline ? <button type="button" onClick={() => setPlaying(true)} aria-label={`Play highlight: ${clip.title}`} className={`${center} rounded-full`}>{play}</button>
      : <a href={clip.source_url} target="_blank" rel="noopener noreferrer" className={center}>{play}</a>}
    {failed && <span role="status" className={`${badge} right-3.5 top-3.5 text-[#D4D4DA]`}>Can&apos;t play here</span>}
    <span className={`${badge} bottom-3.5 left-3.5 text-[13px] text-[#D4D4DA]`}>From {clip.source_label}</span>
  </div>
}

function ShareButton({ share }: { share: NonNullable<CardData['share']> }) {
  const [status, setStatus] = useState<'idle' | 'copied' | 'failed'>('idle')
  if (!share.profile_url) {
    return <div className="flex flex-col gap-2 rounded-[14px] border border-jr-edge p-4">
      <p className="font-semibold">Make your GMTM profile public to share it.</p>
      <p className="text-sm text-jr-soft">Coaches can open your profile only when it is public on GMTM. Your SPARQ card stays private.</p>
      <a href={share.settings_url || 'https://gmtm.com/settings'} target="_blank" rel="noopener noreferrer" className={`${secondary} self-start`}>Open GMTM settings<span className="sr-only"> (opens a new tab)</span></a>
    </div>
  }
  const url = share.profile_url
  const copy = async () => {
    try { await navigator.clipboard.writeText(url); setStatus('copied') } catch { setStatus('failed') }
  }
  return <div className="flex flex-col gap-2">
    <button type="button" onClick={() => void copy()} className={`${primary} w-full`}>{status === 'copied' ? 'Link copied' : 'Copy link for coaches'}</button>
    <p role="status" className="text-sm text-jr-muted">{status === 'copied' ? 'Your GMTM profile link is copied. Paste it in your email to a coach.'
      : status === 'failed' ? 'Copy did not work here. Your link:' : 'This copies your public GMTM profile link.'}</p>
    {status === 'failed' && <input readOnly value={url} aria-label="Your GMTM profile link" onFocus={e => e.currentTarget.select()}
      className="w-full rounded-xl border border-jr-edge bg-jr-well px-4 py-3 text-sm" />}
  </div>
}

export default function MyCard({ userId, profile, snapshot }: { userId: string; profile: ProfileEvidence; snapshot: ProfileMaterialsSnapshot | null }) {
  const { data, setData, error } = useCard(userId)
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')
  const athlete = profile.athlete!
  const picks = data?.chosen ? data.order : []
  const lead = leadClip(data)
  // Combine numbers are a small extra: the first 3 drills (junior drills first, power ball in ft).
  const chips = drillResults(profile, snapshot).slice(0, 3)
  const line = [athlete.graduation_year ? `Class of ${athlete.graduation_year}` : null, athlete.position, athlete.state].filter(Boolean).join(' · ')

  const toggle = useCallback(async (id: string) => {
    if (!data || saving) return
    const next = togglePick(picks, id)
    if (next === picks) return
    setSaving(true); setSaveError('')
    try {
      const body = await readJSON<unknown>(apiFetch(cardURL(userId), { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ film_ids: next }) }))
      setData(readCard(body))
    } catch (e) {
      setSaveError((e as Error).message)
    } finally { setSaving(false) }
  }, [data, picks, saving, setData, userId])

  return <div className="mx-auto flex max-w-[640px] flex-col gap-6 pb-6 pt-6 md:pt-10">
    <h1 className="sr-only">My card</h1>
    <article aria-label="Your athlete card" className="flex flex-col overflow-hidden rounded-[28px] border border-[#26262C] bg-jr-card">
      {lead ? <LeadMedia key={lead.id} clip={lead} />
        : <div className={`relative flex aspect-[4/5] max-h-[70vh] w-full items-center justify-center p-6 text-center sm:aspect-video ${stripes}`}>
          <p className="relative text-jr-soft">{!data && !error ? 'Loading your highlight…' : error || data?.state === 'source_unavailable' ? 'Your clips could not be loaded right now.' : 'No public clips yet. Clips you add on GMTM and make public show here.'}</p>
        </div>}
      <div className="flex flex-col gap-2.5 p-[18px]">
        <h2 className="break-words text-[30px] font-bold leading-tight tracking-[-0.5px]">{athlete.name || 'Your athlete card'}</h2>
        {line && <p className="text-sm text-jr-muted">{line}</p>}
        {chips.length > 0 && <ul aria-label="Combine numbers" className="flex flex-wrap gap-1.5">
          {chips.map((item, index) => <li key={item.id} className={`rounded-full px-2.5 py-1.5 text-[13px] ${index === 0 ? 'bg-jr-done font-semibold text-jr-lime' : 'bg-jr-raised text-[#D4D4DA]'}`}>
            {item.label} {item.value} {item.unit}</li>)}
        </ul>}
      </div>
    </article>

    <section aria-labelledby="picks-title" className="flex flex-col gap-2.5">
      <div className="flex items-baseline justify-between gap-3">
        <h2 id="picks-title" className="text-[17px] font-bold">Choose your highlights</h2>
        <span className="text-[13px] text-jr-muted" aria-live="polite">{picks.length} of {CARD_MAX} on your card</span>
      </div>
      {saveError && <p role="alert" className="text-sm text-amber-200">{saveError}</p>}
      {data?.clips.length ? <ul className="grid grid-cols-2 gap-2.5 sm:grid-cols-3">
        {data.clips.map(clip => {
          const position = picks.indexOf(clip.id)
          const on = position >= 0
          const full = !on && picks.length >= CARD_MAX
          return <li key={clip.id}>
            <button type="button" aria-pressed={on} disabled={saving || full} onClick={() => void toggle(clip.id)}
              aria-label={on ? `${clip.title}, pick ${position + 1}. Tap to remove.` : full ? `${clip.title}. Remove a pick to add this.` : `Add ${clip.title} to your card`}
              className={`flex w-full flex-col gap-1.5 rounded-[14px] bg-jr-card p-2 text-left disabled:cursor-not-allowed ${full ? 'opacity-60' : ''} ${on ? 'border-2 border-jr-lime' : 'border border-[#26262C]'} ${focus}`}>
              <span className="relative block aspect-video overflow-hidden rounded-[10px]">
                <Poster key={`${clip.id}:${clip.thumbnail_url || ''}`} clip={clip} />
                <span aria-hidden="true" className={`absolute right-1.5 top-1.5 flex h-6 w-6 items-center justify-center rounded-full text-[13px] font-bold ${on ? 'bg-jr-lime text-jr-ground' : 'bg-[rgba(11,11,12,0.85)] text-jr-text'}`}>{on ? position + 1 : '+'}</span>
              </span>
              <span className="break-words text-sm font-semibold text-jr-text">{clip.title}</span>
              <span className="break-words text-xs text-jr-muted">{clip.source_label}</span>
            </button>
          </li>
        })}
      </ul> : <p className="rounded-[14px] border border-jr-line bg-jr-card p-4 text-sm text-jr-soft">{!data && !error ? 'Loading your clips…' : 'Your public GMTM clips show here.'}</p>}
      <p className="text-[13px] text-jr-dim">{data && !data.chosen && lead ? `Your card shows “${lead.title}” until you pick. ` : ''}Your first pick plays first. Clips come from your public GMTM uploads.{' '}
        <Link href="/home/footage" className={`text-jr-lime underline underline-offset-4 ${focus}`}>See all my footage and results</Link></p>
    </section>

    {data && data.state === 'ready' && data.share && <ShareButton share={data.share} />}
  </div>
}
