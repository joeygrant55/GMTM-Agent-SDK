'use client'

import { useState, useEffect } from 'react'

interface DashboardProps {
  athleteId: string
  onStartChat: () => void
  onLoadChat: (conversationId: number) => void
  onViewReport: (reportId: number) => void
  onFirstRun: () => void
}

const PLATFORM_META: Record<string, { label: string, icon: string, placeholder: string }> = {
  hudl: { label: 'Hudl', icon: '🎬', placeholder: 'https://www.hudl.com/profile/...' },
  twitter: { label: 'Twitter / X', icon: '𝕏', placeholder: 'https://x.com/username' },
  instagram: { label: 'Instagram', icon: '📸', placeholder: 'https://instagram.com/username' },
  maxpreps: { label: 'MaxPreps', icon: '📊', placeholder: 'https://www.maxpreps.com/athlete/...' },
  '247sports': { label: '247Sports', icon: '⭐', placeholder: 'https://247sports.com/player/...' },
  rivals: { label: 'Rivals', icon: '🏈', placeholder: 'https://rivals.com/...' },
  youtube: { label: 'YouTube', icon: '▶️', placeholder: 'https://youtube.com/@channel' },
  personal_website: { label: 'Website', icon: '🌐', placeholder: 'https://yoursite.com' },
}

const REPORT_TYPE_META: Record<string, { label: string, icon: React.ReactNode, color: string }> = {
  college_fit: {
    label: 'College Fit',
    icon: <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h8a2 2 0 012 2v12a1 1 0 110 2h-3a1 1 0 01-1-1v-2a1 1 0 00-1-1H9a1 1 0 00-1 1v2a1 1 0 01-1 1H4a1 1 0 110-2V4zm3 1h2v2H7V5zm2 4H7v2h2V9zm2-4h2v2h-2V5zm2 4h-2v2h2V9z" clipRule="evenodd"/></svg>,
    color: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
  },
  profile_analysis: {
    label: 'Profile Analysis',
    icon: <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>,
    color: 'bg-green-500/10 text-green-400 border-green-500/20',
  },
  camp_research: {
    label: 'Camp Research',
    icon: <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M5.05 4.05a7 7 0 119.9 9.9L10 18.9l-4.95-4.95a7 7 0 010-9.9zM10 11a2 2 0 100-4 2 2 0 000 4z" clipRule="evenodd"/></svg>,
    color: 'bg-orange-500/10 text-orange-400 border-orange-500/20',
  },
  research: {
    label: 'Research',
    icon: <svg className="w-3.5 h-3.5" fill="currentColor" viewBox="0 0 20 20"><path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd"/></svg>,
    color: 'bg-white/5 text-gray-400 border-white/10',
  },
}

