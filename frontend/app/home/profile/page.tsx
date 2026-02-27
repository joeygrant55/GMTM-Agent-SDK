'use client'

import { useEffect, useState } from 'react'
import { useUser } from '@clerk/nextjs'

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'

const MAJOR_AREAS   = ['Undecided', 'Business', 'STEM', 'Communications', 'Education', 'Other'] as const
const TARGET_LEVELS = ['D1 Power', 'D1 Mid-Major', 'D2', 'D3', 'NAIA', 'Open'] as const
const GEOGRAPHY_OPTIONS   = ['Anywhere', 'In-state', 'Southeast', 'Midwest', 'West', 'Northeast', 'South'] as const
const SCHOOL_SIZE_OPTIONS = ['Large', 'Medium', 'Small', 'No preference'] as const

type Major    = typeof MAJOR_AREAS[number]
type Level    = typeof TARGET_LEVELS[number]
type Geo      = typeof GEOGRAPHY_OPTIONS[number]
type Size     = typeof SCHOOL_SIZE_OPTIONS[number]

function ChipGroup<T extends string>({ options, value, onChange }: { options: readonly T[]; value: T; onChange: (v: T) => void }) {
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {options.map(o => (
        <button key={o} type="button" onClick={() => onChange(o)}
          className={`rounded-xl border px-3 py-1.5 text-sm transition-colors ${
            value === o ? 'border-sparq-lime bg-sparq-lime text-sparq-charcoal font-bold'
                       : 'border-white/10 bg-black/20 text-gray-300 hover:border-sparq-lime/50'
          }`}>{o}</button>
      ))}
    </div>
  )
}

const inp = "w-full rounded-xl border border-white/10 bg-black/30 px-4 py-2.5 text-white placeholder:text-gray-500 focus:outline-none focus:border-sparq-lime/50"

