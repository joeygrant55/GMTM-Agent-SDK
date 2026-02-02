'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import CampFinder from './components/CampFinder'

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
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm">
        <div className="max-w-7xl mx-auto px-4 py-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <a href="/" className="w-10 h-10 bg-indigo-600 rounded-lg flex items-center justify-center">
                <span className="text-white font-bold text-xl">⚡</span>
              </a>
              <h1 className="text-2xl font-bold text-gray-900">SPARQ Agent</h1>
            </div>
            <div className="flex items-center space-x-4">
              <span className="text-sm text-gray-600">Athlete #{athleteId}</span>
              <button className="px-4 py-2 text-sm font-medium text-gray-700 hover:text-gray-900">
                Settings
              </button>
            </div>
          </div>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 py-8 sm:px-6 lg:px-8">
        {/* Profile Header */}
        <div className="bg-white rounded-xl shadow-sm p-6 mb-8">
          <div className="flex items-start space-x-6">
            <div className="w-20 h-20 bg-indigo-100 rounded-full flex items-center justify-center">
              <span className="text-3xl font-bold text-indigo-600">
                {profile.first_name?.[0]}{profile.last_name?.[0]}
              </span>
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-gray-900">
                {profile.first_name} {profile.last_name}
              </h2>
              <div className="mt-1 flex flex-wrap gap-3 text-sm text-gray-600">
                {profile.position && (
                  <span className="inline-flex items-center px-3 py-1 rounded-full bg-blue-100 text-blue-800">
                    {profile.position}
                  </span>
                )}
                {profile.city && profile.state && (
                  <span>📍 {profile.city}, {profile.state}</span>
                )}
                {profile.graduation_year && (
                  <span>🎓 Class of {profile.graduation_year}</span>
                )}
                {profile.sport && (
                  <span>🏈 {profile.sport}</span>
                )}
              </div>
            </div>
            <div className="text-right">
              <div className="text-sm text-gray-500">SPARQ Score</div>
              <div className="text-3xl font-bold text-indigo-600">
                {profile.sparq_score || 'N/A'}
              </div>
            </div>
          </div>
        </div>

        {/* Quick Stats */}
        <div className="grid md:grid-cols-4 gap-6 mb-8">
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-sm text-gray-500 mb-1">Profile Views</div>
            <div className="text-2xl font-bold text-gray-900">23</div>
            <div className="text-xs text-green-600 mt-1">↑ 15% this week</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-sm text-gray-500 mb-1">New Opportunities</div>
            <div className="text-2xl font-bold text-gray-900">5</div>
            <div className="text-xs text-indigo-600 mt-1">Updated daily</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-sm text-gray-500 mb-1">Recruiting Rank</div>
            <div className="text-2xl font-bold text-gray-900">Top 15%</div>
            <div className="text-xs text-gray-600 mt-1">In your position</div>
          </div>
          <div className="bg-white rounded-lg shadow-sm p-6">
            <div className="text-sm text-gray-500 mb-1">Action Items</div>
            <div className="text-2xl font-bold text-gray-900">2</div>
            <div className="text-xs text-orange-600 mt-1">Needs attention</div>
          </div>
        </div>

        {/* Agent Recommendations */}
        <div className="bg-gradient-to-r from-indigo-500 to-purple-600 rounded-xl shadow-lg p-8 mb-8 text-white">
          <h3 className="text-2xl font-bold mb-4">🤖 Your Agent's Recommendations</h3>
          <div className="space-y-3">
            <div className="bg-white bg-opacity-20 rounded-lg p-4">
              <div className="font-semibold mb-1">Update your film</div>
              <div className="text-sm opacity-90">Haven't posted in 60 days - coaches want recent footage</div>
            </div>
            <div className="bg-white bg-opacity-20 rounded-lg p-4">
              <div className="font-semibold mb-1">3 camps match your profile</div>
              <div className="text-sm opacity-90">SPARQ Combine in Houston (Feb 24), Dallas Showcase (Mar 5)</div>
            </div>
            <div className="bg-white bg-opacity-20 rounded-lg p-4">
              <div className="font-semibold mb-1">Coach from Houston viewed your profile</div>
              <div className="text-sm opacity-90">Send a follow-up message within 48 hours</div>
            </div>
          </div>
        </div>

        {/* Camp Finder Agent */}
        <div className="mb-8">
          <CampFinder athleteId={athleteId} />
        </div>

        {/* Opportunities Section */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h3 className="text-2xl font-bold text-gray-900">Opportunities For You</h3>
            <button className="text-sm text-indigo-600 hover:text-indigo-700 font-medium">
              View All →
            </button>
          </div>
          <div className="grid md:grid-cols-3 gap-6">
            {opportunities.slice(0, 3).map((opp) => (
              <div key={opp.user_id} className="bg-white rounded-lg shadow-sm p-6 hover:shadow-md transition-shadow">
                <div className="flex items-start justify-between mb-3">
                  <div className="w-12 h-12 bg-blue-100 rounded-lg flex items-center justify-center">
                    <span className="text-xl">🏫</span>
                  </div>
                  <span className="text-xs px-2 py-1 bg-green-100 text-green-800 rounded-full">
                    Good Match
                  </span>
                </div>
                <h4 className="font-semibold text-gray-900 mb-2">
                  Similar Athlete: {opp.first_name} {opp.last_name}
                </h4>
                <div className="text-sm text-gray-600 space-y-1">
                  <div>Position: {opp.position || 'N/A'}</div>
                  <div>Location: {opp.city}, {opp.state}</div>
                  {opp.sparq_score && <div>SPARQ: {opp.sparq_score}</div>}
                </div>
                <button className="mt-4 w-full px-4 py-2 bg-indigo-600 text-white text-sm font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                  Learn More
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Chat Section */}
        <div className="bg-white rounded-xl shadow-sm p-6">
          <h3 className="text-xl font-bold text-gray-900 mb-4">Ask Your Agent</h3>
          <div className="space-y-4">
            <div className="flex space-x-3">
              <div className="w-10 h-10 bg-gray-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-lg">👤</span>
              </div>
              <div className="flex-1 bg-gray-100 rounded-lg p-3">
                <p className="text-sm text-gray-700">What colleges are recruiting {profile.position}s like me?</p>
              </div>
            </div>
            <div className="flex space-x-3">
              <div className="w-10 h-10 bg-indigo-100 rounded-full flex items-center justify-center flex-shrink-0">
                <span className="text-lg">⚡</span>
              </div>
              <div className="flex-1 bg-indigo-50 rounded-lg p-3">
                <p className="text-sm text-gray-700">
                  Based on your metrics and location ({profile.state}), I found 12 programs actively 
                  recruiting {profile.position}s in your class. Top matches include University of Houston, 
                  TCU, and UTSA. Want me to draft introduction emails for you?
                </p>
              </div>
            </div>
            <div className="flex space-x-3">
              <input
                type="text"
                placeholder="Ask anything about recruiting..."
                className="flex-1 px-4 py-3 border border-gray-300 rounded-lg focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500"
              />
              <button className="px-6 py-3 bg-indigo-600 text-white font-medium rounded-lg hover:bg-indigo-700 transition-colors">
                Send
              </button>
            </div>
          </div>
        </div>
      </main>
    </div>
  )
}
