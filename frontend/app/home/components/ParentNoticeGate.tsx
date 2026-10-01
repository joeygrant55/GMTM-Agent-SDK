'use client'

// GMTM-entry juniors must confirm a parent or guardian knows before personal pages
// load. The backend enforces the same rule on every personal route; this is the UI.
import { useCallback, useEffect, useState } from 'react'
import { apiFetch, BACKEND_URL } from '@/app/_lib/api'

export type EntryNotice = { phase: 'loading' | 'ready' | 'ended'; required: boolean; accepted: boolean }

const NOTICE_URL = `${BACKEND_URL}/api/athlete/parent-notice`
const GMTM_URL = process.env.NEXT_PUBLIC_GMTM_WEB_URL || 'https://gmtm.com'

export function useEntryNotice(userId: string | undefined) {
  const [notice, setNotice] = useState<EntryNotice>({ phase: 'loading', required: false, accepted: false })
  useEffect(() => {
    if (!userId) return
    let live = true
    apiFetch(NOTICE_URL).then(async res => {
      if (!live) return
      if (res.status === 401) return setNotice({ phase: 'ended', required: true, accepted: false })
      const data = res.ok ? await res.json() : null
      // Unknown answer: let the page load; the backend still blocks personal data.
      setNotice({ phase: 'ready', required: data?.required === true, accepted: data?.accepted === true })
    }).catch(() => { if (live) setNotice({ phase: 'ready', required: false, accepted: false }) })
    return () => { live = false }
  }, [userId])
  const accept = useCallback(async () => {
    const res = await apiFetch(NOTICE_URL, { method: 'POST' })
    const data = res.ok ? await res.json() : null
    if (data?.accepted !== true) throw new Error('not saved')
    setNotice({ phase: 'ready', required: true, accepted: true })
  }, [])
  return { notice, accept }
}

export function SwitchAccountLink() {
  return <a href={GMTM_URL} className="inline-flex min-h-11 items-center text-xs text-gray-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime">Not you? Switch</a>
}

export function ParentNoticeScreen({ notice, accept }: { notice: EntryNotice; accept: () => Promise<void> }) {
  const [checked, setChecked] = useState(false)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState(false)
  if (notice.phase === 'ended') {
    return (
      <section className="mx-auto max-w-md py-16 text-center">
        <h1 className="mb-3 text-2xl font-bold">Your SPARQ session ended</h1>
        <p className="mb-8 text-gray-400">Open SPARQ from GMTM again to keep going.</p>
        <a href={GMTM_URL} className="rounded-lg bg-sparq-lime px-6 py-3 font-bold text-sparq-charcoal">Back to GMTM</a>
      </section>
    )
  }
  return (
    <section aria-labelledby="parent-notice-title" className="mx-auto max-w-lg py-16">
      <h1 id="parent-notice-title" className="mb-3 text-2xl font-bold">Before you start</h1>
      <p className="mb-6 text-gray-300">SPARQ helps you find college flag football programs and write a note to a coach. You send any note yourself. Please make sure a parent or guardian knows you are using SPARQ.</p>
      <label className="mb-6 flex items-start gap-3 text-gray-200">
        <input type="checkbox" checked={checked} onChange={event => setChecked(event.target.checked)} className="mt-1 h-5 w-5 accent-sparq-lime" />
        <span>My parent or guardian knows I&apos;m using SPARQ</span>
      </label>
      {error && <p role="alert" className="mb-4 text-sm text-red-300">That did not save. Try again.</p>}
      <button type="button" disabled={!checked || saving} onClick={async () => {
        setSaving(true); setError(false)
        try { await accept() } catch { setError(true) } finally { setSaving(false) }
      }} className="rounded-lg bg-sparq-lime px-6 py-3 font-bold text-sparq-charcoal disabled:opacity-50">Continue</button>
    </section>
  )
}
