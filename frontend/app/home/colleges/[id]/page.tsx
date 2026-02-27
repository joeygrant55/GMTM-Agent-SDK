'use client'

import { useEffect, useState, useCallback } from 'react'
import { useUser } from '@clerk/nextjs'
import { useParams, useRouter } from 'next/navigation'
import Link from 'next/link'

const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'

type ResearchData = {
  coaching_staff?: {
    head_coach?: { name?: string; years_at_school?: string; bio?: string; recruiting_style?: string }
    position_coach?: { name?: string; role?: string; background?: string }
    contact_email?: string
    staff_note?: string
  }
  roster_fit?: {
    players_at_position?: string
    graduating_seniors?: string
    depth_chart_opportunity?: string
    typical_commit_profile?: string
    roster_note?: string
  }
  academic_fit?: {
    major_available?: boolean
    major_name?: string
    academic_profile?: string
    campus_size?: string
    academic_support?: string
    academic_note?: string
  }
  recruiting_path?: {
    next_step?: string
    camp_opportunity?: string
    contact_window?: string
    timeline?: string
    outreach_tip?: string
  }
  overall_assessment?: string
}

type CollegeDetail = {
  id: number
  college_name: string
  college_city: string
  college_state: string
  division: string
  fit_score: number
  fit_reasons?: string[]
  status: string
  deep_research_status?: string
  research_data?: ResearchData
  position?: string
  major_area?: string
}

function ScoreRing({ score }: { score: number }) {
  const color = score >= 85 ? '#C8F542' : score >= 75 ? '#facc15' : '#94a3b8'
  return (
    <div className="relative w-20 h-20 flex-shrink-0">
      <svg className="w-20 h-20 -rotate-90" viewBox="0 0 80 80">
        <circle cx="40" cy="40" r="34" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="6" />
        <circle cx="40" cy="40" r="34" fill="none" stroke={color} strokeWidth="6"
          strokeDasharray={`${2 * Math.PI * 34}`}
          strokeDashoffset={`${2 * Math.PI * 34 * (1 - score / 100)}`}
          strokeLinecap="round" />
      </svg>
      <div className="absolute inset-0 flex items-center justify-center">
        <span className="text-xl font-black text-white">{score}</span>
      </div>
    </div>
  )
}

function Section({ title, icon, children }: { title: string; icon: string; children: React.ReactNode }) {
  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6 space-y-4">
      <h2 className="text-lg font-black text-white flex items-center gap-2">
        <span>{icon}</span> {title}
      </h2>
      {children}
    </div>
  )
}

function InfoRow({ label, value }: { label: string; value?: string | boolean | null }) {
  if (value === undefined || value === null || value === '') return null
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide">{label}</p>
      <p className="text-sm text-gray-200 mt-0.5">{typeof value === 'boolean' ? (value ? 'Yes' : 'No') : value}</p>
    </div>
  )
}

const DEPTH_COLORS: Record<string, string> = {
  'immediate starter': 'text-sparq-lime',
  'compete for playing time': 'text-yellow-400',
  'developmental': 'text-blue-400',
}

