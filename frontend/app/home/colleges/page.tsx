'use client'

import { useMemo, useState } from 'react'

const MOCK_COLLEGES = [
  { id: 1, name: 'University of Georgia', location: 'Athens, GA', division: 'D1', fitScore: 94, status: 'Interested' },
  { id: 2, name: 'Appalachian State', location: 'Boone, NC', division: 'D1', fitScore: 88, status: 'Researching' },
  { id: 3, name: 'James Madison University', location: 'Harrisonburg, VA', division: 'D1', fitScore: 85, status: 'Researching' },
  { id: 4, name: 'Western Kentucky', location: 'Bowling Green, KY', division: 'D1', fitScore: 81, status: 'Researching' },
  { id: 5, name: 'Furman University', location: 'Greenville, SC', division: 'D1', fitScore: 78, status: 'Researching' },
  { id: 6, name: 'Mercer University', location: 'Macon, GA', division: 'D1', fitScore: 74, status: 'Researching' },
  { id: 7, name: 'Lenoir-Rhyne', location: 'Hickory, NC', division: 'D2', fitScore: 71, status: 'Researching' },
  { id: 8, name: 'Carson-Newman', location: 'Jefferson City, TN', division: 'D2', fitScore: 68, status: 'Researching' },
]

const DIVISION_FILTERS = ['All', 'D1', 'D2', 'D3', 'NAIA'] as const

const STATUS_CLASSES: Record<string, string> = {
  Researching: 'bg-white/10 text-gray-300',
  Interested: 'bg-blue-500/20 text-blue-300',
  Contacted: 'bg-yellow-500/20 text-yellow-300',
  Visited: 'bg-purple-500/20 text-purple-300',
  Offered: 'bg-green-500/20 text-green-300',
}

const STATUS_OPTIONS = ['Researching', 'Interested', 'Contacted', 'Visited', 'Offered']

export default function CollegesPage() {
  const [division, setDivision] = useState<(typeof DIVISION_FILTERS)[number]>('All')
  const [statuses, setStatuses] = useState<Record<number, string>>(
    () => Object.fromEntries(MOCK_COLLEGES.map((c) => [c.id, c.status])),
  )

  const colleges = useMemo(() => {
    if (division === 'All') return MOCK_COLLEGES
    return MOCK_COLLEGES.filter((college) => college.division === division)
  }, [division])

  return (
    <div className="text-white pb-8">
      <div className="p-8 pb-4">
        <h1 className="text-3xl font-black text-white">Your College Matches</h1>
        <p className="text-gray-400 mt-1">12 programs matched to your profile</p>
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
        {colleges.map((college) => {
          const status = statuses[college.id]
          return (
            <div key={college.id} className="bg-white/[0.04] border border-white/10 rounded-xl p-4 flex items-center gap-4">
              <div className="w-12 h-12 rounded-xl bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center text-sparq-lime font-black text-lg">
                {college.name[0]}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-bold text-white">{college.name}</div>
                <div className="text-gray-400 text-sm">
                  {college.location} • {college.division}
                </div>
                <div className="mt-2">
                  <div className="text-xs text-gray-400">Fit Score</div>
                  <div className="w-full bg-white/10 rounded-full h-1.5 mt-1">
                    <div
                      style={{ width: `${college.fitScore}%` }}
                      className={`h-1.5 rounded-full ${
                        college.fitScore >= 80
                          ? 'bg-sparq-lime'
                          : college.fitScore >= 60
                            ? 'bg-yellow-400'
                            : 'bg-red-400'
                      }`}
                    />
                  </div>
                  <div className="text-xs text-gray-400 mt-1">{college.fitScore}% match</div>
                </div>
              </div>

              <select
                value={status}
                onChange={(event) =>
                  setStatuses((prev) => ({
                    ...prev,
                    [college.id]: event.target.value,
                  }))
                }
                className={`px-3 py-2 rounded-lg text-sm border border-white/10 focus:outline-none ${STATUS_CLASSES[status]} [&>option]:bg-[#121212] [&>option]:text-white`}
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
