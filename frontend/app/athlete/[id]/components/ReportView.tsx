'use client'

import { useState, useEffect } from 'react'

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

const formatInline = (text: string) => {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener" class="text-blue-600 underline">$1</a>')
}

const formatReportContent = (content: string) => {
  const lines = content.split('\n')
  let html = ''
  let inTable = false
  let tableHeaders: string[] = []
  let tableRows: string[][] = []

  const flushTable = () => {
    if (tableHeaders.length === 0) return ''
    let t = '<div class="overflow-x-auto my-4"><table class="min-w-full text-sm border border-gray-200 rounded-lg overflow-hidden">'
    t += '<thead class="bg-gray-900"><tr>'
    tableHeaders.forEach(h => {
      t += `<th class="px-4 py-2.5 text-left font-semibold text-sparq-lime border-b border-gray-700">${formatInline(h)}</th>`
    })
    t += '</tr></thead><tbody>'
    tableRows.forEach((row, idx) => {
      const bg = idx % 2 === 0 ? 'bg-white' : 'bg-gray-50'
      t += `<tr class="${bg}">`
      row.forEach(cell => {
        t += `<td class="px-4 py-2.5 border-b border-gray-100 text-gray-700">${formatInline(cell)}</td>`
      })
      t += '</tr>'
    })
    t += '</tbody></table></div>'
    tableHeaders = []
    tableRows = []
    inTable = false
    return t
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      const cells = trimmed.slice(1, -1).split('|').map(c => c.trim())
      if (cells.every(c => /^[-:\s]+$/.test(c))) { inTable = true; continue }
      if (!inTable && tableHeaders.length === 0) { tableHeaders = cells; continue }
      if (inTable) { tableRows.push(cells); continue }
    } else {
      if (inTable || tableHeaders.length > 0) html += flushTable()
    }

    if (trimmed.startsWith('#### ')) {
      html += `<h4 class="font-semibold text-gray-800 mt-5 mb-2 text-base">${formatInline(trimmed.slice(5))}</h4>`
    } else if (trimmed.startsWith('### ')) {
      html += `<h3 class="font-semibold text-gray-900 mt-6 mb-2 text-lg">${formatInline(trimmed.slice(4))}</h3>`
    } else if (trimmed.startsWith('## ')) {
      html += `<h2 class="font-bold text-gray-900 mt-8 mb-3 text-xl border-b border-gray-200 pb-2">${formatInline(trimmed.slice(3))}</h2>`
    } else if (trimmed.startsWith('# ')) {
      html += `<h1 class="font-bold text-gray-900 mt-6 mb-4 text-2xl">${formatInline(trimmed.slice(2))}</h1>`
    } else if (trimmed === '---') {
      html += '<hr class="my-6 border-gray-200">'
    } else if (trimmed.startsWith('- ')) {
      html += `<div class="flex gap-2 ml-3 my-1"><span class="text-sparq-lime-dark mt-0.5">•</span><span class="text-gray-700">${formatInline(trimmed.slice(2))}</span></div>`
    } else if (trimmed === '') {
      html += '<div class="h-3"></div>'
    } else {
      html += `<p class="my-2 text-gray-700 leading-relaxed">${formatInline(trimmed)}</p>`
    }
  }

  if (inTable || tableHeaders.length > 0) html += flushTable()
  return html
}

export default function ReportView({ athleteId, reportId, onBack }: ReportViewProps) {
  const [report, setReport] = useState<any>(null)
  const [loading, setLoading] = useState(true)
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'

  useEffect(() => {
    fetch(`${backendUrl}/api/reports/${athleteId}/${reportId}`)
      .then(r => r.json())
      .then(d => { setReport(d); setLoading(false) })
      .catch(() => setLoading(false))
  }, [reportId])

  if (loading) {
    return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sparq-lime" /></div>
  }

  if (!report) return null

  const meta = REPORT_TYPE_META[report.report_type] || REPORT_TYPE_META.research

  return (
    <div className="max-w-4xl mx-auto">
      {/* Report Header */}
      <div className="flex items-center gap-3 mb-6">
        <button onClick={onBack} className="text-gray-400 hover:text-gray-600 text-sm">← Back</button>
        <span className={`px-2 py-1 text-xs font-medium rounded-full ${meta.color}`}>{meta.icon} {meta.label}</span>
      </div>

      {/* Report Document */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-8 sm:p-12">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900 mb-2">{report.title}</h1>
          <p className="text-sm text-gray-500">
            Generated {new Date(report.created_at).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </p>
        </div>

        {/* Report Content - beautifully formatted */}
        <div 
          className="prose prose-gray max-w-none"
          dangerouslySetInnerHTML={{ __html: formatReportContent(report.content) }}
        />
      </div>
    </div>
  )
}