export default function Dashboard({ athleteId, onStartChat, onLoadChat, onViewReport, onFirstRun }: DashboardProps) {
  const [data, setData] = useState<any>(null)
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [addingLink, setAddingLink] = useState(false)
  const [newLink, setNewLink] = useState({ platform: '', url: '' })
  const [sharingReportId, setSharingReportId] = useState<number | null>(null)
  const [copiedReportId, setCopiedReportId] = useState<number | null>(null)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  const shareReport = async (e: React.MouseEvent, reportId: number) => {
    e.stopPropagation()
    setSharingReportId(reportId)
    try {
      const res = await fetch(`${backendUrl}/api/reports/${athleteId}/${reportId}/share-token`)
      if (!res.ok) throw new Error('failed')
      const { url } = await res.json()
      await navigator.clipboard.writeText(url)
      setCopiedReportId(reportId)
      setTimeout(() => setCopiedReportId(null), 2500)
    } catch {
      // Fallback — just copy current page URL
      await navigator.clipboard.writeText(window.location.href)
    } finally {
      setSharingReportId(null)
    }
  }

  useEffect(() => {
    Promise.all([
      fetch(`${backendUrl}/api/dashboard/${athleteId}`).then(r => r.json()),
      fetch(`${backendUrl}/api/reports/${athleteId}`).then(r => r.json()).catch(() => ({ reports: [] }))
    ]).then(([dashData, reportsData]) => {
      setData(dashData)
      setReports(reportsData.reports || [])
      setLoading(false)
    }).catch(() => setLoading(false))
  }, [athleteId])

  const addLink = async () => {
    if (!newLink.platform || !newLink.url) return
    await fetch(`${backendUrl}/api/links`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ user_id: athleteId, ...newLink })
    })
    const res = await fetch(`${backendUrl}/api/dashboard/${athleteId}`)
    setData(await res.json())
    setNewLink({ platform: '', url: '' })
    setAddingLink(false)
  }

  const deleteLink = async (linkId: number) => {
    await fetch(`${backendUrl}/api/links/${linkId}`, { method: 'DELETE' })
    const res = await fetch(`${backendUrl}/api/dashboard/${athleteId}`)
    setData(await res.json())
  }

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sparq-lime"></div>
      </div>
    )
  }

  if (!data) return null

  const { profile, metrics, offer_count, links, recent_chats, completeness, suggested_links } = data

  // Separate highlighted metrics (speed/agility type) from others
  const highlightKeys = ['40-yard dash', '40 yard', 'shuttle', 'vertical', 'broad jump', 'bench']
  const isHighlight = (title: string) => highlightKeys.some(k => title.toLowerCase().includes(k))

  return (
    <div className="space-y-6">
      {/* ===== PROFILE CARD ===== */}
      <div className="bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/10 rounded-2xl overflow-hidden">
        <div className="p-5 sm:p-8">
          <div className="flex flex-col sm:flex-row gap-6">
            {/* Identity */}
            <div className="flex-1">
              <div className="flex items-start gap-4 mb-5">
                <div className="w-16 h-16 sm:w-20 sm:h-20 bg-gradient-to-br from-sparq-lime/30 to-sparq-lime/10 rounded-2xl flex items-center justify-center flex-shrink-0 border border-sparq-lime/20">
                  <span className="text-sparq-lime font-black text-2xl sm:text-3xl">
                    {profile.first_name?.[0]}{profile.last_name?.[0]}
                  </span>
                </div>
                <div>
                  <h2 className="text-2xl sm:text-3xl font-black text-white leading-tight font-display">
                    {profile.first_name} {profile.last_name}
                  </h2>
                  <p className="text-gray-400 text-sm mt-1">
                    {profile.position || 'Athlete'} {profile.graduation_year ? `· Class of ${profile.graduation_year}` : ''}
                  </p>
                  <p className="text-gray-500 text-sm">
                    {[profile.city, profile.state].filter(Boolean).join(', ')}
                  </p>
                  {offer_count > 0 && (
                    <div className="flex items-center gap-1.5 mt-2">
                      <span className="px-2.5 py-0.5 bg-sparq-lime/10 border border-sparq-lime/20 rounded-full text-sparq-lime text-xs font-bold">
                        🎓 {offer_count} Scholarship Offer{offer_count !== 1 ? 's' : ''}
                      </span>
                    </div>
                  )}
                </div>
              </div>

              {/* Key Metrics Grid */}
              {metrics.length > 0 && (
                <div className="grid grid-cols-3 sm:grid-cols-4 gap-2 sm:gap-3">
                  {metrics.slice(0, 8).map((m: any) => {
                    const highlighted = isHighlight(m.title)
                    return (
                      <div
                        key={m.title}
                        className={`rounded-xl px-3 py-2.5 text-center ${
                          highlighted
                            ? 'bg-sparq-lime/10 border border-sparq-lime/20'
                            : 'bg-white/5 border border-white/5'
                        }`}
                      >
                        <div className={`text-lg font-black ${highlighted ? 'text-sparq-lime' : 'text-white'}`}>
                          {m.value}{m.unit ? ` ${m.unit}` : ''}
                        </div>
                        <div className="text-[10px] text-gray-500 uppercase tracking-wider mt-0.5 truncate">
                          {m.title}
                        </div>
                        {m.verified && (
                          <div className="text-[9px] text-sparq-lime/60 mt-0.5">Verified</div>
                        )}
                      </div>
                    )
                  })}
                </div>
              )}
            </div>

            {/* Right side: Profile completeness */}
            <div className="sm:w-[200px] flex-shrink-0 flex flex-col items-center justify-center">
              <div className="relative w-28 h-28">
                <svg className="w-28 h-28 -rotate-90" viewBox="0 0 120 120">
                  <circle cx="60" cy="60" r="52" fill="none" stroke="rgba(255,255,255,0.06)" strokeWidth="8" />
                  <circle
                    cx="60" cy="60" r="52" fill="none"
                    stroke="#c8ff00" strokeWidth="8" strokeLinecap="round"
                    strokeDasharray={`${2 * Math.PI * 52}`}
                    strokeDashoffset={`${2 * Math.PI * 52 * (1 - completeness / 100)}`}
                    className="transition-all duration-1000 ease-out"
                  />
                </svg>
                <div className="absolute inset-0 flex flex-col items-center justify-center">
                  <span className="text-2xl font-black text-sparq-lime">{completeness}%</span>
                  <span className="text-[9px] text-gray-500 uppercase tracking-wider">Complete</span>
                </div>
              </div>
              <span className="text-xs text-gray-500 mt-2">Profile Strength</span>
            </div>
          </div>
        </div>
      </div>

      {/* ===== FIRST-RUN WELCOME BANNER ===== */}
      {recent_chats.length === 0 && reports.length === 0 && (
        <div className="relative overflow-hidden bg-gradient-to-br from-sparq-lime/[0.12] via-sparq-lime/[0.06] to-transparent border border-sparq-lime/30 rounded-2xl p-6 sm:p-8">
          {/* Background glow */}
          <div className="absolute -top-10 -right-10 w-48 h-48 bg-sparq-lime/10 rounded-full blur-3xl pointer-events-none" />
          <div className="relative">
            <div className="inline-flex items-center gap-2 px-3 py-1 bg-sparq-lime/10 border border-sparq-lime/20 rounded-full text-sparq-lime text-xs font-bold mb-4 tracking-wide uppercase">
              <span className="w-1.5 h-1.5 rounded-full bg-sparq-lime animate-pulse" />
              First Analysis Ready
            </div>
            <h2 className="text-xl sm:text-2xl font-black text-white mb-2 font-display leading-tight">
              Ready to find your colleges?
            </h2>
            <p className="text-gray-400 text-sm sm:text-base mb-6 max-w-lg leading-relaxed">
              Your agent has your full athletic profile loaded. Hit the button and it'll analyze your metrics, find your best-fit programs, and show you exactly where you stack up — in about 30 seconds.
            </p>
            <button
              onClick={onFirstRun}
              className="inline-flex items-center gap-2.5 px-6 py-3.5 bg-sparq-lime text-sparq-charcoal font-bold text-sm rounded-xl hover:bg-sparq-lime-dark active:scale-[0.98] transition-all shadow-lg shadow-sparq-lime/20"
            >
              <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
              </svg>
              Run My First Analysis
            </button>
            <p className="text-gray-600 text-xs mt-3">Takes ~30 seconds · No setup needed</p>
          </div>
        </div>
      )}

      {/* ===== QUICK ACTIONS ===== */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
        {/* Quick Scan */}
        <a
          href="/quick-scan"
          className="group bg-gradient-to-br from-sparq-lime/10 to-transparent border border-sparq-lime/30 rounded-2xl p-5 text-left hover:border-sparq-lime/60 transition-all active:scale-[0.98] block"
        >
          <div className="w-10 h-10 rounded-xl bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center mb-3 group-hover:bg-sparq-lime/20 transition-colors">
            <svg className="w-5 h-5 text-sparq-lime" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="m3.75 13.5 10.5-11.25L12 10.5h8.25L9.75 21.75 12 13.5H3.75Z" />
            </svg>
          </div>
          <div className="flex items-center gap-2 mb-1">
            <div className="font-bold text-white text-base font-display">View Quick Scan</div>
            <span className="text-[9px] font-bold text-sparq-lime bg-sparq-lime/10 border border-sparq-lime/20 px-1.5 py-0.5 rounded-full uppercase tracking-wider">Free</span>
          </div>
          <div className="text-gray-500 text-sm">
            Your real metrics + percentile rankings vs. other athletes
          </div>
        </a>

        <button
          onClick={onStartChat}
          className="group bg-white/[0.04] border border-white/10 rounded-2xl p-5 text-left hover:border-white/20 transition-all active:scale-[0.98]"
        >
          <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-3 group-hover:bg-white/10 transition-colors">
            <svg className="w-5 h-5 text-sparq-lime" fill="currentColor" viewBox="0 0 20 20">
              <path d="M11.3 1.046A1 1 0 0112 2v5h4a1 1 0 01.82 1.573l-7 10A1 1 0 018 18v-5H4a1 1 0 01-.82-1.573l7-10a1 1 0 01.12-.381z"/>
            </svg>
          </div>
          <div className="font-bold text-white text-base font-display">New Research</div>
          <div className="text-gray-500 text-sm mt-1">
            Ask your agent about colleges, camps, recruiting strategies
          </div>
        </button>
        {recent_chats.length > 0 && (
          <button
            onClick={() => onLoadChat(recent_chats[0].id)}
            className="group bg-white/[0.04] border border-white/10 rounded-2xl p-5 text-left hover:border-white/20 transition-all active:scale-[0.98]"
          >
            <div className="w-10 h-10 rounded-xl bg-white/5 border border-white/10 flex items-center justify-center mb-3 group-hover:bg-white/10 transition-colors">
              <svg className="w-5 h-5 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M18 10c0 3.866-3.582 7-8 7a8.841 8.841 0 01-4.083-.98L2 17l1.338-3.123C2.493 12.767 2 11.434 2 10c0-3.866 3.582-7 8-7s8 3.134 8 7zM7 9H5v2h2V9zm8 0h-2v2h2V9zM9 9h2v2H9V9z" clipRule="evenodd"/>
              </svg>
            </div>
            <div className="font-bold text-white text-base font-display">Continue Last Chat</div>
            <div className="text-gray-500 text-sm mt-1 truncate">
              {recent_chats[0].title}
            </div>
          </button>
        )}
      </div>

      {/* ===== SAVED REPORTS ===== */}
      {reports.length > 0 && (
        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 sm:p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-sparq-lime/10 border border-sparq-lime/20 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-sparq-lime" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clipRule="evenodd"/>
              </svg>
            </div>
            <h3 className="font-bold text-white font-display">Your Reports</h3>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {reports.map((report: any) => {
              const meta = REPORT_TYPE_META[report.report_type] || REPORT_TYPE_META.research
              const isCopied = copiedReportId === report.id
              const isSharing = sharingReportId === report.id
              return (
                <div
                  key={report.id}
                  className="relative text-left p-4 bg-black/20 border border-white/[0.06] rounded-xl hover:border-sparq-lime/30 transition-all group cursor-pointer"
                  onClick={() => onViewReport(report.id)}
                >
                  <div className="flex items-start justify-between gap-2 mb-2">
                    <span className={`inline-flex items-center gap-1.5 px-2.5 py-0.5 text-xs font-medium rounded-full border ${meta.color}`}>
                      {meta.icon} {meta.label}
                    </span>
                    {/* Share button */}
                    <button
                      onClick={(e) => shareReport(e, report.id)}
                      title="Copy shareable link"
                      className="flex-shrink-0 p-1.5 rounded-lg bg-white/5 hover:bg-sparq-lime/10 border border-white/10 hover:border-sparq-lime/30 transition-all"
                    >
                      {isSharing ? (
                        <svg className="w-3 h-3 text-gray-400 animate-spin" fill="none" viewBox="0 0 24 24">
                          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"/>
                          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z"/>
                        </svg>
                      ) : isCopied ? (
                        <svg className="w-3 h-3 text-sparq-lime" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                        </svg>
                      ) : (
                        <svg className="w-3 h-3 text-gray-500 group-hover:text-gray-300" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                          <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935-2.186 2.25 2.25 0 0 0-3.935 2.186Zm0-12.814a2.25 2.25 0 1 0 3.933 2.185 2.25 2.25 0 0 0-3.933-2.185Z" />
                        </svg>
                      )}
                    </button>
                  </div>
                  <div className="font-medium text-sm text-white truncate group-hover:text-sparq-lime transition-colors">
                    {report.title}
                  </div>
                  <div className="text-[11px] text-gray-600 mt-1 flex items-center gap-2">
                    <span>{new Date(report.created_at).toLocaleDateString()}</span>
                    {isCopied && <span className="text-sparq-lime text-[10px] font-medium">Link copied!</span>}
                  </div>
                  {report.summary && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2">{report.summary}</p>
                  )}
                </div>
              )
            })}
          </div>
        </div>
      )}

      {/* ===== LINKS SECTION ===== */}
      <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 mb-4">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M12.586 4.586a2 2 0 112.828 2.828l-3 3a2 2 0 01-2.828 0 1 1 0 00-1.414 1.414 4 4 0 005.656 0l3-3a4 4 0 00-5.656-5.656l-1.5 1.5a1 1 0 101.414 1.414l1.5-1.5zm-5 5a2 2 0 012.828 0 1 1 0 101.414-1.414 4 4 0 00-5.656 0l-3 3a4 4 0 105.656 5.656l1.5-1.5a1 1 0 10-1.414-1.414l-1.5 1.5a2 2 0 11-2.828-2.828l3-3z" clipRule="evenodd"/>
              </svg>
            </div>
            <div>
              <h3 className="font-bold text-white font-display">Your Links</h3>
              <p className="text-xs text-gray-500">Add profiles so your agent can research deeper</p>
            </div>
          </div>
          <button
            onClick={() => setAddingLink(!addingLink)}
            className="text-sm px-4 py-2 bg-sparq-lime/10 text-sparq-lime border border-sparq-lime/20 rounded-lg hover:bg-sparq-lime/20 transition-colors self-start sm:self-auto font-medium"
          >
            + Add Link
          </button>
        </div>

        {/* Add Link Form */}
        {addingLink && (
          <div className="mb-4 p-4 bg-black/30 border border-white/[0.06] rounded-xl space-y-3">
            <select
              value={newLink.platform}
              onChange={e => setNewLink({ ...newLink, platform: e.target.value })}
              className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white focus:border-sparq-lime/40 focus:outline-none transition-colors [&>option]:bg-[#141414] [&>option]:text-white"
            >
              <option value="">Select platform...</option>
              {suggested_links.map((p: string) => (
                <option key={p} value={p}>{PLATFORM_META[p]?.label || p}</option>
              ))}
              {Object.keys(PLATFORM_META).filter(p => !suggested_links.includes(p)).map(p => (
                <option key={p} value={p}>{PLATFORM_META[p].label}</option>
              ))}
            </select>
            <input
              type="url"
              value={newLink.url}
              onChange={e => setNewLink({ ...newLink, url: e.target.value })}
              placeholder={newLink.platform ? PLATFORM_META[newLink.platform]?.placeholder : 'https://...'}
              className="w-full px-3 py-2.5 bg-white/5 border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:border-sparq-lime/40 focus:outline-none transition-colors"
            />
            <div className="flex gap-2">
              <button
                onClick={addLink}
                disabled={!newLink.platform || !newLink.url}
                className="px-4 py-2 bg-sparq-lime text-sparq-charcoal text-sm font-bold rounded-lg hover:bg-sparq-lime-dark disabled:opacity-30 disabled:cursor-not-allowed transition-colors"
              >
                Save
              </button>
              <button
                onClick={() => setAddingLink(false)}
                className="px-4 py-2 text-gray-400 text-sm rounded-lg hover:bg-white/5 transition-colors"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Existing Links */}
        {links.length === 0 ? (
          <div className="text-center py-8">
            <p className="text-gray-500 text-sm">No links yet. Add your Hudl, socials, and recruiting profiles!</p>
            <div className="flex flex-wrap justify-center gap-2 mt-4">
              {suggested_links.slice(0, 4).map((p: string) => (
                <button
                  key={p}
                  onClick={() => { setAddingLink(true); setNewLink({ platform: p, url: '' }) }}
                  className="px-3 py-1.5 text-xs bg-white/5 border border-white/10 text-gray-400 rounded-full hover:bg-white/10 hover:text-white transition-colors"
                >
                  {PLATFORM_META[p]?.icon} Add {PLATFORM_META[p]?.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {links.map((link: any) => (
              <div key={link.id} className="flex items-center justify-between py-2.5 px-3 bg-black/20 border border-white/[0.06] rounded-xl">
                <div className="flex items-center gap-3 min-w-0">
                  <span className="text-lg flex-shrink-0">{PLATFORM_META[link.platform]?.icon || '🔗'}</span>
                  <div className="min-w-0">
                    <div className="font-medium text-sm text-white">
                      {PLATFORM_META[link.platform]?.label || link.platform}
                    </div>
                    <a href={link.url} target="_blank" rel="noopener" className="text-xs text-gray-500 hover:text-sparq-lime truncate block max-w-xs transition-colors">
                      {link.url}
                    </a>
                  </div>
                </div>
                <button
                  onClick={() => deleteLink(link.id)}
                  className="text-gray-600 hover:text-red-400 text-sm transition-colors ml-2 flex-shrink-0"
                >
                  ✕
                </button>
              </div>
            ))}
            {suggested_links.length > 0 && (
              <div className="pt-2 flex flex-wrap gap-2">
                {suggested_links.slice(0, 3).map((p: string) => (
                  <button
                    key={p}
                    onClick={() => { setAddingLink(true); setNewLink({ platform: p, url: '' }) }}
                    className="px-2.5 py-1 text-xs bg-white/5 border border-white/10 text-gray-500 rounded-full hover:bg-white/10 hover:text-gray-300 transition-colors"
                  >
                    + {PLATFORM_META[p]?.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* ===== RECENT CHATS ===== */}
      {recent_chats.length > 1 && (
        <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 sm:p-6">
          <div className="flex items-center gap-3 mb-4">
            <div className="w-8 h-8 rounded-lg bg-white/5 border border-white/10 flex items-center justify-center flex-shrink-0">
              <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm1-12a1 1 0 10-2 0v4a1 1 0 00.293.707l2.828 2.829a1 1 0 101.415-1.415l-2.536-2.535V6z" clipRule="evenodd"/>
              </svg>
            </div>
            <h3 className="font-bold text-white font-display">Recent Research</h3>
          </div>
          <div className="space-y-2">
            {recent_chats.map((chat: any) => (
              <button
                key={chat.id}
                onClick={() => onLoadChat(chat.id)}
                className="w-full flex items-center justify-between py-3 px-4 bg-black/20 border border-white/[0.06] rounded-xl hover:border-sparq-lime/30 active:bg-white/[0.04] transition-all text-left group"
              >
                <div className="min-w-0 flex-1 mr-3">
                  <div className="font-medium text-sm text-white truncate group-hover:text-sparq-lime transition-colors">
                    {chat.title}
                  </div>
                  <div className="text-[11px] text-gray-600 mt-0.5">
                    {chat.message_count} messages · {new Date(chat.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <svg className="w-4 h-4 text-gray-600 group-hover:text-sparq-lime transition-colors flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                  <path fillRule="evenodd" d="M7.293 14.707a1 1 0 010-1.414L10.586 10 7.293 6.707a1 1 0 011.414-1.414l4 4a1 1 0 010 1.414l-4 4a1 1 0 01-1.414 0z" clipRule="evenodd"/>
                </svg>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
