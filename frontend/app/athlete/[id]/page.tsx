'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import AgentChat from './components/AgentChat'

interface AthleteProfile {
  user_id: number
  first_name: string
  last_name: string
  graduation_year?: number
  city?: string
  state?: string
  position?: string
  sport?: string
  avatar_url?: string
  event_name?: string
  sparq_score?: number
}

export default function AthleteDashboard() {
  const params = useParams()
  const athleteId = params.id as string
  
  const [profile, setProfile] = useState<AthleteProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [opportunities, setOpportunities] = useState<AthleteProfile[]>([])

  useEffect(() => {
    setLoading(true)
    setError(null)
    
    // Fetch specific athlete profile and similar athletes (opportunities)
    Promise.all([
      fetch(`/api/athlete/${athleteId}`),
      fetch(`/api/search?limit=6`)
    ])
      .then(async ([profileRes, oppsRes]) => {
        if (!profileRes.ok) {
          const errorData = await profileRes.json()
          throw new Error(errorData.detail || `Athlete ${athleteId} not found`)
        }
        return Promise.all([profileRes.json(), oppsRes.json()])
      })
      .then(([athleteData, oppsData]) => {
        // Set the specific athlete profile
        setProfile(athleteData)
        setOpportunities(oppsData.athletes || [])
        setLoading(false)
      })
      .catch(err => {
        console.error('Failed to fetch data:', err)
        setError(err.message || 'Failed to load athlete data')
        setLoading(false)
      })
  }, [athleteId])

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-indigo-600 mx-auto"></div>
          <p className="mt-4 text-gray-600">Loading your SPARQ Agent dashboard...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">🔍</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Athlete Not Found</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <div className="space-y-3">
            <a 
              href="/" 
              className="inline-block w-full px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors"
            >
              ← Back to Home
            </a>
            <div className="text-sm text-gray-500">
              Try these athlete IDs: 
              <a href="/athlete/383" className="text-indigo-600 hover:text-indigo-700 ml-1">383</a>,
              <a href="/athlete/435" className="text-indigo-600 hover:text-indigo-700 ml-1">435</a>,
              <a href="/athlete/2370" className="text-indigo-600 hover:text-indigo-700 ml-1">2370</a>
            </div>
          </div>
        </div>
      </div>
    )
  }

  if (!profile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center">
          <p className="text-red-600">No athlete data available</p>
          <a href="/" className="mt-4 inline-block text-indigo-600 hover:text-indigo-700">
            ← Back to home
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Minimal Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-8 h-8 bg-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-lg">⚡</span>
              </div>
              <div>
                <h1 className="text-lg font-bold text-gray-900">SPARQ Agent</h1>
                <p className="text-xs text-gray-600">{profile.first_name} {profile.last_name} • {profile.position || 'Athlete'}</p>
              </div>
            </div>
            <a href="/" className="text-sm text-gray-600 hover:text-gray-900">
              Dashboard
            </a>
          </div>
        </div>
      </header>

      {/* Hero Chat Interface */}
      <main className="max-w-5xl mx-auto px-4 py-8 sm:px-6">
        <div className="mb-6 text-center">
          <h2 className="text-3xl font-bold text-gray-900 mb-2">
            Your AI Recruiting Coordinator
          </h2>
          <p className="text-gray-600">
            Ask anything about recruiting, camps, coaches, or your athletic career
          </p>
        </div>

        {/* Main Chat Interface - Full width, centered */}
        <div className="max-w-4xl mx-auto">
          <AgentChat 
            athleteId={athleteId}
            athleteName={`${profile.first_name} ${profile.last_name}`}
          />
        </div>

        {/* Subtle footer info */}
        <div className="mt-8 text-center text-sm text-gray-500">
          <p>
            🏈 {profile.position} • 📍 {profile.city}, {profile.state} 
            {profile.graduation_year && ` • 🎓 Class of ${profile.graduation_year}`}
          </p>
        </div>
      </main>
    </div>
  )
}