export default function WorkspaceProfilePage() {
  const { user } = useUser()
  const clerkId = user?.id

  const [loading, setLoading]   = useState(true)
  const [saving, setSaving]     = useState(false)
  const [saved, setSaved]       = useState(false)
  const [error, setError]       = useState('')

  const [maxpreps, setMaxpreps] = useState<Record<string, unknown>>({})
  const [gpa, setGpa]           = useState('')
  const [majorArea, setMajorArea]   = useState<Major>('Undecided')
  const [hudlUrl, setHudlUrl]       = useState('')
  const [targetLevel, setTargetLevel] = useState<Level>('Open')
  const [geography, setGeography]   = useState<Geo>('Anywhere')
  const [schoolSize, setSchoolSize] = useState<Size>('No preference')
  const [forty, setForty]   = useState('')
  const [shuttle, setShuttle] = useState('')
  const [vert, setVert]       = useState('')
  const [htFt, setHtFt]       = useState('')
  const [htIn, setHtIn]       = useState('')
  const [wt, setWt]           = useState('')

  useEffect(() => {
    if (!clerkId) return
    fetch(`${backendUrl}/api/workspace/profile/${clerkId}`)
      .then(r => r.json())
      .then(d => {
        setMaxpreps((d.maxpreps_data as Record<string, unknown>) || {})
        const cm = (d.combine_metrics as Record<string, unknown>) || {}
        setForty(cm.fortyYardDash != null ? String(cm.fortyYardDash) : '')
        setShuttle(cm.shuttle != null ? String(cm.shuttle) : '')
        setVert(cm.vertical != null ? String(cm.vertical) : '')
        setHtFt(cm.heightFeet != null ? String(cm.heightFeet) : '')
        setHtIn(cm.heightInches != null ? String(cm.heightInches) : '')
        setWt(cm.weight != null ? String(cm.weight) : '')
        setGpa(d.gpa != null ? String(d.gpa) : '')
        setMajorArea((d.major_area as Major) || 'Undecided')
        setHudlUrl(d.hudl_url || '')
        const g = (d.recruiting_goals as Record<string, unknown>) || {}
        setTargetLevel((g.targetLevel as Level) || 'Open')
        setGeography((g.geography as Geo) || 'Anywhere')
        setSchoolSize((g.schoolSize as Size) || 'No preference')
      })
      .catch(() => setError('Could not load profile'))
      .finally(() => setLoading(false))
  }, [clerkId])

  const n = (s: string) => { const v = parseFloat(s); return Number.isFinite(v) ? v : undefined }

  const save = async () => {
    if (!clerkId) return
    setSaving(true); setError('')
    try {
      const res = await fetch(`${backendUrl}/api/workspace/profile/${clerkId}`, {
        method: 'PATCH',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          gpa: n(gpa), majorArea, hudlUrl: hudlUrl.trim() || null,
          combineMetrics: { fortyYardDash: n(forty), shuttle: n(shuttle), vertical: n(vert), heightFeet: n(htFt), heightInches: n(htIn), weight: n(wt) },
          recruitingGoals: { targetLevel, geography, schoolSize },
        }),
      })
      if (!res.ok) throw new Error()
      setSaved(true); setTimeout(() => setSaved(false), 3000)
    } catch { setError('Save failed — please try again.') }
    finally { setSaving(false) }
  }

  const filled = [!!maxpreps?.name, !!gpa, majorArea !== 'Undecided', !!(forty || vert || wt), !!hudlUrl, targetLevel !== 'Open', geography !== 'Anywhere']
  const pct = Math.round(filled.filter(Boolean).length / filled.length * 100)

  const name     = (maxpreps.name as string) || ''
  const sport    = (maxpreps.sport as string) || ''
  const pos      = (maxpreps.position as string) || ''
  const school   = (maxpreps.school as string) || ''
  const photo    = (maxpreps.photoUrl as string) || ''
  const stats    = (maxpreps.statsPreview as [string, string][]) || []

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
    </div>
  )

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-5">
      <div>
        <h1 className="text-3xl font-black text-white">Your Profile</h1>
        <p className="text-gray-400 mt-1 text-sm">Coaches and AI matching use this — keep it current.</p>
      </div>

      {/* Completion */}
      <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm font-semibold text-gray-300">Profile Completion</span>
          <span className="text-sparq-lime font-black text-lg">{pct}%</span>
        </div>
        <div className="h-2 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-sparq-lime transition-all duration-500" style={{ width: `${pct}%` }} />
        </div>
        {pct < 100 && <p className="text-xs text-gray-500 mt-2">Fill in more fields to improve your college matches.</p>}
      </div>

      {/* MaxPreps identity */}
      {name && (
        <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">📋 MaxPreps Identity</p>
          <div className="flex items-center gap-4">
            {photo && <img src={photo} alt="" className="w-14 h-14 rounded-full object-cover border border-white/10 flex-shrink-0" />}
            <div className="flex-1 min-w-0">
              <p className="text-white font-black text-xl">{name}</p>
              <p className="text-gray-400 text-sm mt-0.5">{[pos, sport, school].filter(Boolean).join(' · ')}</p>
              {stats.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {stats.slice(0, 4).map(([label, val]) => (
                    <span key={label} className="text-xs bg-sparq-lime/10 text-sparq-lime border border-sparq-lime/20 rounded-lg px-2 py-0.5 font-bold">{val} {label}</span>
                  ))}
                </div>
              )}
            </div>
          </div>
          <p className="text-xs text-gray-500 mt-3">Linked from MaxPreps · <a href="/onboarding/search" className="text-sparq-lime hover:underline">Re-link →</a></p>
        </section>
      )}

      {/* Combine */}
      <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 space-y-4">
        <div>
          <h2 className="text-lg font-black text-white">⚡ Combine Metrics</h2>
          <p className="text-xs text-gray-500 mt-0.5">Optional — improves matching when provided.</p>
        </div>
        <div className="grid grid-cols-2 gap-3">
          {([['40-Yard Dash (sec)', forty, setForty, '4.52'], ['Shuttle 5-10-5 (sec)', shuttle, setShuttle, '4.20'],
             ['Vertical (in)', vert, setVert, '32'], ['Weight (lbs)', wt, setWt, '185'],
             ['Height — Feet', htFt, setHtFt, '6'], ['Height — Inches', htIn, setHtIn, '2']] as const).map(([lbl, val, set, ph]) => (
            <div key={lbl}>
              <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block mb-1">{lbl}</label>
              <input value={val} onChange={e => (set as (v: string) => void)(e.target.value)} type="number" placeholder={ph} className={inp} />
            </div>
          ))}
        </div>
      </section>

      {/* Academics */}
      <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 space-y-4">
        <h2 className="text-lg font-black text-white">🎓 Academics</h2>
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block mb-1">GPA</label>
            <input value={gpa} onChange={e => setGpa(e.target.value)} type="number" step="0.01" placeholder="3.8" className={inp} />
          </div>
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block">Area of Study</label>
          <ChipGroup options={MAJOR_AREAS} value={majorArea} onChange={setMajorArea} />
        </div>
      </section>

      {/* Goals */}
      <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 space-y-4">
        <h2 className="text-lg font-black text-white">🎯 Recruiting Goals</h2>
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block">Target Division</label>
          <ChipGroup options={TARGET_LEVELS} value={targetLevel} onChange={setTargetLevel} />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block">Geography</label>
          <ChipGroup options={GEOGRAPHY_OPTIONS} value={geography} onChange={setGeography} />
        </div>
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block">School Size</label>
          <ChipGroup options={SCHOOL_SIZE_OPTIONS} value={schoolSize} onChange={setSchoolSize} />
        </div>
      </section>

      {/* Film */}
      <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 space-y-3">
        <h2 className="text-lg font-black text-white">🎬 Film</h2>
        <div>
          <label className="text-xs font-semibold text-gray-400 uppercase tracking-wide block mb-1">Hudl Highlight URL</label>
          <input value={hudlUrl} onChange={e => setHudlUrl(e.target.value)} type="url"
            placeholder="https://www.hudl.com/profile/..." className={inp} />
        </div>
      </section>

      {error && <p className="text-sm text-red-400">{error}</p>}
      <div className="flex items-center gap-4 pb-10">
        <button onClick={save} disabled={saving}
          className="bg-sparq-lime text-sparq-charcoal font-black rounded-xl px-8 py-3 hover:bg-yellow-300 disabled:opacity-60 transition-colors">
          {saving ? 'Saving...' : 'Save Changes'}
        </button>
        {saved && <span className="text-sparq-lime text-sm font-semibold animate-fade-in">✓ Saved</span>}
      </div>
    </div>
  )
}
