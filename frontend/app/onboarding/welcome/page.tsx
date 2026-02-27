'use client'

import { useEffect, useState } from 'react'
import Link from 'next/link'
import { useUser } from '@clerk/nextjs'
import { MaxPrepsAthlete, ONBOARDING_MAXPREPS_KEY } from '@/app/onboarding/_lib/types'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

// High school benchmarks: avg ≈ 50th percentile, elite ≈ 99th percentile nationally
const SPORT_BENCHMARKS: Record<string, { stat: string; elite: number; avg: number }[]> = {
  Basketball: [
    { stat: 'Points Per Game', elite: 18, avg: 6 },
    { stat: 'Rebounds Per Game', elite: 10, avg: 4 },
    { stat: 'Assists Per Game', elite: 6, avg: 2 },
    { stat: 'Steals Per Game', elite: 4, avg: 1.2 },
    { stat: 'Blocks Per Game', elite: 3, avg: 0.6 },
  ],
  Football: [
    { stat: 'Passing Yards', elite: 2500, avg: 900 },
    { stat: 'Rushing Yards', elite: 1400, avg: 500 },
    { stat: 'Tackles', elite: 90, avg: 40 },
    { stat: 'Touchdowns', elite: 18, avg: 6 },
    { stat: 'Interceptions', elite: 8, avg: 2 },
    { stat: 'Receptions', elite: 60, avg: 25 },
    { stat: 'Sacks', elite: 12, avg: 4 },
  ],
  Soccer: [
    { stat: 'Goals', elite: 22, avg: 6 },
    { stat: 'Assists', elite: 12, avg: 4 },
    { stat: 'Saves', elite: 120, avg: 50 },
  ],
  Volleyball: [
    { stat: 'Kills', elite: 350, avg: 120 },
    { stat: 'Assists', elite: 900, avg: 300 },
    { stat: 'Digs', elite: 400, avg: 150 },
    { stat: 'Aces', elite: 60, avg: 20 },
  ],
  Baseball: [
    { stat: 'Batting Average', elite: 0.42, avg: 0.26 },
    { stat: 'Home Runs', elite: 8, avg: 2 },
    { stat: 'RBI', elite: 40, avg: 15 },
    { stat: 'ERA', elite: 1.2, avg: 3.5 },
    { stat: 'Strikeouts', elite: 80, avg: 35 },
  ],
  Softball: [
    { stat: 'Batting Average', elite: 0.44, avg: 0.28 },
    { stat: 'Home Runs', elite: 8, avg: 2 },
    { stat: 'RBI', elite: 40, avg: 15 },
    { stat: 'ERA', elite: 0.8, avg: 2.5 },
  ],
  Lacrosse: [
    { stat: 'Goals', elite: 50, avg: 15 },
    { stat: 'Assists', elite: 30, avg: 10 },
  ],
  Wrestling: [
    { stat: 'Wins', elite: 40, avg: 18 },
    { stat: 'Pins', elite: 25, avg: 8 },
  ],
}

function statPercentile(value: number, avg: number, elite: number, lowerIsBetter = false): number {
  const ratio = lowerIsBetter
    ? (avg - value) / (avg - elite)
    : (value - avg) / (elite - avg)
  return Math.min(99, Math.max(1, Math.round(50 + ratio * 49)))
}

function estimatePercentile(sport: string | null, statsPreview: [string, string][]): number | null {
  if (!sport || !statsPreview?.length) return null
  const benchmarks = SPORT_BENCHMARKS[sport]
  if (!benchmarks) return null

  const lowerIsBetter = new Set(['ERA', 'Goals Allowed'])

  const scores: number[] = []
  for (const [label, rawValue] of statsPreview) {
    const value = parseFloat(rawValue)
    if (isNaN(value)) continue
    const bench = benchmarks.find(b => label === b.stat || label.startsWith(b.stat.split(' ')[0]))
    if (!bench) continue
    scores.push(statPercentile(value, bench.avg, bench.elite, lowerIsBetter.has(bench.stat)))
  }
  if (!scores.length) return null

  // Headline = primary stat only (21.2 PPG → top 1%, not dragged down by avg rebounds)
  return scores[0]
}

