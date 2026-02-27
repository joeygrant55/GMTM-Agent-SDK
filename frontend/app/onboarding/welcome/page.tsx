'use client'

import { useEffect, useMemo, useState } from 'react'
import Link from 'next/link'
import { useUser } from '@clerk/nextjs'
import { MaxPrepsAthlete, MaxPrepsSeasonStats, ONBOARDING_MAXPREPS_KEY } from '@/app/onboarding/_lib/types'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

function latestSeasonStat(stats: MaxPrepsSeasonStats[] | undefined): MaxPrepsSeasonStats | null {
  if (!Array.isArray(stats) || stats.length === 0) return null
  return [...stats].sort((a, b) => {
    const yearA = Number((a.season || '').match(/\d{4}/)?.[0] || 0)
    const yearB = Number((b.season || '').match(/\d{4}/)?.[0] || 0)
    return yearB - yearA
  })[0]
}

function derivePercentile(athlete: MaxPrepsAthlete | null): number | null {
  const season = latestSeasonStat(athlete?.seasonStats)
  if (!season) return null

  const tackles = Number(season.tackles || 0)
  const interceptions = Number(season.interceptions || 0)
  const passBreakups = Number(season.passBreakups || 0)
  const touchdowns = Number(season.touchdowns || 0)
  const rushYards = Number(season.rushingYards || season.rush_yards || 0)
  const recYards = Number(season.receivingYards || season.rec_yards || 0)

  // Build a raw score from available stats.
  let score = 0
  if (tackles > 0) score += Math.min(tackles * 0.8, 40)
  if (interceptions > 0) score += Math.min(interceptions * 8, 30)
  if (passBreakups > 0) score += Math.min(passBreakups * 2, 15)
  if (touchdowns > 0) score += Math.min(touchdowns * 5, 30)
  if (rushYards > 0) score += Math.min(rushYards * 0.02, 25)
  if (recYards > 0) score += Math.min(recYards * 0.02, 25)

  // Convert to "top X%" where lower is better.
  const topPercent = Math.max(5, Math.round(50 - score * 0.7))
  return topPercent
}

function normalizeToTopPercent(value: number): number {
  const normalized = Math.round(100 - value)
  return Math.max(1, Math.min(99, normalized))
}

export default function OnboardingWelcomePage() {
  const { user, isLoaded } = useUser()
  const [athlete, setAthlete] = useState<MaxPrepsAthlete | null>(null)
  const [percentile, setPercentile] = useState<number | null>(null)
  const [collegeCount, setCollegeCount] = useState<number>(0)

  useEffect(() => {
    const raw = sessionStorage.getItem(ONBOARDING_MAXPREPS_KEY)
    if (!raw) return
    try {
      setAthlete(JSON.parse(raw) as MaxPrepsAthlete)
    } catch {
      setAthlete(null)
    }
  }, [])

  useEffect(() => {
    if (!isLoaded || !user?.id) return
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

    const loadCollegeCount = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/workspace/colleges/${user.id}`)
        if (!res.ok) return
        const data = await res.json() as { total?: number; colleges?: unknown[] }
        if (typeof data.total === 'number') {
          setCollegeCount(data.total)
        } else if (Array.isArray(data.colleges)) {
          setCollegeCount(data.colleges.length)
        }
      } catch {
        // no-op
      }
    }

    void loadCollegeCount()
  }, [isLoaded, user?.id])

  useEffect(() => {
    if (!athlete?.maxprepsAthleteId) {
      setPercentile(derivePercentile(athlete))
      return
    }

    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

    const loadPercentile = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/quick-scan/${athlete.maxprepsAthleteId}`)
        if (!res.ok) throw new Error('quick-scan unavailable')
        const data = await res.json() as {
          percentile?: number
          overall_percentile?: number
          metrics?: { percentile?: number }[]
        }

        if (typeof data.percentile === 'number') {
          setPercentile(normalizeToTopPercent(data.percentile))
          return
        }
        if (typeof data.overall_percentile === 'number') {
          setPercentile(normalizeToTopPercent(data.overall_percentile))
          return
        }
        if (Array.isArray(data.metrics) && data.metrics.length > 0) {
          const nums = data.metrics
            .map((m) => m.percentile)
            .filter((n): n is number => typeof n === 'number')
          if (nums.length) {
            const avg = nums.reduce((sum, n) => sum + n, 0) / nums.length
            setPercentile(normalizeToTopPercent(avg))
            return
          }
        }
      } catch {
        // Fallback below
      }

      setPercentile(derivePercentile(athlete))
    }

    void loadPercentile()
  }, [athlete])

  const latestSeason = useMemo(() => latestSeasonStat(athlete?.seasonStats), [athlete])
  const firstName = (athlete?.name || user?.firstName || 'Athlete').split(' ')[0]
  const classYear = athlete?.classYear || 'Unknown'
  const position = athlete?.position || 'Athlete'

  const statTiles = [
    { label: 'Tackles', value: latestSeason?.tackles ?? '—' },
    { label: 'INTs', value: latestSeason?.interceptions ?? '—' },
    { label: 'PBUs', value: latestSeason?.passBreakups ?? '—' },
  ]

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white px-4 py-10 sm:py-14">
      <div className="max-w-3xl mx-auto min-h-[85vh] flex flex-col items-center justify-center text-center">
        <div className="opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '0ms' }}>
          <img src="/sparq-logo.jpg" alt="SPARQ" className="w-12 h-12 rounded-xl mx-auto border border-white/10" />
        </div>

        <div className="mt-6 opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '200ms' }}>
          <p className="text-lg text-gray-300">Welcome to SPARQ, {firstName}. 👋</p>
          <h1 className="mt-4 text-4xl sm:text-5xl font-black leading-tight text-white">
            You rank in the top <span className="text-sparq-lime">{percentile !== null ? `${percentile}%` : '—'}</span>
          </h1>
          <p className="mt-2 text-xl sm:text-2xl text-gray-200">
            of {position}s in the Class of {classYear} nationally.
          </p>
        </div>

        <div className="w-full mt-8 border-t border-b border-white/10 py-6 opacity-0 [animation:slideIn_0.6s_ease-out_forwards]" style={{ animationDelay: '400ms' }}>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            {statTiles.map((tile) => (
              <div key={tile.label} className="bg-white/[0.04] border border-white/10 rounded-xl p-4">
                <p className="text-2xl font-black text-sparq-lime">{tile.value}</p>
                <p className="text-xs uppercase tracking-wide text-gray-400 mt-1">{tile.label}</p>
              </div>
            ))}
          </div>
          {athlete?.school && (
            <p className="mt-4 text-gray-300 text-sm">
              {athlete.school}
              {athlete.teamRecord ? ` — ${athlete.teamRecord}` : ''}
            </p>
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
