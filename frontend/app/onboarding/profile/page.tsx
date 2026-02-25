'use client'

import { FormEvent, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import {
  CompleteOnboardingPayload,
  MaxPrepsAthlete,
  ONBOARDING_MAXPREPS_KEY,
  ONBOARDING_PROFILE_ID_KEY,
} from '@/app/onboarding/_lib/types'

const MAJOR_AREAS = ['Undecided', 'Business', 'STEM', 'Communications', 'Other'] as const
const TARGET_LEVELS = ['D1 Power', 'D1 Mid-Major', 'D2', 'D3', 'Open'] as const
const GEOGRAPHY_OPTIONS = ['Anywhere', 'In-state', 'Southeast', 'Midwest', 'West', 'Northeast'] as const
const SCHOOL_SIZE_OPTIONS = ['Large', 'Medium', 'Small', 'No preference'] as const

type MajorArea = (typeof MAJOR_AREAS)[number]
type TargetLevel = (typeof TARGET_LEVELS)[number]
type Geography = (typeof GEOGRAPHY_OPTIONS)[number]
type SchoolSize = (typeof SCHOOL_SIZE_OPTIONS)[number]

function SelectionGroup<T extends string>({
  options,
  value,
  onChange,
}: {
  options: readonly T[]
  value: T
  onChange: (value: T) => void
}) {
  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {options.map((option) => (
        <button
          key={option}
          type="button"
          onClick={() => onChange(option)}
          className={`rounded-xl border px-3 py-2 text-sm transition-colors ${
            value === option
              ? 'border-sparq-lime bg-sparq-lime text-sparq-charcoal font-bold'
              : 'border-white/10 bg-black/30 text-gray-300 hover:border-sparq-lime/50'
          }`}
        >
          {option}
        </button>
      ))}
    </div>
  )
}

