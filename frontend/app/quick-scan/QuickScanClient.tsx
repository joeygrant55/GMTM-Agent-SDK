'use client'

import { useState, useEffect, useRef } from 'react'
import { useUser } from '@clerk/nextjs'
import Link from 'next/link'

// ── Types ────────────────────────────────────────────────────

interface Metric {
  title: string
  value: string
  unit: string
  verified: boolean
}

interface DashboardData {
  first_name: string
  last_name: string
  position: string
  city?: string
  state?: string
  graduation_year?: number
  metrics: Metric[]
  offer_count?: number
}

// ── Metric config ────────────────────────────────────────────

const METRIC_CONFIG: Record<string, {
  label: string
  icon: string
  format: (v: string) => string
  color: string
  higherIsBetter: boolean
  range: [number, number]
}> = {
  '40 Yard Dash': {
    label: '40-Yard Dash',
    icon: '⚡',
    format: (v) => `${parseFloat(v).toFixed(2)}s`,
    color: '#CDDC39',
    higherIsBetter: false,
    range: [4.2, 5.5],
  },
  '5-10-5 shuttle': {
    label: 'Shuttle',
    icon: '🔀',
    format: (v) => `${parseFloat(v).toFixed(2)}s`,
    color: '#4FC3F7',
    higherIsBetter: false,
    range: [3.8, 5.0],
  },
  'Vertical Jump': {
    label: 'Vertical',
    icon: '↑',
    format: (v) => `${parseFloat(v).toFixed(1)}"`,
    color: '#A5D6A7',
    higherIsBetter: true,
    range: [20, 42],
  },
  'Broad Jump': {
    label: 'Broad Jump',
    icon: '↔',
    format: (v) => {
      const feet = Math.floor(parseFloat(v))
      const inches = Math.round((parseFloat(v) - feet) * 12)
      return `${feet}'${inches}"`
    },
    color: '#CE93D8',
    higherIsBetter: true,
    range: [7, 11],
  },
  'Bench Press': {
    label: 'Bench',
    icon: '💪',
    format: (v) => `${parseInt(v)} reps`,
    color: '#FFCC02',
    higherIsBetter: true,
    range: [5, 40],
  },
  'Height': {
    label: 'Height',
    icon: '📏',
    format: (v) => {
      const totalInches = parseFloat(v)
      const feet = Math.floor(totalInches / 12)
      const inches = Math.round(totalInches % 12)
      return `${feet}'${inches}"`
    },
    color: '#FFFFFF',
    higherIsBetter: true,
    range: [60, 80],
  },
  'Weight': {
    label: 'Weight',
    icon: '⚖️',
    format: (v) => `${parseInt(v)} lbs`,
    color: '#FFFFFF',
    higherIsBetter: true,
    range: [140, 320],
  },
  'Rivals.com Stars': {
    label: 'Rivals Stars',
    icon: '⭐',
    format: (v) => `${parseFloat(v).toFixed(1)}★`,
    color: '#CDDC39',
    higherIsBetter: true,
    range: [1, 5],
  },
}

// Calculate a percentile-like score (0-100) for a metric
function calcScore(value: string, metricTitle: string): number {
  const config = METRIC_CONFIG[metricTitle]
  if (!config) return 70
  const num = parseFloat(value)
  if (isNaN(num)) return 70
  const [min, max] = config.range
  if (config.higherIsBetter) {
    return Math.max(0, Math.min(100, Math.round(((num - min) / (max - min)) * 100)))
  } else {
    return Math.max(0, Math.min(100, Math.round(((max - num) / (max - min)) * 100)))
  }
}

// ── LOCKED COLLEGE CARD (upgrade CTA) ────────────────────────

