'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { MaxPrepsAthlete, ONBOARDING_MAXPREPS_KEY } from '@/app/onboarding/_lib/types'

const BACKEND_URL = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'

interface StatCategory { name: string; seasonValue: string }
interface Season { sport: string; season: string; position: string; stats: Record<string, string> }
interface AthleteStats { athleteName: string; sport: string | null; position: string | null; seasons: Season[] }

const SPORT_STAT_PRIORITY: Record<string, string[]> = {
  Basketball: ['Points Per Game', 'Rebounds Per Game', 'Assists Per Game', 'Steals Per Game', 'Blocks Per Game'],
  Football: ['Passing Yards', 'Touchdowns', 'Tackles', 'Interceptions', 'Rushing Yards', 'Receptions', 'Sacks'],
  Soccer: ['Goals', 'Assists', 'Saves', 'Goals Allowed', 'Shots On Goal'],
  Baseball: ['Batting Average', 'Home Runs', 'RBI', 'ERA', 'Strikeouts', 'OBP'],
  Softball: ['Batting Average', 'Home Runs', 'RBI', 'ERA', 'Strikeouts'],
  Volleyball: ['Kills', 'Assists', 'Digs', 'Blocks', 'Aces'],
  Lacrosse: ['Goals', 'Assists', 'Ground Balls', 'Saves'],
  Wrestling: ['Wins', 'Pins', 'Technical Falls'],
}

function getTopStats(sport: string | null, stats: Record<string, string>): StatCategory[] {
  const priority = (sport && SPORT_STAT_PRIORITY[sport]) || []
  const keys = Object.keys(stats)
  const ordered = [...priority.filter(k => keys.includes(k)), ...keys.filter(k => !priority.includes(k))]
  return ordered.slice(0, 4).map(name => ({ name, seasonValue: stats[name] }))
}

export default function ConfirmMaxPrepsPage() {
  const router = useRouter()
  const [athlete, setAthlete] = useState<MaxPrepsAthlete | null>(null)
  const [statsData, setStatsData] = useState<AthleteStats | null>(null)
  const [loadingStats, setLoadingStats] = useState(false)
  const [statsError, setStatsError] = useState(false)

  useEffect(() => {
    const raw = sessionStorage.getItem(ONBOARDING_MAXPREPS_KEY)
    if (!raw) return
    try { setAthlete(JSON.parse(raw) as MaxPrepsAthlete) }
    catch { sessionStorage.removeItem(ONBOARDING_MAXPREPS_KEY) }
  }, [])

  useEffect(() => {
    const profileUrl = (athlete as any)?.profileUrl
    if (!profileUrl) return
    setLoadingStats(true)
    fetch(`${BACKEND_URL}/api/maxpreps/athlete-stats?url=${encodeURIComponent(profileUrl)}`)
      .then(r => r.ok ? r.json() : Promise.reject(r.status))
      .then((data: AthleteStats) => { setStatsData(data); setLoadingStats(false) })
      .catch(() => { setStatsError(true); setLoadingStats(false) })
  }, [athlete])

  if (!athlete) return (
    <div className="min-h-screen bg-sparq-charcoal text-white flex items-center justify-center px-4">
      <div className="max-w-md w-full bg-white/[0.04] border border-white/10 rounded-2xl p-6 text-center">
        <h1 className="text-2xl font-black">No MaxPreps data found</h1>
        <p className="mt-3 text-gray-400">Search for your profile first.</p>
        <button onClick={() => router.push('/onboarding/search')}
          className="mt-6 bg-sparq-lime text-sparq-charcoal font-black rounded-xl px-5 py-3">Back to Search</button>
      </div>
    </div>
  )

  const latestSeason = statsData?.seasons?.[statsData.seasons.length - 1]
  const topStats = latestSeason ? getTopStats(statsData?.sport ?? null, latestSeason.stats) : []
  const displaySport = statsData?.sport ?? (athlete as any)?.position ?? 'Athlete'
  const displayPosition = statsData?.position ?? null

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      <div className="mx-auto max-w-3xl px-4 py-12 sm:py-16">
        <p className="text-sm font-semibold tracking-widest text-sparq-lime uppercase text-center">Step 2 of 4</p>
        <h1 className="mt-3 text-center text-4xl font-black">Here&apos;s what we found</h1>

        <div className="mt-8 bg-white/[0.04] border border-white/10 rounded-2xl p-5">
          <h2 className="text-2xl font-black">{athlete.name}</h2>
          <p className="mt-1 text-gray-300">
            {[displayPosition, displaySport, athlete.school].filter(Boolean).join(' · ')}
          </p>
          {athlete.classYear && <p className="mt-1 text-gray-400">Class of {athlete.classYear}</p>}

          <div className="mt-6">
            {loadingStats && (
              <div className="animate-pulse">
                <div className="h-3 w-24 bg-white/10 rounded mb-3" />
                <div className="grid grid-cols-3 gap-3">
                  {[0,1,2].map(i => (
                    <div key={i} className="bg-black/30 border border-white/10 rounded-xl p-3">
                      <div className="h-6 w-10 bg-white/10 rounded mb-1" /><div className="h-3 w-16 bg-white/10 rounded" />
                    </div>
                  ))}
                </div>
              </div>
            )}

            {!loadingStats && topStats.length > 0 && (
              <>
                <h3 className="text-sm uppercase tracking-wide text-gray-400">
                  {latestSeason?.season ? `${latestSeason.season} season` : 'This season'}
                </h3>
                <div className="mt-3 grid grid-cols-2 sm:grid-cols-4 gap-3">
                  {topStats.map(stat => (
                    <div key={stat.name} className="bg-black/30 border border-white/10 rounded-xl p-3">
                      <p className="text-xl font-black text-sparq-lime">{stat.seasonValue ?? '—'}</p>
                      <p className="text-xs text-gray-400 mt-0.5">{stat.name}</p>
                    </div>
                  ))}
                </div>
              </>
            )}

            {!loadingStats && topStats.length === 0 && !statsError && (
              <p className="text-gray-500 text-sm">No stats available for this profile.</p>
            )}
            {statsError && (
              <p className="text-gray-500 text-sm">Stats unavailable — continuing with profile info.</p>
            )}

            {!loadingStats && statsData && statsData.seasons.length > 1 && (
              <div className="mt-6">
                <h3 className="text-sm uppercase tracking-wide text-gray-400 mb-3">Career progression</h3>
                <div className="space-y-2">
                  {[...statsData.seasons].reverse().map((season, idx) => {
                    const keyStats = getTopStats(statsData.sport, season.stats).slice(0, 2)
                    return (
                      <div key={`${season.season}-${idx}`}
                        className="flex items-center justify-between bg-black/30 border border-white/10 rounded-xl p-3">
                        <p className="text-gray-300 text-sm font-medium">{season.season}</p>
                        <p className="text-gray-400 text-sm">{keyStats.map(s => `${s.seasonValue} ${s.name}`).join(' · ')}</p>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        </div>

        <div className="mt-8 flex flex-col sm:flex-row gap-3 sm:items-center">
          <button onClick={() => router.push('/onboarding/profile')}
            className="bg-sparq-lime text-sparq-charcoal font-black rounded-xl px-6 py-3">This is me →</button>
          <button onClick={() => router.push('/onboarding/search')}
            className="text-gray-400 hover:text-sparq-lime px-2 py-1 text-left">Not me, search again</button>
        </div>
      </div>
    </div>
  )
}
