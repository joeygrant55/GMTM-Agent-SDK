'use client'

import { FormEvent, useMemo, useState } from 'react'

interface OutreachEntry {
  id: number
  school: string
  coach: string
  method: 'Email' | 'Phone' | 'Visit' | 'Camp'
  date: string
  status: 'Awaiting Response' | 'Responded' | 'Meeting Scheduled' | 'Archived'
  notes: string
}

const METHOD_ICONS: Record<string, string> = {
  Email: '✉️',
  Phone: '📞',
  Visit: '🏫',
  Camp: '🏕️',
}

const STATUS_COLORS: Record<string, string> = {
  'Awaiting Response': 'bg-yellow-500/20 text-yellow-300',
  Responded: 'bg-green-500/20 text-green-300',
  'Meeting Scheduled': 'bg-blue-500/20 text-blue-300',
  Archived: 'bg-white/10 text-gray-400',
}

const STATUS_OPTIONS: OutreachEntry['status'][] = [
  'Awaiting Response',
  'Responded',
  'Meeting Scheduled',
  'Archived',
]

const METHOD_OPTIONS: OutreachEntry['method'][] = ['Email', 'Phone', 'Visit', 'Camp']

const today = () => new Date().toISOString().split('T')[0]

export default function OutreachPage() {
  const [showForm, setShowForm] = useState(false)
  const [entries, setEntries] = useState<OutreachEntry[]>([])

  const [school, setSchool] = useState('')
  const [coach, setCoach] = useState('')
  const [method, setMethod] = useState<OutreachEntry['method']>('Email')
  const [date, setDate] = useState(today())
  const [notes, setNotes] = useState('')

  const nextId = useMemo(() => (entries.length ? Math.max(...entries.map((entry) => entry.id)) + 1 : 1), [entries])

  const resetForm = () => {
    setSchool('')
    setCoach('')
    setMethod('Email')
    setDate(today())
    setNotes('')
  }

  const submitEntry = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()

    const schoolName = school.trim()
    const coachName = coach.trim()
    if (!schoolName || !coachName || !date) return

    const newEntry: OutreachEntry = {
      id: nextId,
      school: schoolName,
      coach: coachName,
      method,
      date,
      status: 'Awaiting Response',
      notes: notes.trim(),
    }

    setEntries((prev) => [newEntry, ...prev])
    setShowForm(false)
    resetForm()
  }

  const updateStatus = (entryId: number, newStatus: OutreachEntry['status']) => {
    setEntries((prev) => prev.map((entry) => (entry.id === entryId ? { ...entry, status: newStatus } : entry)))
  }

  return (
    <div className="p-8 text-white pb-8">
      <div className="flex items-center justify-between gap-4">
        <div>
          <h1 className="text-3xl font-black text-white">Outreach Tracker</h1>
          <p className="text-gray-400 mt-1">Log every coach contact and track your follow-ups.</p>
        </div>
        <button
          type="button"
          onClick={() => setShowForm((prev) => !prev)}
          className="px-4 py-2 rounded-lg font-semibold bg-sparq-lime text-sparq-charcoal hover:opacity-90"
        >
          {showForm ? 'Cancel' : 'Log Contact'}
        </button>
      </div>

      {showForm ? (
        <form onSubmit={submitEntry} className="mt-6 bg-white/[0.04] border border-white/10 rounded-2xl p-5 grid gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="grid gap-1">
              <span className="text-sm text-gray-300">School</span>
              <input
                value={school}
                onChange={(event) => setSchool(event.target.value)}
                required
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime"
                placeholder="University name"
              />
            </label>

            <label className="grid gap-1">
              <span className="text-sm text-gray-300">Coach</span>
              <input
                value={coach}
                onChange={(event) => setCoach(event.target.value)}
                required
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime"
                placeholder="Coach name"
              />
            </label>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="grid gap-1">
              <span className="text-sm text-gray-300">Method</span>
              <select
                value={method}
                onChange={(event) => setMethod(event.target.value as OutreachEntry['method'])}
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime"
              >
                {METHOD_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </label>

            <label className="grid gap-1">
              <span className="text-sm text-gray-300">Date</span>
              <input
                type="date"
                value={date}
                onChange={(event) => setDate(event.target.value)}
                required
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime"
              />
            </label>
          </div>

          <label className="grid gap-1">
            <span className="text-sm text-gray-300">Notes (optional)</span>
            <textarea
              value={notes}
              onChange={(event) => setNotes(event.target.value)}
              className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 min-h-24 focus:outline-none focus:border-sparq-lime"
              placeholder="What did you send? Any follow-up details?"
            />
          </label>

          <div className="flex justify-end">
            <button type="submit" className="px-4 py-2 rounded-lg font-semibold bg-sparq-lime text-sparq-charcoal hover:opacity-90">
              Save Contact
            </button>
          </div>
        </form>
      ) : null}

      {entries.length === 0 ? (
        <div className="mt-6 bg-white/[0.04] border border-white/10 rounded-2xl p-10 text-center">
          <div className="text-4xl mb-3">✉️</div>
          <h2 className="text-xl font-bold text-white mb-2">No contacts logged yet</h2>
          <p className="text-gray-400">Start with Log Contact to track outreach with coaches.</p>
        </div>
      ) : (
        <div className="mt-6 space-y-3">
          {entries.map((entry) => (
            <div key={entry.id} className="bg-white/[0.04] border border-white/10 rounded-xl p-4 flex flex-col md:flex-row gap-3 md:items-center">
              <div className="w-12 h-12 rounded-xl bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center text-2xl">
                {METHOD_ICONS[entry.method]}
              </div>

              <div className="flex-1 min-w-0">
                <div className="font-bold text-white">{entry.school}</div>
                <div className="text-gray-300 text-sm">{entry.coach}</div>
                <div className="text-gray-400 text-sm mt-1">
                  {entry.method} • {entry.date}
                </div>
                {entry.notes ? <div className="text-gray-400 text-sm mt-1">{entry.notes}</div> : null}
              </div>

              <select
                value={entry.status}
                onChange={(event) => updateStatus(entry.id, event.target.value as OutreachEntry['status'])}
                className={`px-3 py-2 rounded-lg text-sm border border-white/10 focus:outline-none ${STATUS_COLORS[entry.status]} [&>option]:bg-[#121212] [&>option]:text-white`}
              >
                {STATUS_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option}
                  </option>
                ))}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
