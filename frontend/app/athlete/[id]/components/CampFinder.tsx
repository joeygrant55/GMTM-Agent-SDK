'use client'

import { useState } from 'react'

interface Camp {
  name: string
  date: string
  location: string
  cost: number | null
  distance_miles?: number
  fit_score: number
  fit_reasons: string[]
  coaches?: string[]
  testing?: string[]
  url?: string
  deadline?: string
}

interface CampFinderProps {
  athleteId: string
}

export default function CampFinder({ athleteId }: CampFinderProps) {
  const [loading, setLoading] = useState(false)
  const [camps, setCamps] = useState<Camp[]>([])
  const [summary, setSummary] = useState<string>('')
  const [error, setError] = useState<string | null>(null)

  const findCamps = async () => {
    setLoading(true)
    setError(null)
    
    try {
      // Agent research takes 30-40 seconds - no timeout
      const controller = new AbortController()
      const timeoutId = setTimeout(() => controller.abort(), 60000) // 60 second timeout
      
      // Call backend directly to avoid Next.js proxy timeout
      const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
      const response = await fetch(`${backendUrl}/api/agent/find-camps/${athleteId}?max_results=10`, {
        signal: controller.signal
      })
      
      clearTimeout(timeoutId)
      
      if (!response.ok) {
        const errorData = await response.json().catch(() => ({}))
        throw new Error(errorData.detail || errorData.error || 'Failed to find camps')
      }
      
      const data = await response.json()
      setCamps(data.camps || [])
      setSummary(data.summary || '')
    } catch (err: any) {
      setError(err.message || 'Failed to load camps')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="bg-white rounded-lg shadow-sm border border-gray-200 p-4 sm:p-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-3 mb-4">
        <div>
          <h3 className="text-lg font-semibold text-gray-900">🏕️ Camp Finder Agent</h3>
          <p className="text-sm text-gray-600">AI-powered camp discovery & matching</p>
        </div>
        <button
          onClick={findCamps}
          disabled={loading}
          className="px-4 py-3 sm:py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors font-medium text-sm min-h-[44px]"
        >
          {loading ? '🤖 Agent researching... (30-40s)' : '🤖 Find My Camps'}
        </button>
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600">⚠️ {error}</p>
        </div>
      )}

      {summary && (
        <div className="mb-6 p-4 bg-indigo-50 border border-indigo-200 rounded-lg">
          <p className="text-sm text-gray-700 whitespace-pre-line">{summary}</p>
        </div>
      )}

      {camps.length > 0 && (
        <div className="space-y-4">
          <h4 className="font-semibold text-gray-900">All Camps (Ranked by Fit)</h4>
          
          {camps.map((camp, idx) => (
            <div 
              key={idx}
              className="border border-gray-200 rounded-lg p-4 hover:border-indigo-300 transition-colors"
            >
              <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-2">
                <div className="flex-1 min-w-0">
                  <h5 className="font-semibold text-gray-900">{camp.name}</h5>
                  <div className="flex flex-wrap items-center gap-2 sm:gap-3 text-sm text-gray-600 mt-1">
                    <span>📅 {camp.date}</span>
                    <span>📍 {camp.location}</span>
                    {camp.cost && <span>💰 ${camp.cost}</span>}
                    {camp.distance_miles && <span>🚗 {camp.distance_miles} miles</span>}
                  </div>
                </div>
                <div className="flex sm:flex-col items-center sm:items-end gap-2 sm:gap-0">
                  <div className="px-3 py-1 bg-indigo-100 text-indigo-700 rounded-full text-sm font-semibold">
                    Score: {camp.fit_score}
                  </div>
                  {camp.deadline && (
                    <span className="text-xs text-gray-500 sm:mt-1">
                      Deadline: {camp.deadline}
                    </span>
                  )}
                </div>
              </div>

              {camp.fit_reasons && camp.fit_reasons.length > 0 && (
                <div className="mb-3">
                  <div className="flex flex-wrap gap-2">
                    {camp.fit_reasons.map((reason, ridx) => (
                      <span 
                        key={ridx}
                        className="px-2 py-1 bg-green-50 text-green-700 text-xs rounded border border-green-200"
                      >
                        ✅ {reason}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              {camp.coaches && camp.coaches.length > 0 && (
                <div className="mb-2">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">👥 Coaches:</span> {camp.coaches.join(', ')}
                  </p>
                </div>
              )}

              {camp.testing && camp.testing.length > 0 && (
                <div className="mb-3">
                  <p className="text-sm text-gray-600">
                    <span className="font-medium">📊 Testing:</span> {camp.testing.join(', ')}
                  </p>
                </div>
              )}

              {camp.url && (
                <a
                  href={camp.url}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="inline-flex items-center gap-1 text-sm text-indigo-600 hover:text-indigo-700 font-medium"
                >
                  View Details →
                </a>
              )}
            </div>
          ))}
        </div>
      )}

      {!loading && camps.length === 0 && !error && (
        <div className="text-center py-8 text-gray-500">
          <p className="text-sm">Click "Find My Camps" to discover opportunities</p>
        </div>
      )}
    </div>
  )
}