export default function ProfileOnboardingPage() {
  const router = useRouter()
  const [fortyYardDash, setFortyYardDash] = useState('')
  const [shuttle, setShuttle] = useState('')
  const [vertical, setVertical] = useState('')
  const [heightFeet, setHeightFeet] = useState('')
  const [heightInches, setHeightInches] = useState('')
  const [weight, setWeight] = useState('')
  const [gpa, setGpa] = useState('')
  const [majorArea, setMajorArea] = useState<MajorArea>('Undecided')
  const [targetLevel, setTargetLevel] = useState<TargetLevel>('Open')
  const [geography, setGeography] = useState<Geography>('Anywhere')
  const [schoolSize, setSchoolSize] = useState<SchoolSize>('No preference')
  const [hudlUrl, setHudlUrl] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState('')

  const progressPct = useMemo(() => 75, [])

  const toNumber = (value: string): number | undefined => {
    if (!value.trim()) return undefined
    const parsed = Number(value)
    return Number.isFinite(parsed) ? parsed : undefined
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setSubmitting(true)
    setError('')

    let maxprepsData: MaxPrepsAthlete | null = null
    const maxprepsRaw = sessionStorage.getItem(ONBOARDING_MAXPREPS_KEY)
    if (maxprepsRaw) {
      try {
        maxprepsData = JSON.parse(maxprepsRaw) as MaxPrepsAthlete
      } catch {
        maxprepsData = null
      }
    }

    const payload: CompleteOnboardingPayload = {
      maxprepsData,
      combineMetrics: {
        fortyYardDash: toNumber(fortyYardDash),
        shuttle: toNumber(shuttle),
        vertical: toNumber(vertical),
        heightFeet: toNumber(heightFeet),
        heightInches: toNumber(heightInches),
        weight: toNumber(weight),
      },
      gpa: toNumber(gpa),
      majorArea,
      recruitingGoals: {
        targetLevel,
        geography,
        schoolSize,
      },
      hudlUrl: hudlUrl.trim() || undefined,
    }

    try {
      const res = await fetch('/api/onboarding/complete', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.error || 'Failed to complete onboarding')

      if (data.profile_id) {
        sessionStorage.setItem(ONBOARDING_PROFILE_ID_KEY, String(data.profile_id))
      }

      router.push('/onboarding/generating')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to complete onboarding')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
        <p className="text-sm font-semibold tracking-widest text-sparq-lime uppercase">Step 3 of 4</p>
        <h1 className="mt-3 text-4xl font-black">Build Your Recruiting Profile</h1>

        <div className="mt-5 h-2 rounded-full bg-white/10 overflow-hidden">
          <div className="h-full rounded-full bg-sparq-lime" style={{ width: `${progressPct}%` }} />
        </div>

        <form onSubmit={onSubmit} className="mt-8 space-y-5">
          <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
            <h2 className="text-xl font-black">A. Combine Metrics</h2>
            <p className="mt-1 text-sm text-gray-400">Enter what you have. Every field is optional.</p>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input value={fortyYardDash} onChange={(e) => setFortyYardDash(e.target.value)} type="number" step="0.01" placeholder="40-yard dash (sec)" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
              <input value={shuttle} onChange={(e) => setShuttle(e.target.value)} type="number" step="0.01" placeholder="Shuttle 5-10-5 (sec)" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
              <input value={vertical} onChange={(e) => setVertical(e.target.value)} type="number" step="0.1" placeholder="Vertical (inches)" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
              <input value={weight} onChange={(e) => setWeight(e.target.value)} type="number" step="1" placeholder="Weight (lbs)" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
              <input value={heightFeet} onChange={(e) => setHeightFeet(e.target.value)} type="number" step="1" placeholder="Height feet" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
              <input value={heightInches} onChange={(e) => setHeightInches(e.target.value)} type="number" step="1" placeholder="Height inches" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
            </div>
          </section>

          <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
            <h2 className="text-xl font-black">B. Academics</h2>
            <div className="mt-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
              <input value={gpa} onChange={(e) => setGpa(e.target.value)} type="number" step="0.01" placeholder="GPA" className="rounded-xl border border-white/10 bg-black/30 px-4 py-3" />
              <select
                value={majorArea}
                onChange={(e) => setMajorArea(e.target.value as MajorArea)}
                className="rounded-xl border border-white/10 bg-black/30 px-4 py-3"
              >
                {MAJOR_AREAS.map((major) => (
                  <option key={major} value={major}>{major}</option>
                ))}
              </select>
            </div>
          </section>

          <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
            <h2 className="text-xl font-black">C. Recruiting Goals</h2>
            <div className="mt-4">
              <p className="text-sm text-gray-300">Target level</p>
              <SelectionGroup options={TARGET_LEVELS} value={targetLevel} onChange={setTargetLevel} />
            </div>
            <div className="mt-4">
              <p className="text-sm text-gray-300">Geography</p>
              <SelectionGroup options={GEOGRAPHY_OPTIONS} value={geography} onChange={setGeography} />
            </div>
            <div className="mt-4">
              <p className="text-sm text-gray-300">School size</p>
              <SelectionGroup options={SCHOOL_SIZE_OPTIONS} value={schoolSize} onChange={setSchoolSize} />
            </div>
          </section>

          <section className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
            <h2 className="text-xl font-black">D. Film</h2>
            <p className="mt-1 text-sm text-gray-400">Hudl highlight link (optional)</p>
            <input
              value={hudlUrl}
              onChange={(e) => setHudlUrl(e.target.value)}
              type="url"
              placeholder="https://www.hudl.com/profile/..."
              className="mt-3 w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3"
            />
          </section>

          {error && <p className="text-sm text-red-400">{error}</p>}

          <button
            type="submit"
            disabled={submitting}
            className="w-full sm:w-auto bg-sparq-lime text-sparq-charcoal font-black rounded-xl hover:bg-sparq-lime-dark disabled:opacity-60 px-6 py-3"
          >
            {submitting ? 'Building...' : 'Build My Profile →'}
          </button>
        </form>
      </div>
    </div>
  )
}