export default function CollegeDetailPage() {
  const { user } = useUser()
  const params = useParams()
  const router = useRouter()
  const collegeId = params?.id as string

  const [data, setData] = useState<CollegeDetail | null>(null)
  const [loading, setLoading] = useState(true)
  const [researching, setResearching] = useState(false)
  const [error, setError] = useState('')

  const load = useCallback(async () => {
    if (!user?.id || !collegeId) return
    try {
      const res = await fetch(`${backendUrl}/api/workspace/colleges/${user.id}/${collegeId}`)
      if (!res.ok) throw new Error()
      const d = await res.json()
      setData(d)
      // If still researching, poll
      if (d.deep_research_status === 'researching') {
        setTimeout(load, 5000)
      } else {
        setResearching(false)
      }
    } catch {
      setError('Could not load college data')
    } finally {
      setLoading(false)
    }
  }, [user?.id, collegeId])

  useEffect(() => { load() }, [load])

  const startResearch = async () => {
    if (!user?.id || !collegeId) return
    setResearching(true)
    try {
      await fetch(`${backendUrl}/api/workspace/colleges/${user.id}/${collegeId}/research`, { method: 'POST' })
      setTimeout(load, 3000)
    } catch {
      setResearching(false)
    }
  }

  if (loading) return (
    <div className="flex items-center justify-center h-64">
      <div className="w-6 h-6 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
    </div>
  )
  if (error || !data) return (
    <div className="p-8 text-center text-gray-400">{error || 'College not found'}</div>
  )

  const rd = data.research_data
  const isResearching = data.deep_research_status === 'researching' || researching
  const hasResearch = !!rd

  return (
    <div className="max-w-2xl mx-auto px-4 py-8 space-y-5">
      {/* Back */}
      <Link href="/home/colleges" className="text-sm text-gray-500 hover:text-sparq-lime flex items-center gap-1 transition-colors">
        ← Back to College Fits
      </Link>

      {/* Header */}
      <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
        <div className="flex items-center gap-5">
          <ScoreRing score={data.fit_score} />
          <div className="flex-1 min-w-0">
            <h1 className="text-2xl font-black text-white leading-tight">{data.college_name}</h1>
            <p className="text-gray-400 mt-0.5">{[data.college_city, data.college_state].filter(Boolean).join(', ')} · {data.division}</p>
            <div className="flex items-center gap-2 mt-2">
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold border ${
                data.status === 'Offered' ? 'text-sparq-lime border-sparq-lime/30 bg-sparq-lime/10' :
                data.status === 'Contacted' ? 'text-blue-400 border-blue-400/30 bg-blue-400/10' :
                'text-gray-400 border-white/10 bg-white/5'
              }`}>{data.status}</span>
              {data.fit_score >= 85 && <span className="text-xs text-sparq-lime font-semibold">Strong Fit</span>}
            </div>
          </div>
        </div>

        {/* Initial fit summary */}
        {data.fit_reasons && data.fit_reasons.length > 0 && (
          <div className="mt-4 pt-4 border-t border-white/10">
            <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Initial Fit Analysis</p>
            <ul className="space-y-1.5">
              {data.fit_reasons.filter(r => r && r.length > 5).map((r, i) => (
                <li key={i} className="flex gap-2 text-sm text-gray-300">
                  <span className="text-sparq-lime flex-shrink-0 mt-0.5">›</span> {r}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      {/* Deep Research CTA or status */}
      {!hasResearch && (
        <div className={`border rounded-2xl p-6 text-center ${isResearching ? 'border-sparq-lime/30 bg-sparq-lime/5' : 'border-white/10 bg-white/[0.04]'}`}>
          {isResearching ? (
            <>
              <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin mx-auto mb-3" />
              <p className="text-white font-bold">Researching {data.college_name}...</p>
              <p className="text-gray-400 text-sm mt-1">Analyzing coaching staff, roster, academics, and recruiting path. Takes ~30 seconds.</p>
            </>
          ) : (
            <>
              <p className="text-white font-black text-lg mb-1">Run Deep Research</p>
              <p className="text-gray-400 text-sm mb-4">Get a full breakdown of coaching staff, roster fit, academics, and your recruiting path at {data.college_name}.</p>
              <button onClick={startResearch}
                className="bg-sparq-lime text-sparq-charcoal font-black px-6 py-3 rounded-xl hover:bg-yellow-300 transition-colors">
                Research This School →
              </button>
            </>
          )}
        </div>
      )}

      {/* Coaching Staff */}
      {hasResearch && rd?.coaching_staff && (
        <Section title="Coaching Staff" icon="🏀">
          {rd.coaching_staff.head_coach?.name && (
            <div className="bg-black/20 rounded-xl p-4 space-y-2">
              <div className="flex items-center justify-between">
                <p className="font-bold text-white">{rd.coaching_staff.head_coach.name}</p>
                <span className="text-xs text-gray-500">Head Coach {rd.coaching_staff.head_coach.years_at_school ? `· ${rd.coaching_staff.head_coach.years_at_school}` : ''}</span>
              </div>
              {rd.coaching_staff.head_coach.bio && <p className="text-sm text-gray-400">{rd.coaching_staff.head_coach.bio}</p>}
              {rd.coaching_staff.head_coach.recruiting_style && (
                <div className="mt-2 pt-2 border-t border-white/5">
                  <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-1">Recruiting Style</p>
                  <p className="text-sm text-gray-300">{rd.coaching_staff.head_coach.recruiting_style}</p>
                </div>
              )}
            </div>
          )}
          {rd.coaching_staff.position_coach?.name && (
            <div className="bg-black/20 rounded-xl p-4 space-y-1">
              <div className="flex items-center justify-between">
                <p className="font-bold text-white">{rd.coaching_staff.position_coach.name}</p>
                <span className="text-xs text-gray-500">{rd.coaching_staff.position_coach.role}</span>
              </div>
              {rd.coaching_staff.position_coach.background && <p className="text-sm text-gray-400">{rd.coaching_staff.position_coach.background}</p>}
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <InfoRow label="Contact Email" value={rd.coaching_staff.contact_email} />
            <InfoRow label="Staff Notes" value={rd.coaching_staff.staff_note} />
          </div>
        </Section>
      )}

      {/* Roster Fit */}
      {hasResearch && rd?.roster_fit && (
        <Section title="Roster Fit" icon="📋">
          <div className="grid grid-cols-2 gap-4">
            <div className="bg-black/20 rounded-xl p-4 text-center">
              <p className="text-2xl font-black text-white">{rd.roster_fit.players_at_position ?? '—'}</p>
              <p className="text-xs text-gray-500 mt-1">Players at your position</p>
            </div>
            <div className="bg-black/20 rounded-xl p-4 text-center">
              <p className="text-2xl font-black text-sparq-lime">{rd.roster_fit.graduating_seniors ?? '—'}</p>
              <p className="text-xs text-gray-500 mt-1">Graduating seniors</p>
            </div>
          </div>
          {rd.roster_fit.depth_chart_opportunity && (
            <div className="bg-black/20 rounded-xl p-4">
              <p className="text-xs text-gray-500 font-semibold uppercase tracking-wide mb-1">Opportunity Level</p>
              <p className={`text-base font-black capitalize ${DEPTH_COLORS[rd.roster_fit.depth_chart_opportunity.toLowerCase()] || 'text-white'}`}>
                {rd.roster_fit.depth_chart_opportunity}
              </p>
            </div>
          )}
          <InfoRow label="Typical Commit Profile" value={rd.roster_fit.typical_commit_profile} />
          <InfoRow label="Roster Notes" value={rd.roster_fit.roster_note} />
        </Section>
      )}

      {/* Academic Fit */}
      {hasResearch && rd?.academic_fit && (
        <Section title="Academic Fit" icon="🎓">
          {rd.academic_fit.major_name && (
            <div className={`rounded-xl p-4 flex items-center gap-3 ${rd.academic_fit.major_available ? 'bg-sparq-lime/10 border border-sparq-lime/20' : 'bg-white/5 border border-white/10'}`}>
              <span className="text-2xl">{rd.academic_fit.major_available ? '✅' : '⚠️'}</span>
              <div>
                <p className="text-white font-bold">{rd.academic_fit.major_name}</p>
                <p className="text-xs text-gray-400">{rd.academic_fit.major_available ? 'Program available' : 'Not offered — check alternatives'}</p>
              </div>
            </div>
          )}
          <div className="grid grid-cols-2 gap-3">
            <InfoRow label="Academic Profile" value={rd.academic_fit.academic_profile} />
            <InfoRow label="Campus Size" value={rd.academic_fit.campus_size} />
          </div>
          <InfoRow label="Academic Support" value={rd.academic_fit.academic_support} />
          <InfoRow label="Academic Notes" value={rd.academic_fit.academic_note} />
        </Section>
      )}

      {/* Recruiting Path */}
      {hasResearch && rd?.recruiting_path && (
        <Section title="Your Recruiting Path" icon="🎯">
          {rd.recruiting_path.next_step && (
            <div className="bg-sparq-lime/10 border border-sparq-lime/20 rounded-xl p-4">
              <p className="text-xs font-semibold text-sparq-lime uppercase tracking-wide mb-1">Next Step</p>
              <p className="text-white font-bold">{rd.recruiting_path.next_step}</p>
            </div>
          )}
          <div className="space-y-3">
            <InfoRow label="Camp / Showcase Opportunity" value={rd.recruiting_path.camp_opportunity} />
            <InfoRow label="Contact Window" value={rd.recruiting_path.contact_window} />
            <InfoRow label="Realistic Timeline" value={rd.recruiting_path.timeline} />
          </div>
          {rd.recruiting_path.outreach_tip && (
            <div className="bg-black/20 rounded-xl p-4">
              <p className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-1">💡 Outreach Tip</p>
              <p className="text-sm text-gray-300 italic">"{rd.recruiting_path.outreach_tip}"</p>
            </div>
          )}
        </Section>
      )}

      {/* Overall Assessment */}
      {hasResearch && rd?.overall_assessment && (
        <div className="bg-white/[0.04] border border-sparq-lime/20 rounded-2xl p-6">
          <p className="text-xs font-semibold text-sparq-lime uppercase tracking-wide mb-2">Overall Assessment</p>
          <p className="text-gray-200 leading-relaxed">{rd.overall_assessment}</p>
        </div>
      )}

      {/* Re-research */}
      {hasResearch && !isResearching && (
        <div className="pb-8 text-center">
          <button onClick={startResearch} className="text-xs text-gray-600 hover:text-gray-400 transition-colors">
            ↻ Refresh Research
          </button>
        </div>
      )}
    </div>
  )
}
