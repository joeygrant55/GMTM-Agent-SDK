'use client'

import Link from 'next/link'
import { useUser } from '@clerk/nextjs'
import { useEffect, useMemo, useState } from 'react'
import { MaxPrepsAthlete, ONBOARDING_MAXPREPS_KEY } from '@/app/onboarding/_lib/types'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

interface College {
  id: number
  college_name: string
  fit_reasons?: string[] | null
}

interface ProfileByClerkResponse {
  found?: boolean
  user_id?: number | null
  has_sparq_profile?: boolean
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

function buildKeyAchievement(maxprepsData: MaxPrepsAthlete | null) {
  if (!maxprepsData?.seasonStats?.length) return ''
  const latestSeason = maxprepsData.seasonStats[0]
  if (!latestSeason) return ''

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

export default function DraftCoachEmailPage() {
  const { user, isLoaded } = useUser()
  const [loading, setLoading] = useState(true)
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

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const selectedCollege = useMemo(
    () => colleges.find((college) => college.id === selectedCollegeId) || null,
    [colleges, selectedCollegeId]
  )

  useEffect(() => {
    if (!isLoaded || !user?.id) return

    let cancelled = false
    const loadData = async () => {
      setLoading(true)
      setError('')

      try {
        const [profileRes, collegesRes] = await Promise.all([
          fetch(`${backendUrl}/api/profile/by-clerk/${user.id}`),
          fetch(`${backendUrl}/api/workspace/colleges/${user.id}`),
        ])

        const profileData = (await profileRes.json()) as ProfileByClerkResponse
        if (!profileData?.has_sparq_profile) {
          throw new Error('Complete onboarding first to draft outreach emails.')
        }

        const collegesData = await collegesRes.json()
        const list: College[] = Array.isArray(collegesData?.colleges) ? collegesData.colleges : []

        let maxprepsData: MaxPrepsAthlete | null = null
        const maxprepsRaw = sessionStorage.getItem(ONBOARDING_MAXPREPS_KEY)
        if (maxprepsRaw) {
          try {
            maxprepsData = JSON.parse(maxprepsRaw) as MaxPrepsAthlete
          } catch {
            maxprepsData = null
          }
        }

        const fullName = [user.firstName, user.lastName].filter(Boolean).join(' ').trim()
        const draftProfile: DraftProfile = {
          name: maxprepsData?.name || fullName || 'Athlete',
          position: maxprepsData?.position || 'Athlete',
          classYear: String(maxprepsData?.classYear || 'Unknown'),
          school: maxprepsData?.school || 'My High School',
          city: maxprepsData?.city || '',
          state: maxprepsData?.state || '',
          hudlUrl: '',
          keyAchievement: buildKeyAchievement(maxprepsData),
        }

        if (!cancelled) {
          setProfile(draftProfile)
          setColleges(list)
          setSelectedCollegeId(list[0]?.id ?? null)
        }
      } catch (err) {
        if (!cancelled) {
          setError(err instanceof Error ? err.message : 'Failed to load draft data.')
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    loadData()
    return () => {
      cancelled = true
    }
  }, [backendUrl, isLoaded, user?.firstName, user?.id, user?.lastName])

  useEffect(() => {
    setEmailDraft(buildEmailTemplate(profile, selectedCollege))
  }, [profile, selectedCollege])

  const copyEmail = async () => {
    if (!user?.id || !selectedCollege || !emailDraft.trim()) return

    setCopying(true)
    setError('')

    try {
      await navigator.clipboard.writeText(emailDraft)
      const outreachRes = await fetch(`${backendUrl}/api/workspace/outreach/${user.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          school: selectedCollege.college_name,
          method: 'Email',
          contact_date: new Date().toISOString().slice(0, 10),
          status: 'Awaiting Response',
          notes: 'Drafted via SPARQ',
        }),
      })
      if (!outreachRes.ok) {
        throw new Error('Failed to log outreach')
      }
      setToast('Copied! Logged to your outreach tracker.')
      setTimeout(() => setToast(''), 2500)
    } catch {
      setError('Email copied failed or outreach log failed. Please try again.')
    } finally {
      setCopying(false)
    }
  }

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
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
