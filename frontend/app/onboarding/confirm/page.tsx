'use client'

import { useEffect, useMemo, useState } from 'react'
import { useRouter } from 'next/navigation'
import { MaxPrepsAthlete, MaxPrepsSeasonStats, ONBOARDING_MAXPREPS_KEY } from '@/app/onboarding/_lib/types'

function toSeasonYear(season?: string): number {
  if (!season) return 0
  const match = season.match(/\d{4}/)
  return match ? Number(match[0]) : 0
}

function formatSeasonLabel(stat: MaxPrepsSeasonStats): string {
  return stat.season || 'Season'
}

export default function ConfirmMaxPrepsPage() {
  const router = useRouter()
  const [athlete, setAthlete] = useState<MaxPrepsAthlete | null>(null)

  useEffect(() => {
    const raw = sessionStorage.getItem(ONBOARDING_MAXPREPS_KEY)
    if (!raw) return

    try {
      const parsed = JSON.parse(raw) as MaxPrepsAthlete
      setAthlete(parsed)
    } catch {
      sessionStorage.removeItem(ONBOARDING_MAXPREPS_KEY)
    }
  }, [])

  const sortedStats = useMemo(() => {
    if (!athlete?.seasonStats?.length) return []
    return [...athlete.seasonStats].sort((a, b) => toSeasonYear(a.season) - toSeasonYear(b.season))
  }, [athlete])

  const currentSeason = sortedStats[sortedStats.length - 1]
  const previousSeason = sortedStats[sortedStats.length - 2]

  const tackleGrowth = useMemo(() => {
    if (!currentSeason?.tackles || !previousSeason?.tackles || previousSeason.tackles === 0) return null
    const change = ((currentSeason.tackles - previousSeason.tackles) / previousSeason.tackles) * 100
    return Math.round(change)
  }, [currentSeason, previousSeason])

  if (!athlete) {
    return (
      <div className="min-h-screen bg-sparq-charcoal text-white flex items-center justify-center px-4">
        <div className="max-w-md w-full bg-white/[0.04] border border-white/10 rounded-2xl p-6 text-center">
          <h1 className="text-2xl font-black">No MaxPreps data found</h1>
          <p className="mt-3 text-gray-400">Search for your profile first.</p>
          <button
            onClick={() => router.push('/onboarding/search')}
            className="mt-6 bg-sparq-lime text-sparq-charcoal font-black rounded-xl hover:bg-sparq-lime-dark px-5 py-3"
          >
            Back to Search
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
        <p className="text-sm font-semibold tracking-widest text-sparq-lime uppercase text-center">Step 2 of 4</p>
        <h1 className="mt-3 text-center text-4xl font-black">Here&apos;s what we found</h1>

        <div className="mt-8 bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <h2 className="text-2xl font-black">{athlete.name}</h2>
          <p className="mt-1 text-gray-300">{athlete.position || 'Athlete'} · {athlete.school || 'School unavailable'}</p>
          <p className="mt-1 text-gray-400">Class of {athlete.classYear || 'Unknown'}</p>

          <div className="mt-6">
            <h3 className="text-sm uppercase tracking-wide text-gray-400">This season</h3>
            <div className="mt-3 grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="bg-black/30 border border-white/10 rounded-xl p-3">
                <p className="text-xl font-black text-sparq-lime">{currentSeason?.tackles ?? '—'}</p>
                <p className="text-xs text-gray-400">Tackles</p>
              </div>
              <div className="bg-black/30 border border-white/10 rounded-xl p-3">
                <p className="text-xl font-black text-sparq-lime">{currentSeason?.interceptions ?? '—'}</p>
                <p className="text-xs text-gray-400">INTs</p>
              </div>
              <div className="bg-black/30 border border-white/10 rounded-xl p-3">
                <p className="text-xl font-black text-sparq-lime">{currentSeason?.passBreakups ?? '—'}</p>
                <p className="text-xs text-gray-400">PBUs</p>
              </div>
            </div>
            {athlete.teamRecord && <p className="mt-3 text-gray-400 text-sm">Team record: {athlete.teamRecord}</p>}
          </div>

          {sortedStats.length > 1 && (
            <div className="mt-6">
              <h3 className="text-sm uppercase tracking-wide text-gray-400">Career progression</h3>
              <div className="mt-3 space-y-2">
                {sortedStats.map((season, idx) => (
                  <div key={`${season.season || idx}`} className="flex items-center justify-between bg-black/30 border border-white/10 rounded-xl p-3">
                    <p className="text-gray-300">
                      {formatSeasonLabel(season)}: {season.tackles ?? '—'} tackles, {season.interceptions ?? '—'} INTs
                    </p>
                    {idx === sortedStats.length - 1 && tackleGrowth !== null && (
                      <span className="text-xs font-semibold text-sparq-lime">{tackleGrowth >= 0 ? `↑ ${tackleGrowth}%` : `${tackleGrowth}%`}</span>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        <div className="mt-8 flex flex-col sm:flex-row gap-3 sm:items-center">
          <button
            onClick={() => router.push('/onboarding/profile')}
            className="bg-sparq-lime text-sparq-charcoal font-black rounded-xl hover:bg-sparq-lime-dark px-6 py-3"
          >
            This is me →
          </button>
          <button
            onClick={() => router.push('/onboarding/search')}
            className="text-gray-400 hover:text-sparq-lime px-2 py-1 text-left"
          >
            Not me, search again
          </button>
        </div>
      </div>
    </div>
  )
}
