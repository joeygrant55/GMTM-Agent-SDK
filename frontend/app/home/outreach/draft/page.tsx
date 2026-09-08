'use client'

import { apiFetch } from '@/app/_lib/api'
import { ProfileConnectionError, readProfileConnectionResponse } from '@/app/_lib/profileConnection'

import dynamic from 'next/dynamic'

import Link from 'next/link'
import { useUser } from '@clerk/nextjs'
import { useEffect, useMemo, useRef, useState } from 'react'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

class DraftDataError extends Error {}

interface College {
  id: number
  college_name: string
  fit_reasons?: string[] | null
}

interface DraftProfile {
  name: string
  position: string
  classYear: string
  school: string
  city: string
  state: string
  hudlUrl: string
  keyAchievement: string
}

function toReadableStatName(key: string) {
  const known: Record<string, string> = {
    tackles: 'tackle',
    interceptions: 'interception',
    passBreakups: 'pass breakup',
    sacks: 'sack',
    touchdowns: 'touchdown',
  }
  if (known[key]) return known[key]
  return key
    .replace(/([a-z0-9])([A-Z])/g, '$1 $2')
    .replace(/_/g, ' ')
    .toLowerCase()
}

function buildKeyAchievement(maxprepsData: Record<string, unknown>) {
  if (!Array.isArray(maxprepsData.seasonStats)) return ''
  const latestSeason = maxprepsData.seasonStats[0]
  if (!latestSeason || typeof latestSeason !== 'object' || Array.isArray(latestSeason)) return ''

  let bestKey = ''
  let bestValue = 0
  for (const [key, value] of Object.entries(latestSeason)) {
    if (key === 'season') continue
    if (typeof value !== 'number' || !Number.isFinite(value) || value <= 0) continue
    if (value > bestValue) {
      bestValue = value
      bestKey = key
    }
  }

  if (!bestKey || bestValue <= 0) return ''
  const stat = toReadableStatName(bestKey)
  const suffix = bestValue === 1 ? '' : 's'
  return `recorded ${bestValue} ${stat}${suffix}`
}

