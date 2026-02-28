'use client'

import Link from 'next/link'

import { useEffect, useMemo, useState } from 'react'
import { useUser } from '@clerk/nextjs'

interface College {
  id: number
  college_name: string
  college_city: string
  college_state: string
  division: string
  fit_score: number
  fit_reasons?: string[] | null
  status: string
}

const MOCK_FALLBACK: College[] = []

const DIVISION_FILTERS = ['All', 'D1', 'D2', 'D3', 'NAIA'] as const

const STATUS_CLASSES: Record<string, string> = {
  Researching: 'bg-white/10 text-gray-300',
  Interested: 'bg-blue-500/20 text-blue-300',
  Contacted: 'bg-yellow-500/20 text-yellow-300',
  Visited: 'bg-purple-500/20 text-purple-300',
  Offered: 'bg-green-500/20 text-green-300',
  Committed: 'bg-emerald-500/20 text-emerald-300',
  Declined: 'bg-red-500/20 text-red-300',
}

const STATUS_OPTIONS = ['Researching', 'Interested', 'Contacted', 'Visited', 'Offered', 'Committed', 'Declined']

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

type Tier = 'likely' | 'target' | 'reach'

function getTier(fitScore: number): Tier {
  if (fitScore >= 85) return 'likely'
  if (fitScore >= 75) return 'target'
  return 'reach'
}

const TIER_CONFIG: Record<Tier, { label: string; emoji: string; description: string; barColor: string; badgeClass: string }> = {
  likely: {
    label: 'Likely Fits',
    emoji: '🎯',
    description: 'Strong match — these programs recruit athletes with your profile',
    barColor: 'bg-sparq-lime',
    badgeClass: 'bg-sparq-lime/20 text-sparq-lime border-sparq-lime/30',
  },
  target: {
    label: 'Target Schools',
    emoji: '⚡',
    description: 'Solid fit — competitive but realistic with your stats',
    barColor: 'bg-yellow-400',
    badgeClass: 'bg-yellow-400/20 text-yellow-300 border-yellow-400/30',
  },
  reach: {
    label: 'Reach Schools',
    emoji: '🚀',
    description: 'Ambitious — worth pursuing but competition will be high',
    barColor: 'bg-orange-400',
    badgeClass: 'bg-orange-400/20 text-orange-300 border-orange-400/30',
  },
}