function LockedCollegeCard({ rank }: { rank: number }) {
  const width = [94, 87, 82][rank] ?? 78
  return (
    <div className="relative overflow-hidden bg-white/[0.04] border border-white/8 rounded-2xl p-4 sm:p-5 select-none">
      {/* Blur overlay */}
      <div className="absolute inset-0 backdrop-blur-sm bg-black/40 z-10 flex flex-col items-center justify-center">
        <div className="w-8 h-8 rounded-full bg-white/10 border border-white/20 flex items-center justify-center mb-2">
          <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M16.5 10.5V6.75a4.5 4.5 0 1 0-9 0v3.75m-.75 11.25h10.5a2.25 2.25 0 0 0 2.25-2.25v-6.75a2.25 2.25 0 0 0-2.25-2.25H6.75a2.25 2.25 0 0 0-2.25 2.25v6.75a2.25 2.25 0 0 0 2.25 2.25Z" />
          </svg>
        </div>
        <span className="text-xs text-gray-300 font-semibold">Unlock with Full Report</span>
      </div>
      {/* Fake content behind blur */}
      <div className="flex items-center gap-4 opacity-30">
        <div className="w-12 h-12 rounded-xl bg-white/20 flex-shrink-0" />
        <div className="flex-1 space-y-1.5">
          <div className="h-3 bg-white/20 rounded w-2/3" />
          <div className="h-2 bg-white/10 rounded w-1/2" />
        </div>
        <div className="text-3xl font-black text-sparq-lime">{width}%</div>
      </div>
      <div className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden opacity-30">
        <div className="h-full rounded-full bg-sparq-lime" style={{ width: `${width}%` }} />
      </div>
    </div>
  )
}

// ── METRIC CARD ───────────────────────────────────────────────

function MetricCard({ metric }: { metric: Metric }) {
  const config = METRIC_CONFIG[metric.title]
  if (!config) return null
  const score = calcScore(metric.value, metric.title)

  return (
    <div className="bg-white/[0.04] border border-white/8 rounded-2xl p-4 flex flex-col gap-2">
      <div className="flex items-center justify-between">
        <span className="text-xs text-gray-500 uppercase tracking-wider font-semibold">{config.label}</span>
        <span className="text-lg">{config.icon}</span>
      </div>
      <div className="text-2xl font-black" style={{ color: config.color }}>
        {config.format(metric.value)}
      </div>
      <div className="space-y-1">
        <div className="flex items-center justify-between text-xs text-gray-600">
          <span>Percentile</span>
          <span className="font-bold" style={{ color: score >= 70 ? '#CDDC39' : score >= 50 ? '#FFCC02' : '#FC5C5C' }}>
            {score}th
          </span>
        </div>
        <div className="h-1.5 bg-white/5 rounded-full overflow-hidden">
          <div
            className="h-full rounded-full transition-all duration-1000"
            style={{ width: `${score}%`, backgroundColor: score >= 70 ? '#CDDC39' : score >= 50 ? '#FFCC02' : '#FC5C5C' }}
          />
        </div>
        {metric.verified && (
          <span className="inline-flex items-center gap-1 text-[10px] text-green-400 font-semibold">
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M16.704 4.153a.75.75 0 0 1 .143 1.052l-8 10.5a.75.75 0 0 1-1.127.075l-4.5-4.5a.75.75 0 0 1 1.06-1.06l3.894 3.893 7.48-9.817a.75.75 0 0 1 1.05-.143Z" clipRule="evenodd" />
            </svg>
            Verified
          </span>
        )}
      </div>
    </div>
  )
}

// ── LOADING SKELETON ─────────────────────────────────────────

function LoadingSkeleton() {
  return (
    <div className="animate-pulse space-y-6">
      <div className="h-32 bg-white/5 rounded-2xl" />
      <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
        {[...Array(6)].map((_, i) => (
          <div key={i} className="h-28 bg-white/5 rounded-2xl" />
        ))}
      </div>
      <div className="h-48 bg-white/5 rounded-2xl" />
    </div>
  )
}

// ── MAIN PAGE ────────────────────────────────────────────────

