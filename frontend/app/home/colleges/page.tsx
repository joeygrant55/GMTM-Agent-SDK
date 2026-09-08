'use client'

import { apiFetch } from '@/app/_lib/api'

import dynamic from 'next/dynamic'

import Link from 'next/link'
import { useSearchParams } from 'next/navigation'

import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import { supportedCombineEvent } from '../components/currentCombine'

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

function CollegesPage() {
  const { user, isLoaded } = useUser()
  if (!isLoaded) return <p role="status" className="p-8 text-gray-400">Loading your account…</p>
  if (!user?.id) return <p className="p-8 text-gray-400">Sign in to see your saved college matches.</p>
  return <CollegeSession key={user.id} clerkId={user.id} />
}

interface ResearchRequest {
  controller: AbortController
  pollTimer?: ReturnType<typeof setTimeout>
  deadlineTimer?: ReturnType<typeof setTimeout>
}

function CollegeSession({ clerkId }: { clerkId: string }) {
  const params = useSearchParams()
  const rawEvent = params.get('event_id')
  const eventId = rawEvent && /^\d+$/.test(rawEvent) ? supportedCombineEvent(Number(rawEvent)) : null
  const combineHref = eventId ? `/home/inbox?event_id=${eventId}` : '/home/inbox'
  const [division, setDivision] = useState<(typeof DIVISION_FILTERS)[number]>('All')
  const [colleges, setColleges] = useState<College[]>([])
  const [loading, setLoading] = useState(true)
  const [statuses, setStatuses] = useState<Record<number, string>>({})
  const [loadError, setLoadError] = useState('')
  const [researchState, setResearchState] = useState<'idle' | 'requesting' | 'waiting'>('idle')
  const [researchMessage, setResearchMessage] = useState('')
  const [researchError, setResearchError] = useState('')
  const lifetime = useRef<AbortController | null>(null)
  const request = useRef<ResearchRequest | null>(null)
  const readGeneration = useRef(0)
  const refreshing = researchState !== 'idle'

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const stopChecking = useCallback(() => {
    const active = request.current
    request.current = null
    if (!active) return
    active.controller.abort()
    clearTimeout(active.pollTimer)
    clearTimeout(active.deadlineTimer)
  }, [])

  const loadColleges = useCallback(async (signal: AbortSignal): Promise<'loaded' | 'failed' | 'superseded'> => {
    const generation = ++readGeneration.current
    const isCurrentRead = () => !signal.aborted && readGeneration.current === generation
    setLoadError('')
    try {
      const res = await apiFetch(`${backendUrl}/api/workspace/colleges/${clerkId}`, { signal })
      if (!res.ok) throw new Error('Saved matches unavailable')
      const data = await res.json()
      if (!isCurrentRead()) return 'superseded'
      if (!Array.isArray(data.colleges) || !data.colleges.every((college: College) =>
        college && Number.isSafeInteger(college.id) && typeof college.college_name === 'string'
        && typeof college.fit_score === 'number' && Number.isFinite(college.fit_score))) {
        throw new Error('Saved matches unconfirmed')
      }
      setColleges(data.colleges)
      setStatuses(Object.fromEntries(data.colleges.map((college: College) => [college.id, college.status])))
      return 'loaded'
    } catch {
      if (!isCurrentRead()) return 'superseded'
      setLoadError('We could not load your saved college matches. Try loading them again.')
      return 'failed'
    } finally {
      if (isCurrentRead()) setLoading(false)
    }
  }, [backendUrl, clerkId])

  useEffect(() => {
    const controller = new AbortController()
    lifetime.current = controller
    void loadColleges(controller.signal)
    return () => {
      controller.abort()
      stopChecking()
      if (lifetime.current === controller) lifetime.current = null
    }
  }, [loadColleges, stopChecking])

  const handleRefreshMatches = async () => {
    if (!lifetime.current || lifetime.current.signal.aborted || request.current) return
    const active: ResearchRequest = { controller: new AbortController() }
    request.current = active
    const isCurrent = () => request.current === active && !active.controller.signal.aborted
    const finish = (message: string, error = '') => {
      if (!isCurrent()) return
      stopChecking()
      setResearchState('idle')
      setResearchMessage(message)
      setResearchError(error)
    }
    setResearchState('requesting')
    setResearchMessage('')
    setResearchError('')
    // A hung acceptance request must not leave this page permanently busy.
    active.deadlineTimer = setTimeout(() => finish('', 'We could not confirm whether your research request was accepted. Reload saved matches before making another request.'), 30000)
    try {
      const res = await apiFetch(`${backendUrl}/api/workspace/trigger-matching/${clerkId}`, { method: 'POST', signal: active.controller.signal })
      if (!isCurrent()) return
      if (!res.ok) {
        finish('', res.status === 422
          ? 'College research needs a sport in your recruiting profile. Your combine progress is still available in My next move.'
          : res.status === 401 ? 'Sign in again before requesting college research.'
          : 'Your research request was not accepted. Try again later; your saved matches are unchanged.')
        return
      }
      const data = await res.json()
      if (!isCurrent()) return
      if (data.status !== 'matching started' || !Number.isSafeInteger(data.profile_id) || data.profile_id <= 0) {
        throw new Error('Research acceptance unconfirmed')
      }
      clearTimeout(active.deadlineTimer)
      setResearchState('waiting')
      setResearchMessage('Matching request accepted. Checking for saved research updates…')
      active.deadlineTimer = setTimeout(() => finish('We stopped checking after three minutes. Research may still be running. You can reload saved matches without starting another request.'), 180000)
      const poll = async () => {
        if (!isCurrent()) return
        try {
          const status = await apiFetch(`${backendUrl}/api/workspace/enrichment-status/${clerkId}`, { signal: active.controller.signal })
          if (!isCurrent()) return
          if (!status.ok) throw new Error('Research status unavailable')
          const result = await status.json()
          if (!isCurrent()) return
          if (typeof result.complete !== 'boolean') throw new Error('Research status unconfirmed')
          if (result.complete) {
            // This legacy flag is not a job ID or proof this request completed.
            const outcome = await loadColleges(active.controller.signal)
            if (outcome === 'superseded') finish('Research status is available.')
            else finish(outcome === 'loaded' ? 'Saved college research is available. Review the current matches below.' : '', outcome === 'loaded' ? '' : 'Research status is available, but the saved matches could not be reloaded.')
          } else {
            active.pollTimer = setTimeout(() => { void poll() }, 15000)
          }
        } catch {
          finish('', 'We could not check for research updates. Research may still be running. Reload saved matches before making another request.')
        }
      }
      active.pollTimer = setTimeout(() => { void poll() }, 15000)
    } catch {
      finish('', 'We could not confirm whether your research request was accepted. Reload saved matches before making another request.')
    }
  }

  const updateStatus = (collegeId: number, newStatus: string) => {
    setStatuses((prev) => ({ ...prev, [collegeId]: newStatus }))
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
    apiFetch(`${backendUrl}/api/workspace/colleges/${collegeId}/status`, {
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
    const hasEnrichedReasons = Array.isArray(college.fit_reasons) && college.fit_reasons.some(r => typeof r === 'string' && r.length > 30)
    const fitReasons = hasEnrichedReasons ? (college.fit_reasons as string[]).filter(reason => typeof reason === 'string' && reason.trim()).slice(0, 3) : null
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
              <p className="mt-2 text-xs text-gray-500 italic">Detailed fit research is not available for this program.</p>
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
            <p className="text-gray-400 mt-1">{loadError ? (colleges.length ? 'Showing matches from your last successful check' : 'Saved college matches are unavailable') : `${colleges.length} programs matched to your profile`}</p>
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
                {researchState === 'requesting' ? 'Requesting research…' : 'Checking saved research…'}
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

        {!loadError && filteredColleges.length === 0 && (
          <div className="text-center py-16 text-gray-500">
            <p className="text-lg font-semibold">{colleges.length === 0 ? 'No college matches are saved.' : 'No saved matches in this division.'}</p>
            <p className="text-sm mt-1">Your combine progress is available in <Link href={combineHref} className="text-sparq-lime underline">My next move</Link>.</p>
          </div>
        )}
      </div>

      <div className="px-8 mt-4 space-y-3">
        {loadError && <p role="alert" className="text-sm text-amber-200">{loadError}</p>}
        {researchError && <p role="alert" className="text-sm text-amber-200">{researchError}</p>}
        {researchMessage && <p role="status" className="text-sm text-gray-300">{researchMessage}</p>}
        {(loadError || researchError || researchMessage) && <button type="button" onClick={() => { if (lifetime.current) void loadColleges(lifetime.current.signal) }} className="min-h-11 text-sm text-sparq-lime underline">Reload saved matches</button>}
      </div>
    </div>
  )
}


export default dynamic(() => Promise.resolve(CollegesPage), { ssr: false })