function extractCoachLastName(fitReasons?: string[] | null) {
  if (!Array.isArray(fitReasons)) return ''
  for (const reason of fitReasons) {
    const match = reason.match(/\bcoach\s+([A-Za-z'-]+)/i)
    if (match?.[1]) return match[1]
  }
  return ''
}

function buildEmailTemplate(profile: DraftProfile, college: College | null) {
  const collegeName = college?.college_name || '[College Name]'
  const coachLastName = extractCoachLastName(college?.fit_reasons)
  const coachLine = coachLastName ? `Coach ${coachLastName},` : 'Coach,'
  const achievementLine = profile.keyAchievement
    ? `This past season I ${profile.keyAchievement}.`
    : 'This past season I continued developing my game and competing at a high level.'
  const location = [profile.city, profile.state].filter(Boolean).join(', ') || 'my area'
  const hudlLine = profile.hudlUrl ? `\n${profile.hudlUrl}` : ''

  return `Subject: ${profile.name} | ${profile.position} | Class of ${profile.classYear} | ${profile.school}

${coachLine}

My name is ${profile.name} and I am a ${profile.position} in the Class of ${profile.classYear} from ${profile.school} in ${location}.

I am very interested in ${collegeName} and believe I would be a great fit for your program. ${achievementLine}

I would love the opportunity to speak with you about my interest in ${collegeName}.${hudlLine}

Thank you for your time,
${profile.name}
`
}

function DraftCoachEmailPage() {
  const { user, isLoaded } = useUser()
  if (!isLoaded || !user?.id) {
    return <p role="status" className="p-8 text-gray-300">{isLoaded ? 'Sign in to draft outreach emails.' : 'Loading your account…'}</p>
  }
  return <DraftCoachEmailSession key={user.id} user={user} />
}

function DraftCoachEmailSession({ user }: { user: { id: string; firstName?: string | null; lastName?: string | null } }) {
  const [loading, setLoading] = useState(true)
  const [profileReady, setProfileReady] = useState(false)
  const [loadAttempt, setLoadAttempt] = useState(0)
  const [error, setError] = useState('')
  const [colleges, setColleges] = useState<College[]>([])
  const [selectedCollegeId, setSelectedCollegeId] = useState<number | null>(null)
  const [profile, setProfile] = useState<DraftProfile>({
    name: '',
    position: '',
    classYear: '',
    school: '',
    city: '',
    state: '',
    hudlUrl: '',
    keyAchievement: '',
  })
  const [emailDraft, setEmailDraft] = useState('')
  const [copying, setCopying] = useState(false)
  const [toast, setToast] = useState('')
  const lifetimeRef = useRef<AbortController | null>(null)
  const toastTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const selectedCollege = useMemo(
    () => colleges.find((college) => college.id === selectedCollegeId) || null,
    [colleges, selectedCollegeId]
  )

  useEffect(() => {
    const controller = new AbortController()
    lifetimeRef.current = controller
    const signal = controller.signal
    const loadData = async () => {
      setLoading(true)
      setProfileReady(false)
      setError('')

      try {
        const profileRes = await apiFetch(`${backendUrl}/api/profile/by-clerk/${user.id}`, { signal })
        const profileData = await readProfileConnectionResponse(profileRes)
        if (signal.aborted) return
        if (!profileData.has_sparq_profile) {
          throw new DraftDataError('Complete onboarding first to draft outreach emails.')
        }

        const [workspaceRes, collegesRes] = await Promise.all([
          apiFetch(`${backendUrl}/api/workspace/profile/${user.id}`, { signal }),
          apiFetch(`${backendUrl}/api/workspace/colleges/${user.id}`, { signal }),
        ])
        if (!workspaceRes.ok) throw new DraftDataError('We could not load your athlete information. Please try again.')
        if (!collegesRes.ok) throw new DraftDataError('We could not load your colleges. Please try again.')
        const workspaceData = await workspaceRes.json()
        if (!workspaceData || typeof workspaceData !== 'object' || Array.isArray(workspaceData)
          || workspaceData.clerk_id !== user.id) {
          throw new DraftDataError('We could not confirm the owner of this profile. Please try again.')
        }
        const collegesData = await collegesRes.json()
        const list: College[] = Array.isArray(collegesData?.colleges) ? collegesData.colleges : []

        // The old onboarding cache has no account owner. Use this caller's
        // saved workspace instead of carrying another athlete's browser data.
        const maxprepsData: Record<string, unknown> = workspaceData.maxpreps_data
          && typeof workspaceData.maxpreps_data === 'object' && !Array.isArray(workspaceData.maxpreps_data)
          ? workspaceData.maxpreps_data : {}
        const text = (value: unknown, fallback = '') => typeof value === 'string' && value.trim() ? value : fallback
        const classYear = maxprepsData.classYear ?? workspaceData.class_year

        const fullName = [user.firstName, user.lastName].filter(Boolean).join(' ').trim()
        const draftProfile: DraftProfile = {
          name: text(maxprepsData.name, text(workspaceData.name, fullName || 'Athlete')),
          position: text(maxprepsData.position, text(workspaceData.position, 'Athlete')),
          classYear: typeof classYear === 'number' && Number.isFinite(classYear) ? String(classYear) : text(classYear, 'Unknown'),
          school: text(maxprepsData.school, text(workspaceData.school, 'My High School')),
          city: text(maxprepsData.city, text(workspaceData.city)),
          state: text(maxprepsData.state, text(workspaceData.state)),
          hudlUrl: text(workspaceData.hudl_url),
          keyAchievement: buildKeyAchievement(maxprepsData),
        }

        if (!signal.aborted) {
          setProfile(draftProfile)
          setColleges(list)
          setSelectedCollegeId(list[0]?.id ?? null)
          setProfileReady(true)
        }
      } catch (err) {
        if (!signal.aborted) {
          setError(err instanceof ProfileConnectionError || err instanceof DraftDataError
            ? err.message : 'We could not load your draft information. Please try again.')
        }
      } finally {
        if (!signal.aborted) setLoading(false)
      }
    }

    loadData()
    return () => {
      controller.abort()
      if (toastTimerRef.current) clearTimeout(toastTimerRef.current)
    }
  }, [backendUrl, user.firstName, user.id, user.lastName, loadAttempt])

  useEffect(() => {
    setEmailDraft(buildEmailTemplate(profile, selectedCollege))
  }, [profile, selectedCollege])

  const copyEmail = async () => {
    const signal = lifetimeRef.current?.signal
    if (!profileReady || signal?.aborted || !selectedCollege || !emailDraft.trim()) return

    setCopying(true)
    setError('')

    try {
      await navigator.clipboard.writeText(emailDraft)
      if (signal?.aborted) return
      const outreachRes = await apiFetch(`${backendUrl}/api/workspace/outreach/${user.id}`, {
        method: 'POST',
        signal,
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          school: selectedCollege.college_name,
          method: 'Email',
          contact_date: new Date().toISOString().slice(0, 10),
          status: 'Awaiting Response',
          notes: 'Drafted via SPARQ',
        }),
      })
      if (signal?.aborted) return
      if (!outreachRes.ok) {
        throw new Error('Failed to log outreach')
      }
      setToast('Copied! Logged to your outreach tracker.')
      toastTimerRef.current = setTimeout(() => setToast(''), 2500)
    } catch {
      if (!signal?.aborted) setError('Email copied failed or outreach log failed. Please try again.')
    } finally {
      if (!signal?.aborted) setCopying(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  if (!profileReady) {
    return (
      <div className="p-8 text-white">
        <h1 className="text-3xl font-black">Draft Coach Emails</h1>
        <p role="alert" className="mt-4 text-amber-200">{error}</p>
        <button type="button" onClick={() => setLoadAttempt(value => value + 1)} className="mt-5 min-h-11 rounded-lg bg-sparq-lime px-4 font-bold text-sparq-charcoal">Retry profile check</button>
        <Link href="/home/outreach" className="mt-3 block py-3 text-sparq-lime underline">Back to Outreach</Link>
      </div>
    )
  }

  return (
    <div className="text-white pb-8 px-8">
      <div className="pt-8 pb-4">
        <Link href="/home/outreach" className="text-sm text-gray-400 hover:text-sparq-lime">
          ← Back to Outreach
        </Link>
        <h1 className="text-3xl font-black text-white mt-3">Draft Coach Emails</h1>
        <p className="text-gray-400 mt-1">Generate and personalize your outreach email in one click.</p>
      </div>

      {error && (
        <div className="mb-4 rounded-xl border border-red-400/30 bg-red-400/10 text-red-300 px-4 py-3 text-sm">
          {error}
        </div>
      )}

      <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5">
        <label htmlFor="college-select" className="block text-sm text-gray-300 mb-2">
          Select a college
        </label>
        <select
          id="college-select"
          value={selectedCollegeId ?? ''}
          onChange={(event) => {
            const nextValue = event.target.value
            setSelectedCollegeId(nextValue ? Number(nextValue) : null)
          }}
          className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white focus:border-sparq-lime focus:outline-none"
        >
          {colleges.length === 0 && <option value="">No matches available</option>}
          {colleges.map((college) => (
            <option key={college.id} value={college.id}>
              {college.college_name}
            </option>
          ))}
        </select>

        <label htmlFor="email-draft" className="block text-sm text-gray-300 mt-5 mb-2">
          Email draft
        </label>
        <textarea
          id="email-draft"
          value={emailDraft}
          onChange={(event) => setEmailDraft(event.target.value)}
          rows={16}
          className="w-full rounded-xl border border-white/10 bg-black/30 px-4 py-3 text-white focus:border-sparq-lime focus:outline-none"
        />

        <button
          type="button"
          onClick={copyEmail}
          disabled={copying || !selectedCollege || !emailDraft.trim()}
          className="mt-4 px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-xl hover:bg-sparq-lime-dark disabled:opacity-60"
        >
          {copying ? 'Copying...' : 'Copy Email'}
        </button>
      </div>

      {toast && (
        <div className="fixed bottom-6 right-6 bg-sparq-lime text-sparq-charcoal px-4 py-3 rounded-xl font-semibold shadow-lg">
          {toast}
        </div>
      )}
    </div>
  )
}


export default dynamic(() => Promise.resolve(DraftCoachEmailPage), { ssr: false })