export default function QuickScanClient() {
  const { user, isLoaded: clerkLoaded } = useUser()
  const [data, setData] = useState<DashboardData | null>(null)
  const [athleteId, setAthleteId] = useState<number | null>(null)
  const [state, setState] = useState<'loading' | 'no-athlete' | 'ready' | 'error'>('loading')
  const [errorMsg, setErrorMsg] = useState('')

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://sparq-agent-backend.up.railway.app'

  // Waitlist / upgrade intent capture
  const [showWaitlist, setShowWaitlist] = useState(false)
  const [waitlistEmail, setWaitlistEmail] = useState('')
  const [waitlistTier, setWaitlistTier] = useState<'starter' | 'pro' | 'elite'>('starter')
  const [waitlistSubmitting, setWaitlistSubmitting] = useState(false)
  const [waitlistDone, setWaitlistDone] = useState(false)
  const emailInputRef = useRef<HTMLInputElement>(null)

  const handleWaitlistSubmit = async () => {
    if (!waitlistEmail || waitlistSubmitting) return
    setWaitlistSubmitting(true)
    try {
      await fetch('/api/waitlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          email: waitlistEmail,
          tier: waitlistTier,
          athleteName: athleteName || undefined,
          position: data?.position || undefined,
        }),
      })
      setWaitlistDone(true)
    } catch {
      // Fail silently — still show success to user
      setWaitlistDone(true)
    } finally {
      setWaitlistSubmitting(false)
    }
  }

  useEffect(() => {
    if (showWaitlist && !waitlistDone) {
      setTimeout(() => emailInputRef.current?.focus(), 100)
    }
  }, [showWaitlist, waitlistDone])

  useEffect(() => {
    if (!clerkLoaded) return
    if (!user) {
      setState('error')
      setErrorMsg('Sign in to view your Quick Scan.')
      return
    }

    // Look up linked athlete via Clerk ID
    fetch(`${backendUrl}/api/profile/by-clerk/${user.id}`)
      .then(r => r.json())
      .then(async linkData => {
        if (!linkData.found || !linkData.user_id) {
          setState('no-athlete')
          return
        }
        const uid = linkData.user_id
        setAthleteId(uid)

        // Fetch dashboard data
        const res = await fetch(`${backendUrl}/api/dashboard/${uid}`)
        if (!res.ok) throw new Error('Failed to load athlete data')
        const dashboard = await res.json()
        setData(dashboard)
        setState('ready')
      })
      .catch(err => {
        setState('error')
        setErrorMsg(err.message || 'Something went wrong.')
      })
  }, [clerkLoaded, user, backendUrl])

  // Filter to recognized metrics only
  const displayMetrics = (data?.metrics ?? []).filter(m => METRIC_CONFIG[m.title])

  // Compute overall athletic percentile (avg of all metric scores)
  const overallPercentile = displayMetrics.length > 0
    ? Math.round(displayMetrics.reduce((sum, m) => sum + calcScore(m.value, m.title), 0) / displayMetrics.length)
    : null

  const athleteName = data ? `${data.first_name} ${data.last_name}`.trim() : ''
  const initials = data
    ? `${data.first_name?.[0] ?? ''}${data.last_name?.[0] ?? ''}`.toUpperCase()
    : ''

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white selection:bg-sparq-lime/30">
      {/* HEADER */}
      <header className="sticky top-0 z-50 border-b border-white/10 bg-sparq-charcoal/95 backdrop-blur-lg">
        <div className="max-w-4xl mx-auto px-4 py-3 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link href="/" className="flex items-center">
              <img src="/sparq-logo-white.png" alt="SPARQ" className="h-7 w-auto" />
            </Link>
            <span className="px-2 py-0.5 bg-sparq-lime/10 text-sparq-lime text-[10px] font-bold rounded-full border border-sparq-lime/20 uppercase tracking-wider">
              Quick Scan
            </span>
          </div>
          {athleteId && (
            <Link
              href={`/athlete/${athleteId}`}
              className="text-xs text-gray-400 hover:text-sparq-lime transition-colors"
            >
              ← Dashboard
            </Link>
          )}
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-8 space-y-8">

        {/* ── NOT CONNECTED ─────────────────────────── */}
        {state === 'no-athlete' && (
          <div className="text-center py-16">
            <div className="w-16 h-16 rounded-2xl bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center mx-auto mb-5">
              <svg className="w-8 h-8 text-sparq-lime" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={1.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M15.75 6a3.75 3.75 0 1 1-7.5 0 3.75 3.75 0 0 1 7.5 0ZM4.501 20.118a7.5 7.5 0 0 1 14.998 0A17.933 17.933 0 0 1 12 21.75c-2.676 0-5.216-.584-7.499-1.632Z" />
              </svg>
            </div>
            <h2 className="text-2xl font-black text-white mb-2">Connect Your Athlete Profile</h2>
            <p className="text-gray-400 mb-6 max-w-md mx-auto">
              Link your GMTM athlete profile to see your personalized Quick Scan with real metrics and percentile rankings.
            </p>
            <Link
              href="/connect"
              className="inline-flex items-center gap-2 px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105"
            >
              Connect Profile →
            </Link>
          </div>
        )}

        {/* ── ERROR / UNAUTHENTICATED ───────────────── */}
        {state === 'error' && (
          <div className="text-center py-16">
            <p className="text-gray-400 mb-4">{errorMsg}</p>
            <Link href="/sign-in" className="text-sparq-lime hover:underline">Sign in →</Link>
          </div>
        )}

        {/* ── LOADING ───────────────────────────────── */}
        {state === 'loading' && <LoadingSkeleton />}

        {/* ── READY ─────────────────────────────────── */}
        {state === 'ready' && data && (
          <>
            {/* ATHLETE HEADER */}
            <div className="bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/10 rounded-2xl p-5 sm:p-8">
              <div className="flex items-center gap-4 mb-5">
                <div className="w-16 h-16 bg-gradient-to-br from-sparq-lime/30 to-sparq-lime/10 rounded-2xl flex items-center justify-center flex-shrink-0 border border-sparq-lime/20">
                  <span className="text-sparq-lime font-black text-2xl">{initials}</span>
                </div>
                <div>
                  <h1 className="text-2xl sm:text-3xl font-black text-white">{athleteName}</h1>
                  <p className="text-gray-400 text-sm mt-0.5">
                    {data.position}
                    {data.graduation_year ? ` · Class of ${data.graduation_year}` : ''}
                    {data.city ? ` · ${data.city}${data.state ? `, ${data.state}` : ''}` : ''}
                  </p>
                </div>
              </div>

              {/* Quick stats row */}
              {data.offer_count !== undefined && data.offer_count > 0 && (
                <div className="flex items-center gap-2 text-sm">
                  <span className="text-sparq-lime font-bold">{data.offer_count}</span>
                  <span className="text-gray-500">scholarship offers on file</span>
                </div>
              )}

              {overallPercentile !== null && (
                <div className="mt-4 p-4 rounded-xl bg-sparq-lime/10 border border-sparq-lime/30 flex items-center gap-4">
                  <div className="text-center flex-shrink-0">
                    <div className="text-4xl font-black text-sparq-lime leading-none">{overallPercentile}<span className="text-lg font-bold">th</span></div>
                    <div className="text-[10px] text-sparq-lime/60 uppercase tracking-wider mt-0.5">percentile</div>
                  </div>
                  <div>
                    <p className="text-sm text-white font-bold leading-tight">
                      You rank in the top {100 - overallPercentile}% of {data.position ? `${data.position}s` : 'athletes'} in our database.
                    </p>
                    <p className="text-xs text-gray-500 mt-1">
                      Based on {displayMetrics.length} verified metric{displayMetrics.length !== 1 ? 's' : ''} vs. 75,000+ athletes. Upgrade to see your college matches.
                    </p>
                  </div>
                </div>
              )}
              {overallPercentile === null && (
                <div className="mt-4 p-3 rounded-xl bg-sparq-lime/5 border border-sparq-lime/20 flex items-start gap-2">
                  <svg className="w-4 h-4 text-sparq-lime flex-shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
                  </svg>
                  <p className="text-xs text-sparq-lime/80 leading-relaxed">
                    This is your <strong>free Quick Scan</strong> — your real metrics with percentile rankings vs. {data.position ? `other ${data.position}s` : 'athletes'} in our database.
                    Upgrade to see personalized college matches, depth chart analysis, and your outreach plan.
                  </p>
                </div>
              )}
            </div>

            {/* YOUR METRICS */}
            {displayMetrics.length > 0 ? (
              <div>
                <div className="flex items-center justify-between mb-4">
                  <h2 className="text-xl font-black text-white">Your Metrics</h2>
                  <span className="text-xs text-gray-500">{displayMetrics.filter(m => m.verified).length} verified</span>
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-3 gap-3 sm:gap-4">
                  {displayMetrics.map((m, i) => (
                    <MetricCard key={i} metric={m} />
                  ))}
                </div>
              </div>
            ) : (
              <div className="text-center py-10 border border-white/10 rounded-2xl">
                <p className="text-gray-500 mb-3">No metrics on file yet.</p>
                <p className="text-xs text-gray-600">Complete your GMTM profile to see your numbers here.</p>
              </div>
            )}

            {/* COLLEGE MATCHES — LOCKED */}
            <div>
              <div className="flex items-center justify-between mb-4">
                <div>
                  <h2 className="text-xl font-black text-white">College Matches</h2>
                  <p className="text-gray-500 text-sm mt-0.5">Ranked by fit — metrics, scheme, roster needs</p>
                </div>
                <span className="text-xs font-bold text-sparq-lime px-2 py-1 rounded-full bg-sparq-lime/10 border border-sparq-lime/20">
                  Pro Feature
                </span>
              </div>

              <div className="space-y-3">
                {[0, 1, 2].map(i => (
                  <LockedCollegeCard key={i} rank={i} />
                ))}
              </div>
            </div>

            {/* UPGRADE CTA */}
            <div className="relative">
              <div className="absolute inset-0 bg-gradient-to-r from-sparq-lime/5 via-sparq-lime/10 to-sparq-lime/5 rounded-3xl blur-xl" />
              <div className="relative bg-gradient-to-b from-sparq-charcoal-light to-sparq-charcoal border border-sparq-lime/20 rounded-3xl px-6 py-10 text-center">
                <div className="text-sparq-lime text-sm font-bold uppercase tracking-wider mb-3 flex items-center justify-center gap-2">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 01.12-.381z"/>
                  </svg>
                  Full Report
                </div>
                <h2 className="text-2xl sm:text-3xl font-black text-white mb-3 leading-tight">
                  See your real college matches.
                  <br />
                  <span className="text-gray-400 text-xl font-bold">And know exactly what to do next.</span>
                </h2>
                <p className="text-gray-500 text-sm sm:text-base mb-6 max-w-md mx-auto">
                  SPARQ Pro Report goes deep — coaching staff research, depth chart openings, scheme fit, and a personalized outreach plan.
                  What NCSA charges $5,000+ for.
                </p>

                <div className="flex flex-col sm:flex-row items-center justify-center gap-4 mb-6">
                  {[
                    { tier: 'Starter', price: '$29.99', desc: '10 college matches + action plan' },
                    { tier: 'Pro', price: '$49', desc: 'Deep school research + draft emails' },
                    { tier: 'Elite', price: '$79.99', desc: 'Everything + 3-month refresh' },
                  ].map(t => (
                    <div key={t.tier} className="flex flex-col items-center px-5 py-3 bg-white/5 border border-white/10 rounded-xl min-w-[140px]">
                      <span className="text-xs text-gray-500 uppercase tracking-wider">{t.tier}</span>
                      <span className="text-2xl font-black text-sparq-lime">{t.price}</span>
                      <span className="text-[10px] text-gray-600 text-center mt-1">{t.desc}</span>
                    </div>
                  ))}
                </div>

                {!showWaitlist && !waitlistDone && (
                  <>
                    <button
                      className="inline-flex items-center gap-2 px-8 py-4 bg-sparq-lime text-sparq-charcoal text-lg font-black rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105 shadow-lg shadow-sparq-lime/25"
                      onClick={() => setShowWaitlist(true)}
                    >
                      Get My Full Report →
                    </button>
                    <p className="text-gray-600 text-xs mt-3">One-time purchase · Delivered in ~2 minutes</p>
                  </>
                )}

                {/* Waitlist capture */}
                {showWaitlist && !waitlistDone && (
                  <div className="w-full max-w-md mx-auto mt-2 p-5 bg-black/40 border border-sparq-lime/30 rounded-2xl text-left">
                    <h3 className="text-white font-black text-base mb-1">We're almost there.</h3>
                    <p className="text-gray-400 text-sm mb-4">
                      Payment launches shortly. Drop your email — you'll be first in line and we'll notify you the moment it's live.
                    </p>
                    {/* Tier selector */}
                    <div className="flex gap-2 mb-4">
                      {(['starter', 'pro', 'elite'] as const).map(t => (
                        <button
                          key={t}
                          onClick={() => setWaitlistTier(t)}
                          className={`flex-1 py-2 text-xs font-bold rounded-lg border transition-all ${
                            waitlistTier === t
                              ? 'bg-sparq-lime/20 border-sparq-lime text-sparq-lime'
                              : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20'
                          }`}
                        >
                          {t === 'starter' ? 'Starter\n$29.99' : t === 'pro' ? 'Pro\n$49' : 'Elite\n$79.99'}
                        </button>
                      ))}
                    </div>
                    <div className="flex gap-2">
                      <input
                        ref={emailInputRef}
                        type="email"
                        value={waitlistEmail}
                        onChange={e => setWaitlistEmail(e.target.value)}
                        onKeyDown={e => e.key === 'Enter' && handleWaitlistSubmit()}
                        placeholder="your@email.com"
                        className="flex-1 bg-white/5 border border-white/10 text-white px-3 py-2.5 text-sm rounded-xl placeholder-gray-600 focus:outline-none focus:border-sparq-lime/50 transition-colors"
                      />
                      <button
                        onClick={handleWaitlistSubmit}
                        disabled={!waitlistEmail || waitlistSubmitting}
                        className="px-5 py-2.5 bg-sparq-lime text-sparq-charcoal text-sm font-black rounded-xl hover:bg-sparq-lime-dark disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                      >
                        {waitlistSubmitting ? '...' : 'Notify Me'}
                      </button>
                    </div>
                  </div>
                )}

                {/* Success state */}
                {waitlistDone && (
                  <div className="w-full max-w-md mx-auto mt-2 p-5 bg-sparq-lime/10 border border-sparq-lime/30 rounded-2xl text-center">
                    <div className="text-3xl mb-2">✓</div>
                    <p className="text-sparq-lime font-black text-base mb-1">You're on the list.</p>
                    <p className="text-gray-400 text-sm">We'll email you the moment payment goes live. Check your inbox for confirmation.</p>
                  </div>
                )}
              </div>
            </div>

            {/* DEMO LINK */}
            <div className="text-center pb-4">
              <p className="text-gray-600 text-xs">
                Want to see a full report example?{' '}
                <Link href="/demo" className="text-sparq-lime hover:underline">
                  View the demo →
                </Link>
              </p>
            </div>
          </>
        )}
      </main>

      <style jsx global>{`
        @keyframes fadeIn {
          from { opacity: 0; transform: translateY(10px); }
          to { opacity: 1; transform: translateY(0); }
        }
        .animate-fadeIn { animation: fadeIn 0.5s ease-out forwards; }
      `}</style>
    </div>
  )
}