export default function CollegesPage() {
  const { user, isLoaded } = useUser()
  const [division, setDivision] = useState<(typeof DIVISION_FILTERS)[number]>('All')
  const [colleges, setColleges] = useState<College[]>([])
  const [loading, setLoading] = useState(true)
  const [statuses, setStatuses] = useState<Record<number, string>>({})
  const [enrichmentComplete, setEnrichmentComplete] = useState(false)
  const [toast, setToast] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const applyColleges = (list: College[]) => {
    setColleges(list)
    setStatuses((prev) => ({ ...Object.fromEntries(list.map((c) => [c.id, c.status])), ...prev }))
  }

  const loadColleges = async (clerkId?: string) => {
    if (!clerkId) {
      applyColleges([])
      setLoading(false)
      return
    }
    try {
      const res = await fetch(`${backendUrl}/api/workspace/colleges/${clerkId}`)
      const data = await res.json()
      const list = data.colleges && data.colleges.length > 0 ? data.colleges : MOCK_FALLBACK
      applyColleges(list)
    } catch {
      applyColleges([])
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (!isLoaded) return
    void loadColleges(user?.id)
  }, [isLoaded, user?.id])

  useEffect(() => {
    if (!toast) return
    const timer = setTimeout(() => setToast(''), 4500)
    return () => clearTimeout(timer)
  }, [toast])

  useEffect(() => {
    if (!isLoaded || !user?.id || enrichmentComplete) return

    const pollStatus = async () => {
      try {
        const res = await fetch(`${backendUrl}/api/workspace/enrichment-status/${user.id}`)
        if (!res.ok) return
        const data = await res.json() as { complete?: boolean }
        if (data.complete) {
          setEnrichmentComplete(true)
          setToast('Research complete — your fit breakdown is ready!')
          await loadColleges(user.id)
        }
      } catch {
        // no-op
      }
    }

    void pollStatus()
    const interval = setInterval(() => { void pollStatus() }, 30000)
    return () => clearInterval(interval)
  }, [backendUrl, enrichmentComplete, isLoaded, user?.id])

  const handleRefreshMatches = async () => {
    if (!user?.id || refreshing) return
    setRefreshing(true)
    setEnrichmentComplete(false)
    setToast('Finding new college matches for your profile...')
    try {
      await fetch(`${backendUrl}/api/workspace/trigger-matching/${user.id}`, { method: 'POST' })
      const poll = async () => {
        try {
          const res = await fetch(`${backendUrl}/api/workspace/enrichment-status/${user.id}`)
          if (!res.ok) return false
          const data = await res.json() as { complete?: boolean }
          return !!data.complete
        } catch { return false }
      }
      const interval = setInterval(async () => {
        const done = await poll()
        if (done) {
          clearInterval(interval)
          setRefreshing(false)
          setEnrichmentComplete(true)
          setToast('Matches refreshed — here are your updated college fits!')
          await loadColleges(user.id)
        }
      }, 15000)
      setTimeout(() => { clearInterval(interval); setRefreshing(false) }, 180000)
    } catch {
      setRefreshing(false)
      setToast('Refresh failed — try again in a moment')
    }
  }

  const updateStatus = (collegeId: number, newStatus: string) => {
    setStatuses((prev) => ({ ...prev, [collegeId]: newStatus }))
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
    fetch(`${backendUrl}/api/workspace/colleges/${collegeId}/status`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ status: newStatus }),
    }).catch(() => {})
  }

  const filteredColleges = useMemo(() => {
    if (division === 'All') return colleges
    return colleges.filter((college) => college.division === division)
  }, [colleges, division])

  const tieredColleges = useMemo(() => {
    const tiers: Record<Tier, College[]> = { likely: [], target: [], reach: [] }
    for (const c of filteredColleges) tiers[getTier(c.fit_score)].push(c)
    return tiers
  }, [filteredColleges])

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  const CollegeCard = ({ college }: { college: College }) => {
    const status = statuses[college.id]
    const hasEnrichedReasons = Array.isArray(college.fit_reasons) && college.fit_reasons.some(r => r && r.length > 30)
    const fitReasons = hasEnrichedReasons ? (college.fit_reasons as string[]).filter(Boolean).slice(0, 3) : null
    const tier = getTier(college.fit_score)
    const tierCfg = TIER_CONFIG[tier]

    return (
      <Link
        href={`/home/colleges/${college.id}`}
        className="bg-white/[0.04] border border-white/10 rounded-xl p-4 flex items-center gap-4 hover:border-sparq-lime/30 transition-colors cursor-pointer block"
      >
        <div className="w-12 h-12 rounded-xl bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center text-sparq-lime font-black text-lg">
          {college.college_name[0]}
        </div>

        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-bold text-white">{college.college_name}</span>
            <span className={`text-xs px-1.5 py-0.5 rounded-md border ${tierCfg.badgeClass}`}>
              {tierCfg.emoji} {tier === 'likely' ? 'Likely' : tier === 'target' ? 'Target' : 'Reach'}
            </span>
          </div>
          <div className="text-gray-400 text-sm">
            {college.college_city}, {college.college_state} • {college.division}
          </div>
          <div className="mt-2">
            <div className="w-full bg-white/10 rounded-full h-1.5 mt-1">
              <div
                style={{ width: `${college.fit_score}%` }}
                className={`h-1.5 rounded-full ${tierCfg.barColor}`}
              />
            </div>
            <div className="text-xs text-gray-400 mt-1">{college.fit_score}% match</div>
            {fitReasons ? (
              <ul className="mt-2 text-xs text-gray-300 space-y-1">
                {fitReasons.map((reason, index) => (
                  <li key={`${college.id}-reason-${index}`} className="flex items-start gap-1.5">
                    <span className="text-sparq-lime leading-4">•</span>
                    <span>{reason}</span>
                  </li>
                ))}
              </ul>
            ) : (
              <p className="mt-2 text-xs text-gray-500 italic flex items-center gap-1.5">
                <span className="w-1.5 h-1.5 rounded-full bg-yellow-400 animate-pulse inline-block" />
                Researching this program for you...
              </p>
            )}
          </div>
        </div>

        <select
          value={status}
          onClick={(e) => e.preventDefault()}
          onChange={(event) => { event.preventDefault(); updateStatus(college.id, event.target.value) }}
          className={`px-3 py-2 rounded-lg text-sm border border-white/10 focus:outline-none ${STATUS_CLASSES[status] || STATUS_CLASSES.Researching} [&>option]:bg-[#121212] [&>option]:text-white`}
        >
          {STATUS_OPTIONS.map((option) => (
            <option key={option} value={option}>{option}</option>
          ))}
        </select>
      </Link>
    )
  }

  return (
    <div className="text-white pb-8">
      <div className="p-8 pb-4">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-black text-white">Your College Matches</h1>
            <p className="text-gray-400 mt-1">{colleges.length} programs matched to your profile</p>
          </div>
          <button
            type="button"
            onClick={handleRefreshMatches}
            disabled={refreshing}
            className="flex items-center gap-2 px-4 py-2 rounded-xl border border-white/10 bg-white/[0.04] text-sm text-gray-300 hover:border-sparq-lime/40 hover:text-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed mt-1 shrink-0"
          >
            {refreshing ? (
              <>
                <span className="w-3.5 h-3.5 border-2 border-gray-400 border-t-transparent rounded-full animate-spin" />
                Finding matches...
              </>
            ) : (
              <>
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Refresh Matches
              </>
            )}
          </button>
        </div>
      </div>

      <div className="px-8 pb-4">
        <div className="flex flex-wrap gap-2">
          {DIVISION_FILTERS.map((filter) => {
            const active = division === filter
            return (
              <button
                key={filter}
                type="button"
                onClick={() => setDivision(filter)}
                className={`px-3 py-1.5 text-sm rounded-lg border border-white/10 ${
                  active ? 'bg-sparq-lime text-sparq-charcoal' : 'bg-white/10 text-gray-300'
                }`}
              >
                {filter}
              </button>
            )
          })}
        </div>
      </div>

      <div className="px-8 space-y-8">
        {(['likely', 'target', 'reach'] as Tier[]).map((tier) => {
          const tierColleges = tieredColleges[tier]
          if (tierColleges.length === 0) return null
          const cfg = TIER_CONFIG[tier]
          return (
            <div key={tier}>
              <div className="mb-3">
                <div className="flex items-center gap-2">
                  <span className="text-lg">{cfg.emoji}</span>
                  <h2 className="text-lg font-bold text-white">{cfg.label}</h2>
                  <span className="text-xs text-gray-500 bg-white/5 px-2 py-0.5 rounded-full">{tierColleges.length}</span>
                </div>
                <p className="text-xs text-gray-500 mt-0.5 ml-7">{cfg.description}</p>
              </div>
              <div className="space-y-3">
                {tierColleges.map((college) => (
                  <CollegeCard key={college.id} college={college} />
                ))}
              </div>
            </div>
          )
        })}

        {filteredColleges.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            <p className="text-lg font-semibold">No matches yet</p>
            <p className="text-sm mt-1">Complete onboarding or refresh to generate your college list</p>
          </div>
        )}
      </div>

      {toast && (
        <div className="fixed top-4 right-4 z-50 bg-black/80 border border-sparq-lime/40 text-sparq-lime text-sm px-4 py-3 rounded-xl backdrop-blur">
          {toast}
        </div>
      )}
    </div>
  )
}
