'use client'

import { useEffect, useMemo, useState } from 'react'

interface College {
  id: number
  college_name: string
  college_city: string
  college_state: string
  division: string
  fit_score: number
  status: string
}

const MOCK_FALLBACK: College[] = [
  { id: 1, college_name: 'University of Georgia', college_city: 'Athens', college_state: 'GA', division: 'D1', fit_score: 94, status: 'Interested' },
  { id: 2, college_name: 'Appalachian State', college_city: 'Boone', college_state: 'NC', division: 'D1', fit_score: 88, status: 'Researching' },
  { id: 3, college_name: 'James Madison University', college_city: 'Harrisonburg', college_state: 'VA', division: 'D1', fit_score: 85, status: 'Researching' },
  { id: 4, college_name: 'Western Kentucky', college_city: 'Bowling Green', college_state: 'KY', division: 'D1', fit_score: 81, status: 'Researching' },
  { id: 5, college_name: 'Furman University', college_city: 'Greenville', college_state: 'SC', division: 'D1', fit_score: 78, status: 'Researching' },
  { id: 6, college_name: 'Mercer University', college_city: 'Macon', college_state: 'GA', division: 'D1', fit_score: 74, status: 'Researching' },
  { id: 7, college_name: 'Lenoir-Rhyne', college_city: 'Hickory', college_state: 'NC', division: 'D2', fit_score: 71, status: 'Researching' },
  { id: 8, college_name: 'Carson-Newman', college_city: 'Jefferson City', college_state: 'TN', division: 'D2', fit_score: 68, status: 'Researching' },
]

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

export default function CollegesPage() {
  const [division, setDivision] = useState<(typeof DIVISION_FILTERS)[number]>('All')
  const [colleges, setColleges] = useState<College[]>([])
  const [loading, setLoading] = useState(true)
  const [statuses, setStatuses] = useState<Record<number, string>>({})

  useEffect(() => {
    let cancelled = false

    const loadColleges = async () => {
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL
      const clerkId = (window as unknown as { Clerk?: { user?: { id?: string } } }).Clerk?.user?.id

      if (!clerkId) {
        if (!cancelled) {
          setColleges(MOCK_FALLBACK)
          setStatuses(Object.fromEntries(MOCK_FALLBACK.map((c) => [c.id, c.status])))
          setLoading(false)
        }
        return
      }

      try {
        const res = await fetch(`${backendUrl}/api/workspace/colleges/${clerkId}`)
        const data = await res.json()
        const list = data.colleges && data.colleges.length > 0 ? data.colleges : MOCK_FALLBACK
        if (!cancelled) {
          setColleges(list)
          setStatuses(Object.fromEntries(list.map((c: College) => [c.id, c.status])))
        }
      } catch {
        if (!cancelled) {
          setColleges(MOCK_FALLBACK)
          setStatuses(Object.fromEntries(MOCK_FALLBACK.map((c) => [c.id, c.status])))
        }
      } finally {
        if (!cancelled) setLoading(false)
      }
    }

    const waitForClerk = async () => {
      for (let i = 0; i < 20; i += 1) {
        const clerkReady = (window as unknown as { Clerk?: { user?: { id?: string } } }).Clerk?.user?.id
        if (clerkReady) break
        await new Promise((resolve) => setTimeout(resolve, 150))
      }
      await loadColleges()
    }

    waitForClerk()

    return () => {
      cancelled = true
    }
  }, [])

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

  if (loading) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
      </div>
    )
  }

  return (
    <div className="text-white pb-8">
      <div className="p-8 pb-4">
        <h1 className="text-3xl font-black text-white">Your College Matches</h1>
        <p className="text-gray-400 mt-1">{colleges.length} programs matched to your profile</p>
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

      <div className="px-8 space-y-3">
        {filteredColleges.map((college) => {
          const status = statuses[college.id]
          return (
            <div key={college.id} className="bg-white/[0.04] border border-white/10 rounded-xl p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center text-sparq-lime font-black text-lg">
                {college.college_name[0]}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-bold text-white">{college.college_name}</div>
                <div className="text-gray-400 text-sm">
                  {college.college_city}, {college.college_state} • {college.division}
                </div>
                <div className="mt-2">
                  <div className="text-xs text-gray-400">Fit Score</div>
                  <div className="w-full bg-white/10 rounded-full h-1.5 mt-1">
                    <div
                      style={{ width: `${college.fit_score}%` }}
                      className={`h-1.5 rounded-full ${
                        college.fit_score >= 80
                          ? 'bg-sparq-lime'
                          : college.fit_score >= 60
                            ? 'bg-yellow-400'
                            : 'bg-red-400'
                      }`}
                    />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{college.fit_score}% match</div>
                </div>
              </div>

              <select
                value={status}
                onChange={(event) => updateStatus(college.id, event.target.value)}
                className={`px-3 py-2 rounded-lg text-sm border border-white/10 focus:outline-none ${STATUS_CLASSES[status] || STATUS_CLASSES.Researching} [&>option]:bg-[#121212] [&>option]:text-white`}
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          )
        })}
      </div>
    </div>
  )
}
