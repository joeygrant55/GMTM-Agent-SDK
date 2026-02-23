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
  const [autoStartMessage, setAutoStartMessage] = useState<string | null>(null)

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
    setAutoStartMessage(null)
    setLoadConversationId(null)
    setView('chat')
  }

  const handleFirstRun = () => {
    setAutoStartMessage('Analyze my recruiting profile and give me a full breakdown — my top college program fits, how my metrics compare, and what I should focus on to improve my recruiting chances.')
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
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-[#c8ff00] mx-auto"></div>
      </div>
    )
  }

  if (error || !profile) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-4 rounded-2xl bg-[#141414] flex items-center justify-center">
            <svg className="w-8 h-8 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}><path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" /></svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2 font-display">Athlete Not Found</h2>
          <p className="text-white/50 mb-6">{error}</p>
          <a href="/" className="px-6 py-3 bg-[#c8ff00] text-[#0a0a0a] font-semibold rounded-lg hover:bg-[#d4ff33] transition-colors">
            ← Back to Home
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen min-h-[100dvh] bg-[#0a0a0a]">
      {/* Header */}
      <header className="bg-[#0a0a0a] border-b border-white/[0.06] sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-3 py-2 sm:px-6 sm:py-3">
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-2 sm:gap-3 min-w-0 flex-1">
              <div className="w-7 h-7 sm:w-8 sm:h-8 rounded-lg bg-[#141414] border border-white/[0.06] flex items-center justify-center flex-shrink-0">
                <span className="text-[#c8ff00] font-bold text-xs font-display">S</span>
              </div>
              <div className="min-w-0">
                <h1 className="text-sm sm:text-lg font-bold text-white truncate font-display">SPARQ Agent</h1>
                <p className="text-xs text-white/40 truncate hidden sm:block">{profile.first_name} {profile.last_name} • {profile.position || 'Athlete'}</p>
              </div>
            </div>
            <div className="flex items-center gap-1 sm:gap-2 flex-shrink-0">
              {/* View Toggle */}
              <div className="flex bg-white/[0.06] rounded-lg p-0.5">
                <button
                  onClick={() => setView('dashboard')}
                  className={`px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-md transition-colors ${
                    view === 'dashboard' ? 'bg-[#141414] shadow-sm text-white font-medium' : 'text-white/40 hover:text-white/60'
                  }`}
                >
                  Home
                </button>
                <button
                  onClick={() => setView('chat')}
                  className={`px-2 sm:px-3 py-1.5 text-xs sm:text-sm rounded-md transition-colors ${
                    view === 'chat' ? 'bg-[#141414] shadow-sm text-white font-medium' : 'text-white/40 hover:text-white/60'
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
            onFirstRun={handleFirstRun}
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
              autoStartMessage={autoStartMessage}
            />
          </div>
        )}
      </main>
    </div>
  )
}
