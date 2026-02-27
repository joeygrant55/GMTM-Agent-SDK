'use client'

import { FormEvent, useState } from 'react'
import Link from 'next/link'
import { useRouter } from 'next/navigation'
import { MaxPrepsAthlete, ONBOARDING_MAXPREPS_KEY } from '@/app/onboarding/_lib/types'

function normalizeResult(raw: Record<string, unknown>): MaxPrepsAthlete {
  return {
    maxprepsAthleteId: String(raw.maxprepsAthleteId ?? raw.maxpreps_athlete_id ?? raw.id ?? ''),
    name: String((raw.name ?? `${raw.first_name ?? ''} ${raw.last_name ?? ''}`.trim()) || 'Unknown Athlete'),
    position: raw.position ? String(raw.position) : undefined,
    sport: Array.isArray(raw.sports) && (raw.sports as string[]).length > 0
      ? (raw.sports as string[])[0].replace(/^Boys |^Girls /, '')
      : undefined,
    sports: Array.isArray(raw.sports) ? (raw.sports as string[]) : undefined,
    school: raw.school ? String(raw.school) : raw.high_school ? String(raw.high_school) : undefined,
    classYear: raw.classYear ? Number(raw.classYear) : raw.grad_year ? Number(raw.grad_year) : undefined,
    city: raw.city ? String(raw.city) : undefined,
    state: raw.state ? String(raw.state) : undefined,
    maxprepsUrl: raw.maxprepsUrl ? String(raw.maxprepsUrl) : undefined,
    profileUrl: raw.profileUrl ? String(raw.profileUrl) : undefined,
    photoUrl: raw.photoUrl ? String(raw.photoUrl) : undefined,
    teamRecord: raw.teamRecord ? String(raw.teamRecord) : undefined,
    seasonStats: Array.isArray(raw.seasonStats) ? (raw.seasonStats as MaxPrepsAthlete['seasonStats']) : undefined,
  }
}

