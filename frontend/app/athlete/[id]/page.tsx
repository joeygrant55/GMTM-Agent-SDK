'use client'

import { useEffect, useState } from 'react'
import { useParams } from 'next/navigation'
import { UserButton } from '@clerk/nextjs'
import AgentChat from './components/AgentChat'
import Dashboard from './components/Dashboard'
import ReportView from './components/ReportView'

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
  const [view, setView] = useState<'dashboard' | 'chat' | 'report'>('dashboard')
  const [loadConversationId, setLoadConversationId] = useState<number | null>(null)
  const [viewReportId, setViewReportId] = useState<number | null>(null)

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

  const handleViewReport = (reportId: number) => {
    setViewReportId(reportId)
    setView('report')
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
    <div className="min-h-screen min-h-[100dvh] bg-gradient-to-br from-gray-50 to-gray-100">
      {/* Header */}
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-3 py-2 sm:px-6 sm:py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <img src="/sparq-logo.jpg" alt="SPARQ" className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg flex-shrink-0" />
              <div className="min-w-0">
                <h1 className="text-sm sm:text-lg font-bold text-gray-900 truncate">SPARQ Agent</h1>
                <p className="text-xs text-gray-600 truncate hidden sm:block">{profile.first_name} {profile.last_name} • {profile.position || 'Athlete'}</p>
              </div>
            </div>
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              {/* View Toggle */}
              <div className="flex bg-gray-100 rounded-lg p-0.5">
                <button
                  onClick={() => setView('dashboard')}
                  className={`px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-md transition-colors ${
                    view === 'dashboard' ? 'bg-white shadow-sm text-gray-900 font-medium' : 'text-gray-500 hover:text-gray-700'
                  }`}
                >
                  Home
                </button>
                <button
                  onClick={() => setView('chat')}
                  className={`px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-md transition-colors ${
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
      <main className="max-w-5xl mx-auto px-3 py-4 sm:px-6 sm:py-8">
        {view === 'dashboard' ? (
          <Dashboard
            athleteId={athleteId}
            onStartChat={handleStartChat}
            onLoadChat={handleLoadChat}
            onViewReport={handleViewReport}
          />
        ) : view === 'report' && viewReportId ? (
          <ReportView
            athleteId={athleteId}
            reportId={viewReportId}
            onBack={() => setView('dashboard')}
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
