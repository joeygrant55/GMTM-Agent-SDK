'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { UserButton } from '@clerk/nextjs'
import AgentChat from './components/AgentChat'
import Dashboard from './components/Dashboard'

interface AthleteProfile {
  user_id: number
  first_name: string
  last_name: string
  graduation_year?: number
  city?: string
  state?: string
  position?: string
  sport?: string
}

export default function AthleteDashboard() {
  const params = useParams()
  const athleteId = params.id as string
  
  const [profile, setProfile] = useState<AthleteProfile | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [view, setView] = useState<'dashboard' | 'chat'>('dashboard')
  const [loadConversationId, setLoadConversationId] = useState<number | null>(null)

  useEffect(() => {
    setLoading(true)
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    fetch(`${backendUrl}/api/athlete/${athleteId}`)
      .then(async res => {
        if (!res.ok) throw new Error(`Athlete ${athleteId} not found`)
        return res.json()
      })
      .then(data => { setProfile(data); setLoading(false) })
      .catch(err => { setError(err.message); setLoading(false) })
  }, [athleteId])

  const handleStartChat = () => {
    setLoadConversationId(null)
    setView('chat')
  }

  const handleLoadChat = (conversationId: number) => {
    setLoadConversationId(conversationId)
    setView('chat')
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sparq-lime mx-auto"></div>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-gray-50 flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="text-6xl mb-4">🔍</div>
          <h2 className="text-2xl font-bold text-gray-900 mb-2">Athlete Not Found</h2>
          <p className="text-gray-600 mb-6">{error}</p>
          <a href="/" className="px-6 py-3 bg-sparq-charcoal text-white font-medium rounded-lg hover:bg-sparq-charcoal-light transition-colors">
            ← Back to Home
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200">
        <div className="max-w-5xl mx-auto px-4 py-3 sm:px-6">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <img src="/sparq-logo.jpg" alt="SPARQ" className="w-8 h-8 rounded-lg" />
              <div>
                <h1 className="text-lg font-bold text-gray-900">SPARQ Agent</h1>
                <p className="text-xs text-gray-600">{profile.first_name} {profile.last_name} • {profile.position || 'Athlete'}</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* View Toggle */}
              <div className="flex bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setView('dashboard')}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                    view === 'dashboard' ? 'bg-white shadow-sm text-gray-900 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Home
                </button>
                <button
                  onClick={() => setView('chat')}
                  className={`px-3 py-1.5 text-sm rounded-md transition-colors ${
                    view === 'chat' ? 'bg-white shadow-sm text-gray-900 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Agent
                </button>
              </div>
              <UserButton afterSignOutUrl="/" />
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-5xl mx-auto px-4 py-8 sm:px-6">
        {view === 'dashboard' ? (
          <Dashboard
            athleteId={athleteId}
            onStartChat={handleStartChat}
            onLoadChat={handleLoadChat}
          />
        ) : (
          <div className="max-w-4xl mx-auto">
            <AgentChat
              athleteId={athleteId}
              athleteName={`${profile.first_name} ${profile.last_name}`}
              initialConversationId={loadConversationId}
            />
          </div>
        )}
      </main>
    </div>
  )
}