export default function OnboardingWelcomePage() {
  const { user, isLoaded } = useUser()
  const [athlete, setAthlete] = useState<MaxPrepsAthlete | null>(null)
  const [statsPreview, setStatsPreview] = useState<[string, string][]>([])
  const [lastSeason, setLastSeason] = useState<string | null>(null)
  const [percentile, setPercentile] = useState<number | null>(null)
  const [collegeCount, setCollegeCount] = useState<number>(0)

  useEffect(() => {
    const raw = sessionStorage.getItem(ONBOARDING_MAXPREPS_KEY)
    if (!raw) return
    try {
      const parsed = JSON.parse(raw) as MaxPrepsAthlete & { statsPreview?: [string, string][]; lastSeason?: string }
      setAthlete(parsed)
      const preview = parsed.statsPreview || []
      setStatsPreview(preview)
      setLastSeason(parsed.lastSeason || null)
      setPercentile(estimatePercentile(parsed.sport || null, preview))
    } catch {
      setAthlete(null)
    }
  }, [])

  useEffect(() => {
    if (!isLoaded || !user?.id) return
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
    fetch(`${backendUrl}/api/workspace/colleges/${user.id}`)
      .then(r => r.ok ? r.json() : null)
      .then(data => {
        if (!data) return
        if (typeof data.total === 'number') setCollegeCount(data.total)
        else if (Array.isArray(data.colleges)) setCollegeCount(data.colleges.length)
      })
      .catch(() => {})
  }, [isLoaded, user?.id])

  const firstName = (athlete?.name || user?.firstName || 'Athlete').split(' ')[0]
  const position = athlete?.position || 'Athlete'
  const sport = (athlete as any)?.sport || null
  const displaySport = sport || position

  // Shorten stat labels for display
  function shortLabel(label: string) {
    return label
      .replace(' Per Game', '/G')
      .replace('Points', 'Pts').replace('Rebounds', 'Reb').replace('Assists', 'Ast')
      .replace('Steals', 'Stl').replace('Blocks', 'Blk')
      .replace('Batting Average', 'AVG').replace('Home Runs', 'HR')
      .replace('Passing Yards', 'Pass Yds').replace('Rushing Yards', 'Rush Yds')
      .replace('Touchdowns', 'TDs').replace('Interceptions', 'INTs')
  }

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white px-4 py-10 sm:py-14">
      <div className="max-w-3xl mx-auto min-h-[85vh] flex flex-col items-center justify-center text-center">

        <div className="opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '0ms' }}>
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-12 h-12 rounded-xl mx-auto border border-white/10" />
        </div>

        <div className="mt-6 opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '200ms' }}>
          <p className="text-lg text-gray-300">Welcome to SPARQ, {firstName}. 👋</p>
          {percentile !== null ? (
            <>
              <h1 className="mt-4 text-4xl sm:text-5xl font-black leading-tight">
                You rank in the top <span className="text-sparq-lime">{100 - percentile}%</span>
              </h1>
              <p className="mt-2 text-xl text-gray-200">
                of {position}s nationally{lastSeason ? ` (${lastSeason} season)` : ''}.
              </p>
            </>
          ) : (
            <>
              <h1 className="mt-4 text-4xl sm:text-5xl font-black leading-tight">
                Your profile is <span className="text-sparq-lime">live.</span>
              </h1>
              <p className="mt-2 text-xl text-gray-200">
                {displaySport} · {athlete?.school || 'Athlete'}
              </p>
            </>
          )}
        </div>

        <div className="w-full mt-8 border-t border-b border-white/10 py-6 opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '400ms' }}>
          {statsPreview.length > 0 ? (
            <>
              <p className="text-xs uppercase tracking-widest text-gray-500 mb-4">
                {lastSeason ? `${lastSeason} Season Stats` : 'Season Stats'}
              </p>
              <div className={`grid gap-3 ${statsPreview.length === 2 ? 'grid-cols-2' : statsPreview.length >= 4 ? 'grid-cols-2 sm:grid-cols-4' : 'grid-cols-3'}`}>
                {statsPreview.map(([label, value]) => (
                  <div key={label} className="bg-white/[0.04] border border-white/10 rounded-xl p-4">
                    <p className="text-2xl font-black text-sparq-lime">{value}</p>
                    <p className="text-xs uppercase tracking-wide text-gray-400 mt-1">{shortLabel(label)}</p>
                  </div>
                ))}
              </div>
            </>
          ) : (
            <p className="text-gray-500 text-sm">No season stats available — your profile is built from your MaxPreps data.</p>
          )}
          {athlete?.school && (
            <p className="mt-4 text-gray-400 text-sm">{athlete.school}</p>
          )}
        </div>

        <div className="mt-6 opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '600ms' }}>
          <p className="text-lg text-gray-200 flex items-center justify-center gap-2">
            <span className="w-2 h-2 rounded-full bg-sparq-lime animate-pulse" />
            <span><strong className="text-sparq-lime">{collegeCount}</strong> programs are being matched to your profile right now.</span>
          </p>
          <Link href="/home" className="inline-flex mt-6 bg-sparq-lime text-sparq-charcoal px-6 py-3 rounded-xl font-black">
            Enter Your Workspace →
          </Link>
        </div>

      </div>
    </div>
  )
}
