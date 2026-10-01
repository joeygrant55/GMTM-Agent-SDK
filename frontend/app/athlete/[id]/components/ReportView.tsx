'use client'

import { apiFetch } from '@/app/_lib/api'

import { useState, useEffect, useCallback } from 'react'
import SafeMarkdown from '@/components/SafeMarkdown'

interface ReportViewProps {
  athleteId: string
  reportId: number
  onBack: () => void
}

const REPORT_TYPE_META: Record<string, { label: string, icon: string, color: string }> = {
  college_fit: { label: 'College Fit Report', icon: '🏫', color: 'bg-blue-50 text-blue-700' },
  profile_analysis: { label: 'Profile Analysis', icon: '📊', color: 'bg-green-50 text-green-700' },
  camp_research: { label: 'Camp Research', icon: '🏕️', color: 'bg-orange-50 text-orange-700' },
  school_deep_dive: { label: 'School Deep Dive', icon: '🔍', color: 'bg-purple-50 text-purple-700' },
  action_plan: { label: 'Action Plan', icon: '✅', color: 'bg-emerald-50 text-emerald-700' },
  research: { label: 'Research', icon: '📋', color: 'bg-gray-50 text-gray-700' },
}

export default function ReportView({ athleteId, reportId, onBack }: ReportViewProps) {
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const [copied, setCopied] = useState(false)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://focused-essence-production-9809.up.railway.app'

  useEffect(() => {
    apiFetch(`${backendUrl}/api/reports/${athleteId}/${reportId}`)
      .then(r => r.json())
      .then(d => { setReport(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [reportId])

  const handleShare = useCallback(async () => {
    try {
      const res = await apiFetch(`${backendUrl}/api/reports/${athleteId}/${reportId}/share-token`)
      if (!res.ok) throw new Error('failed')
      const { url } = await res.json()
      await navigator.clipboard.writeText(url)
    } catch {
      await navigator.clipboard.writeText(window.location.href)
    }
    setCopied(true)
    setTimeout(() => setCopied(false), 2500)
  }, [athleteId, reportId, backendUrl])

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sparq-lime" /></div>
  }

  if (!report) return null

  const meta = REPORT_TYPE_META[report.report_type] || REPORT_TYPE_META.research

  return (
    <div className="max-w-4xl mx-auto">
      {/* Report Header */}
      <div className="flex items-center justify-between gap-3 mb-6">
        <div className="flex items-center gap-3">
          <button onClick={onBack} className="text-gray-400 hover:text-gray-300 text-sm transition-colors">← Back</button>
          <span className={`px-2 py-1 text-xs font-medium rounded-full ${meta.color}`}>{meta.icon} {meta.label}</span>
        </div>
        <button
          onClick={handleShare}
          className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 text-gray-400 text-sm rounded-lg hover:bg-sparq-lime/10 hover:border-sparq-lime/30 hover:text-sparq-lime transition-all"
        >
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5 text-sparq-lime" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
              </svg>
              <span className="text-sparq-lime text-xs">Copied!</span>
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935-2.186 2.25 2.25 0 0 0-3.935 2.186Zm0-12.814a2.25 2.25 0 1 0 3.933 2.185 2.25 2.25 0 0 0-3.933-2.185Z" />
              </svg>
              <span className="text-xs">Share report</span>
            </>
          )}
        </button>
      </div>

      {/* Report Document */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-4 sm:p-8 lg:p-12">
        <div className="mb-6 sm:mb-8">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 mb-2">{report.title}</h1>
          <p className="text-sm text-gray-500">
            Generated {new Date(report.created_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>

        {/* Report Content - beautifully formatted */}
        <div className="prose prose-gray max-w-none">
          <SafeMarkdown content={report.content} light />
        </div>
      </div>
    </div>
  )
}