export default function MaxPrepsSearchPage() {
  const router = useRouter()
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<MaxPrepsAthlete[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [searched, setSearched] = useState(false)

  const onSearch = async (e: FormEvent) => {
    e.preventDefault()
    if (query.trim().length < 2) {
      setError('Enter at least 2 characters to search.')
      return
    }

    setLoading(true)
    setError('')
    setSearched(true)

    try {
      const res = await fetch(`/api/onboarding/maxpreps/search?q=${encodeURIComponent(query.trim())}`)
      const data = await res.json()
      if (!res.ok) {
        throw new Error(data.error || 'Search failed.')
      }

      const rawResults = Array.isArray(data.results)
        ? data.results
        : Array.isArray(data.athletes)
          ? data.athletes
          : []

      setResults(rawResults.map((item: Record<string, unknown>) => normalizeResult(item)))
    } catch (err) {
      setResults([])
      setError(err instanceof Error ? err.message : 'Search failed. Please try again.')
    } finally {
      setLoading(false)
    }
  }

  const onSelect = (athlete: MaxPrepsAthlete) => {
    sessionStorage.setItem(ONBOARDING_MAXPREPS_KEY, JSON.stringify(athlete))
    router.push('/onboarding/confirm')
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
        <div className="mb-8 text-center">
          <p className="text-sm font-semibold tracking-widest text-sparq-lime uppercase">Step 1 of 4</p>
          <h1 className="mt-3 text-4xl font-black">Find Your MaxPreps Profile</h1>
          <p className="mt-3 text-gray-400">Search for your name to import your stats automatically.</p>
        </div>

        <form onSubmit={onSearch} className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <label htmlFor="athlete-search" className="text-sm text-gray-300">Athlete name</label>
          <div className="mt-3 flex gap-3">
            <input
              id="athlete-search"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Jordan Mitchell"
              className="flex-1 rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white placeholder:text-gray-500 focus:border-sparq-lime focus:outline-none"
            />
            <button
              type="submit"
              disabled={loading}
              className="bg-sparq-lime text-sparq-charcoal font-black rounded-xl hover:bg-sparq-lime-dark disabled:opacity-60 px-6 py-3"
            >
              {loading ? 'Searching...' : 'Search'}
            </button>
          </div>
          {error && <p className="mt-3 text-sm text-red-400">{error}</p>}
        </form>

        {loading && (
          <div className="mt-6 space-y-3">
            <p className="text-center text-gray-400 text-sm mb-4 animate-pulse">
              Pulling stats from MaxPreps — this takes a few seconds...
            </p>
            {[0, 1, 2].map((i) => (
              <div key={i} className="w-full bg-white/[0.04] border border-white/10 rounded-2xl p-5 animate-pulse">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 space-y-2">
                    <div className="h-5 bg-white/10 rounded w-40" />
                    <div className="h-3 bg-white/10 rounded w-56" />
                    <div className="h-3 bg-white/10 rounded w-24" />
                  </div>
                  <div className="w-10 h-10 rounded-full bg-white/10 flex-shrink-0" />
                </div>
                <div className="mt-3 flex gap-3">
                  {[0, 1, 2].map((j) => (
                    <div key={j} className="bg-black/30 rounded-lg px-3 py-2 w-16">
                      <div className="h-4 bg-white/10 rounded mb-1" />
                      <div className="h-2 bg-white/10 rounded" />
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}

        <div className="mt-6 space-y-3">
          {!loading && results.map((athlete) => {
            const raw = athlete as any
            const statsPreview: [string, string][] = raw.statsPreview || []
            const lastSeason: string | null = raw.lastSeason || null
            const schoolColor: string | null = raw.schoolColor || null
            const hasStats = statsPreview.length > 0
            return (
              <button
                key={`${athlete.maxprepsAthleteId || athlete.name}-${athlete.school || ''}`}
                onClick={() => onSelect(athlete)}
                className={`w-full text-left bg-white/[0.04] border rounded-2xl p-5 hover:border-sparq-lime/50 transition-colors ${hasStats ? 'border-white/20' : 'border-white/10 opacity-75'}`}
              >
                <div className="flex items-start justify-between gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      {schoolColor && (
                        <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ backgroundColor: `#${schoolColor}` }} />
                      )}
                      <span className="text-lg font-bold text-white truncate">{athlete.name}</span>
                    </div>
                    <div className="mt-1 text-gray-300 text-sm">
                      {[athlete.position, athlete.school].filter(Boolean).join(' · ')}
                    </div>
                    <div className="mt-0.5 text-gray-500 text-xs">
                      {athlete.classYear ? `Class of ${athlete.classYear}` : null}
                      {lastSeason ? (athlete.classYear ? ` · ${lastSeason}` : lastSeason) : null}
                      {!athlete.classYear && !lastSeason ? 'No season data' : null}
                    </div>
                  </div>
                  {athlete.photoUrl && (
                    <img src={athlete.photoUrl} alt="" className="w-10 h-10 rounded-full object-cover flex-shrink-0" />
                  )}
                </div>

                {hasStats && (
                  <div className="mt-3 flex gap-3 flex-wrap">
                    {statsPreview.map(([label, value]: [string, string]) => (
                      <div key={label} className="bg-black/30 rounded-lg px-2.5 py-1.5 text-center">
                        <div className="text-sparq-lime font-black text-sm">{value}</div>
                        <div className="text-gray-500 text-xs">{label.replace(' Per Game', '/G').replace(' Per ', '/').replace('Percentage', '%')}</div>
                      </div>
                    ))}
                  </div>
                )}
              </button>
            )
          })}

          {searched && !loading && results.length === 0 && !error && (
            <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 text-gray-400">
              No results found. Try a different name spelling.
            </div>
          )}
        </div>

        <div className="mt-6 text-center">
          <Link href="/onboarding/profile" className="text-sm text-gray-400 hover:text-sparq-lime">
            Can&apos;t find yourself? Skip manual entry
          </Link>
        </div>
      </div>
    </div>
  )
}
