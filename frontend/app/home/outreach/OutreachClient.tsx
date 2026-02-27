'use client'

import { FormEvent, useEffect, useMemo, useState } from 'react'
import { useUser } from '@clerk/nextjs'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

interface OutreachEntry {
  id: number
  school: string
  coach: string
  method: 'Email' | 'Phone' | 'Visit' | 'Camp'
  date: string
  contact_date?: string
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

function normalizeEntry(raw: Record<string, unknown>): OutreachEntry {
  return {
    id: Number(raw.id),
    school: String(raw.school ?? ''),
    coach: String(raw.coach ?? ''),
    method: (raw.method as OutreachEntry['method']) ?? 'Email',
    date: String(raw.contact_date ?? raw.date ?? today()),
    status: (raw.status as OutreachEntry['status']) ?? 'Awaiting Response',
    notes: String(raw.notes ?? ''),
  }
}

export default function OutreachClient() {
  const { user, isLoaded } = useUser()
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  const [showForm, setShowForm] = useState(false)
  const [entries, setEntries] = useState<OutreachEntry[]>([])
  const [fetching, setFetching] = useState(true)

  const [school, setSchool] = useState('')
  const [coach, setCoach] = useState('')
  const [method, setMethod] = useState<OutreachEntry['method']>('Email')
  const [date, setDate] = useState(today())
  const [notes, setNotes] = useState('')

  const nextLocalId = useMemo(
    () => (entries.length ? Math.max(...entries.map((e) => e.id)) + 1 : 1),
    [entries]
  )

  // Load entries from backend
  useEffect(() => {
    if (!isLoaded || !user?.id) return
    fetch(`${backendUrl}/api/workspace/outreach/${user.id}`)
      .then((res) => res.json())
      .then((data) => {
        if (Array.isArray(data?.entries)) {
          setEntries(data.entries.map(normalizeEntry))
        }
      })
      .catch(() => {/* fallback: local state only */})
      .finally(() => setFetching(false))
  }, [backendUrl, isLoaded, user?.id])

  const resetForm = () => {
    setSchool('')
    setCoach('')
    setMethod('Email')
    setDate(today())
    setNotes('')
  }

  const submitEntry = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    const schoolName = school.trim()
    const coachName = coach.trim()
    if (!schoolName || !date) return

    const optimisticEntry: OutreachEntry = {
      id: nextLocalId,
      school: schoolName,
      coach: coachName,
      method,
      date,
      status: 'Awaiting Response',
      notes: notes.trim(),
    }

    setEntries((prev) => [optimisticEntry, ...prev])
    setShowForm(false)
    resetForm()

    if (user?.id) {
      fetch(`${backendUrl}/api/workspace/outreach/${user.id}`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          school: schoolName,
          coach: coachName || undefined,
          method,
          contact_date: date,
          status: 'Awaiting Response',
          notes: notes.trim() || undefined,
        }),
      })
        .then((res) => res.json())
        .then((data) => {
          if (data?.entry?.id) {
            setEntries((prev) =>
              prev.map((e) => (e.id === optimisticEntry.id ? normalizeEntry(data.entry) : e))
            )
          }
        })
        .catch(() => {/* keep optimistic entry */})
    }
  }

  const updateStatus = (entryId: number, newStatus: OutreachEntry['status']) => {
    setEntries((prev) =>
      prev.map((e) => (e.id === entryId ? { ...e, status: newStatus } : e))
    )
    if (user?.id) {
      fetch(`${backendUrl}/api/workspace/outreach/${entryId}/status`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ status: newStatus }),
      }).catch(() => {/* best-effort */})
    }
  }

  if (fetching && isLoaded && user?.id) {
    return (
      <div className="p-8 flex items-center justify-center min-h-64">
        <div className="w-8 h-8 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
      </div>
    )
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

      {showForm && (
        <form onSubmit={submitEntry} className="mt-6 bg-white/[0.04] border border-white/10 rounded-2xl p-5 grid gap-4">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="grid gap-1">
              <span className="text-sm text-gray-300">School</span>
              <input value={school} onChange={(e) => setSchool(e.target.value)} required
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime"
                placeholder="University name" />
            </label>
            <label className="grid gap-1">
              <span className="text-sm text-gray-300">Coach (optional)</span>
              <input value={coach} onChange={(e) => setCoach(e.target.value)}
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime"
                placeholder="Coach name" />
            </label>
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <label className="grid gap-1">
              <span className="text-sm text-gray-300">Method</span>
              <select value={method} onChange={(e) => setMethod(e.target.value as OutreachEntry['method'])}
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime">
                {METHOD_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </label>
            <label className="grid gap-1">
              <span className="text-sm text-gray-300">Date</span>
              <input type="date" value={date} onChange={(e) => setDate(e.target.value)} required
                className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 focus:outline-none focus:border-sparq-lime" />
            </label>
          </div>
          <label className="grid gap-1">
            <span className="text-sm text-gray-300">Notes (optional)</span>
            <textarea value={notes} onChange={(e) => setNotes(e.target.value)}
              className="bg-sparq-charcoal border border-white/10 rounded-lg px-3 py-2 min-h-24 focus:outline-none focus:border-sparq-lime"
              placeholder="What did you send? Any follow-up details?" />
          </label>
          <div className="flex justify-end">
            <button type="submit" className="px-4 py-2 rounded-lg font-semibold bg-sparq-lime text-sparq-charcoal hover:opacity-90">
              Save Contact
            </button>
          </div>
        </form>
      )}

      {entries.length === 0 ? (
        <div className="mt-6 bg-white/[0.04] border border-white/10 rounded-2xl p-10 text-center">
          <div className="text-4xl mb-3">✉️</div>
          <h2 className="text-xl font-bold text-white mb-2">No contacts logged yet</h2>
          <p className="text-gray-400">Hit "Log Contact" to start tracking your coach outreach.</p>
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
                {entry.coach && <div className="text-gray-300 text-sm">{entry.coach}</div>}
                <div className="text-gray-400 text-sm mt-1">{entry.method} • {entry.date}</div>
                {entry.notes && <div className="text-gray-400 text-sm mt-1">{entry.notes}</div>}
              </div>
              <select value={entry.status} onChange={(e) => updateStatus(entry.id, e.target.value as OutreachEntry['status'])}
                className={`px-3 py-2 rounded-lg text-sm border border-white/10 focus:outline-none ${STATUS_COLORS[entry.status]} [&>option]:bg-[#121212] [&>option]:text-white`}>
                {STATUS_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
