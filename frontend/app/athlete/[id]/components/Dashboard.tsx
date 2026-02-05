'use client'

import { useState, useEffect } from 'react'

interface DashboardProps {
  athleteId: string
  onStartChat: () => void
  onLoadChat: (conversationId: number) => void
  onViewReport: (reportId: number) => void
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

const REPORT_TYPE_META: Record<string, { label: string, icon: string, color: string }> = {
  college_fit: { label: 'College Fit', icon: '🏫', color: 'bg-blue-50 text-blue-700' },
  profile_analysis: { label: 'Profile Analysis', icon: '📊', color: 'bg-green-50 text-green-700' },
  camp_research: { label: 'Camp Research', icon: '🏕️', color: 'bg-orange-50 text-orange-700' },
  research: { label: 'Research', icon: '📋', color: 'bg-gray-50 text-gray-700' },
}

export default function Dashboard({ athleteId, onStartChat, onLoadChat, onViewReport }: DashboardProps) {
  const [data, setData] = useState<any>(null)
  const [reports, setReports] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [addingLink, setAddingLink] = useState(false)
  const [newLink, setNewLink] = useState({ platform: '', url: '' })

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

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
    // Refresh
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

  return (
    <div className="space-y-6">
      {/* Profile Card */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
          <div className="flex items-center gap-3 sm:gap-4">
            <div className="w-12 h-12 sm:w-16 sm:h-16 bg-sparq-charcoal rounded-full flex items-center justify-center flex-shrink-0">
              <span className="text-sparq-lime text-lg sm:text-2xl font-bold">
                {profile.first_name?.[0]}{profile.last_name?.[0]}
              </span>
            </div>
            <div className="min-w-0">
              <h2 className="text-xl sm:text-2xl font-bold text-gray-900 truncate">
                {profile.first_name} {profile.last_name}
              </h2>
              <p className="text-sm sm:text-base text-gray-600 truncate">
                {profile.position} • {profile.city}, {profile.state}
              </p>
              {offer_count > 0 && (
                <p className="text-sm text-sparq-lime-dark font-medium mt-1">
                  🎓 {offer_count} scholarship offer{offer_count !== 1 ? 's' : ''}
                </p>
              )}
            </div>
          </div>
          <div className="flex items-center gap-2 sm:flex-col sm:items-end sm:text-right">
            <div className="text-xs sm:text-sm text-gray-500">Profile</div>
            <div className="flex items-center gap-2 flex-1 sm:flex-initial">
              <div className="w-20 sm:w-24 h-2 bg-gray-200 rounded-full overflow-hidden">
                <div
                  className="h-full bg-sparq-lime rounded-full transition-all"
                  style={{ width: `${completeness}%` }}
                />
              </div>
              <span className="text-sm font-medium text-gray-700">{completeness}%</span>
            </div>
          </div>
        </div>

        {/* Key Metrics */}
        {metrics.length > 0 && (
          <div className="mt-4 grid grid-cols-2 sm:grid-cols-4 gap-2 sm:gap-3">
            {metrics.slice(0, 8).map((m: any) => (
              <div key={m.title} className="bg-gray-50 rounded-lg px-2 sm:px-3 py-2">
                <div className="text-xs text-gray-500 truncate">{m.title}</div>
                <div className="font-semibold text-gray-900 text-sm sm:text-base truncate">
                  {m.value} {m.unit || ''}
                  {m.verified ? ' ✅' : ''}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
        <button
          onClick={onStartChat}
          className="bg-sparq-charcoal text-white rounded-xl p-4 sm:p-5 text-left hover:bg-sparq-charcoal-light transition-colors active:scale-[0.98]"
        >
          <div className="text-sparq-lime text-xl sm:text-2xl mb-2">⚡</div>
          <div className="font-semibold text-base sm:text-lg">New Research</div>
          <div className="text-gray-400 text-sm mt-1">
            Ask your agent about colleges, camps, recruiting strategies
          </div>
        </button>
        {recent_chats.length > 0 && (
          <button
            onClick={() => onLoadChat(recent_chats[0].id)}
            className="bg-white border border-gray-200 rounded-xl p-4 sm:p-5 text-left hover:border-sparq-lime transition-colors active:scale-[0.98]"
          >
            <div className="text-xl sm:text-2xl mb-2">💬</div>
            <div className="font-semibold text-base sm:text-lg text-gray-900">Continue Last Chat</div>
            <div className="text-gray-500 text-sm mt-1 truncate">
              {recent_chats[0].title}
            </div>
          </button>
        )}
      </div>

      {/* Saved Reports */}
      {reports.length > 0 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
          <h3 className="font-semibold text-gray-900 mb-3">📋 Your Reports</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 sm:gap-3">
            {reports.map((report: any) => {
              const meta = REPORT_TYPE_META[report.report_type] || REPORT_TYPE_META.research
              return (
                <button
                  key={report.id}
                  onClick={() => onViewReport(report.id)}
                  className="text-left p-4 border border-gray-200 rounded-lg hover:border-sparq-lime transition-colors"
                >
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`px-2 py-0.5 text-xs font-medium rounded-full ${meta.color}`}>
                      {meta.icon} {meta.label}
                    </span>
                  </div>
                  <div className="font-medium text-sm text-gray-900 truncate mt-1">{report.title}</div>
                  <div className="text-xs text-gray-400 mt-1">
                    {new Date(report.created_at).toLocaleDateString()}
                  </div>
                  {report.summary && (
                    <p className="text-xs text-gray-500 mt-2 line-clamp-2">{report.summary}</p>
                  )}
                </button>
              )
            })}
          </div>
        </div>
      )}

      {/* Links Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-0 mb-4">
          <div>
            <h3 className="font-semibold text-gray-900">Your Links</h3>
            <p className="text-sm text-gray-500">Add your profiles so your agent can research deeper</p>
          </div>
          <button
            onClick={() => setAddingLink(!addingLink)}
            className="text-sm px-3 py-2 sm:py-1.5 bg-sparq-charcoal text-sparq-lime rounded-lg hover:bg-sparq-charcoal-light transition-colors self-start sm:self-auto"
          >
            + Add Link
          </button>
        </div>

        {/* Add Link Form */}
        {addingLink && (
          <div className="mb-4 p-4 bg-gray-50 rounded-lg space-y-3">
            <select
              value={newLink.platform}
              onChange={e => setNewLink({ ...newLink, platform: e.target.value })}
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
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
              className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm"
            />
            <div className="flex gap-2">
              <button
                onClick={addLink}
                disabled={!newLink.platform || !newLink.url}
                className="px-4 py-2 bg-sparq-charcoal text-white text-sm rounded-lg hover:bg-sparq-charcoal-light disabled:opacity-50"
              >
                Save
              </button>
              <button
                onClick={() => setAddingLink(false)}
                className="px-4 py-2 text-gray-600 text-sm rounded-lg hover:bg-gray-100"
              >
                Cancel
              </button>
            </div>
          </div>
        )}

        {/* Existing Links */}
        {links.length === 0 ? (
          <div className="text-center py-6">
            <p className="text-gray-400 text-sm">No links yet. Add your Hudl, socials, and recruiting profiles!</p>
            <div className="flex flex-wrap justify-center gap-2 mt-3">
              {suggested_links.slice(0, 4).map((p: string) => (
                <button
                  key={p}
                  onClick={() => { setAddingLink(true); setNewLink({ platform: p, url: '' }) }}
                  className="px-3 py-1 text-xs bg-gray-100 text-gray-600 rounded-full hover:bg-gray-200"
                >
                  {PLATFORM_META[p]?.icon} Add {PLATFORM_META[p]?.label}
                </button>
              ))}
            </div>
          </div>
        ) : (
          <div className="space-y-2">
            {links.map((link: any) => (
              <div key={link.id} className="flex items-center justify-between py-2 px-3 bg-gray-50 rounded-lg">
                <div className="flex items-center gap-3">
                  <span className="text-lg">{PLATFORM_META[link.platform]?.icon || '🔗'}</span>
                  <div>
                    <div className="font-medium text-sm text-gray-900">
                      {PLATFORM_META[link.platform]?.label || link.platform}
                    </div>
                    <a href={link.url} target="_blank" rel="noopener" className="text-xs text-gray-500 hover:text-sparq-charcoal truncate block max-w-xs">
                      {link.url}
                    </a>
                  </div>
                </div>
                <button
                  onClick={() => deleteLink(link.id)}
                  className="text-gray-400 hover:text-red-500 text-sm"
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
                    className="px-2 py-1 text-xs bg-gray-100 text-gray-500 rounded-full hover:bg-gray-200"
                  >
                    + {PLATFORM_META[p]?.label}
                  </button>
                ))}
              </div>
            )}
          </div>
        )}
      </div>

      {/* Recent Chats */}
      {recent_chats.length > 1 && (
        <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-6">
          <h3 className="font-semibold text-gray-900 mb-3">Recent Research</h3>
          <div className="space-y-2">
            {recent_chats.map((chat: any) => (
              <button
                key={chat.id}
                onClick={() => onLoadChat(chat.id)}
                className="w-full flex items-center justify-between py-3 sm:py-2 px-3 bg-gray-50 rounded-lg hover:bg-gray-100 active:bg-gray-200 transition-colors text-left"
              >
                <div className="min-w-0 flex-1 mr-2">
                  <div className="font-medium text-sm text-gray-900 truncate">{chat.title}</div>
                  <div className="text-xs text-gray-400">
                    {chat.message_count} messages • {new Date(chat.updated_at).toLocaleDateString()}
                  </div>
                </div>
                <span className="text-gray-400 flex-shrink-0">→</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
