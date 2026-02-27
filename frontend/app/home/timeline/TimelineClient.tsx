'use client'

import { useEffect, useState } from 'react'
import { useUser } from '@clerk/nextjs'
const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'
const getApiBase = () => process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

interface TimelineEvent {
  type: 'onboarding' | 'college_added' | 'outreach_sent'
  date: string
  title: string
  detail: string | null
}

function relativeDate(dateStr: string): string {
  const date = new Date(dateStr)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays} days ago`
  if (diffDays < 30) return `${Math.floor(diffDays / 7)} weeks ago`
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
}

const EVENT_STYLES: Record<TimelineEvent['type'], { dot: string; icon: string }> = {
  onboarding: { dot: 'bg-sparq-lime', icon: '🏁' },
  college_added: { dot: 'bg-blue-400', icon: '🎓' },
  outreach_sent: { dot: 'bg-orange-400', icon: '✉️' },
}

export default function TimelineClient() {
  const { user, isLoaded } = useUser()
  const [events, setEvents] = useState<TimelineEvent[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!isLoaded || !user) return
    const clerkId = user.id
    fetch(`${getApiBase()}/workspace/timeline/${clerkId}`)
      .then((r) => r.json())
      .then((data) => {
        setEvents(Array.isArray(data) ? data : [])
        setLoading(false)
      })
      .catch(() => setLoading(false))
  }, [isLoaded, user])

  return (
    <div className="p-6 max-w-2xl">
      <h1 className="text-2xl font-bold text-white mb-1">Timeline</h1>
      <p className="text-gray-400 text-sm mb-8">Your recruiting activity, in order.</p>

      {loading && (
        <div className="space-y-6">
          {[0, 1, 2].map((i) => (
            <div key={i} className="flex gap-4 animate-pulse">
              <div className="flex flex-col items-center">
                <div className="w-3 h-3 rounded-full bg-gray-700 mt-1" />
                <div className="w-0.5 flex-1 bg-gray-800 mt-1" />
              </div>
              <div className="pb-6 flex-1">
                <div className="h-4 bg-gray-700 rounded w-48 mb-2" />
                <div className="h-3 bg-gray-800 rounded w-32" />
              </div>
            </div>
          ))}
        </div>
      )}

      {!loading && events.length === 0 && (
        <div className="text-center py-16 text-gray-500">
          <div className="text-4xl mb-3">📭</div>
          <p className="text-sm">No activity yet — complete onboarding to get started.</p>
        </div>
      )}

      {!loading && events.length > 0 && (
        <div className="space-y-0">
          {events.map((event, i) => {
            const style = EVENT_STYLES[event.type]
            const isLast = i === events.length - 1
            return (
              <div key={i} className="flex gap-4">
                {/* Timeline column */}
                <div className="flex flex-col items-center">
                  <div className={`w-3 h-3 rounded-full mt-1 flex-shrink-0 ${style.dot}`} />
                  {!isLast && <div className="w-0.5 flex-1 bg-gray-700 mt-1" />}
                </div>

                {/* Content */}
                <div className={`pb-6 flex-1 ${isLast ? '' : ''}`}>
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <span className="mr-2">{style.icon}</span>
                      <span className="text-white text-sm font-medium">{event.title}</span>
                      {event.detail && (
                        <p className="text-gray-400 text-xs mt-0.5 ml-6">{event.detail}</p>
                      )}
                    </div>
                    <span className="text-gray-500 text-xs whitespace-nowrap flex-shrink-0 mt-0.5">
                      {relativeDate(event.date)}
                    </span>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
