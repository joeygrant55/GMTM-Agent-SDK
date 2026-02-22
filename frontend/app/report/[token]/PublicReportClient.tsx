'use client'

import { useState, useEffect } from 'react'
import Link from 'next/link'

interface PublicReport {
  id: number
  report_type: string
  title: string
  content: string
  summary: string
  created_at: string
  first_name: string
  last_name: string
  position: string
  sport: string
  graduation_year: number
  city: string
  state: string
}

const REPORT_TYPE_META: Record<string, { label: string; icon: string }> = {
  college_fit: { label: 'College Fit Report', icon: '🏫' },
  profile_analysis: { label: 'Profile Analysis', icon: '📊' },
  camp_research: { label: 'Camp Research', icon: '🏕️' },
  school_deep_dive: { label: 'School Deep Dive', icon: '🔍' },
  action_plan: { label: 'Action Plan', icon: '✅' },
  research: { label: 'Research Report', icon: '📋' },
}

// ── Markdown → HTML formatter (matches ReportView.tsx) ────────────────────────
function formatInline(text: string) {
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/(https?:\/\/[^\s<]+)/g, '<a href="$1" target="_blank" rel="noopener" class="text-sparq-lime underline">$1</a>')
}

function formatReportContent(content: string): string {
  const lines = content.split('\n')
  let html = ''
  let inTable = false
  let tableHeaders: string[] = []
  let tableRows: string[][] = []

  const flushTable = () => {
    if (tableHeaders.length === 0) return ''
    let t = '<div class="overflow-x-auto my-4"><table class="min-w-full text-sm border border-white/10 rounded-lg overflow-hidden">'
    t += '<thead class="bg-white/5"><tr>'
    tableHeaders.forEach(h => {
      t += `<th class="px-4 py-2.5 text-left font-semibold text-sparq-lime border-b border-white/10">${formatInline(h)}</th>`
    })
    t += '</tr></thead><tbody>'
    tableRows.forEach((row, idx) => {
      const bg = idx % 2 === 0 ? 'bg-transparent' : 'bg-white/[0.02]'
      t += `<tr class="${bg}">`
      row.forEach(cell => {
        t += `<td class="px-4 py-2.5 border-b border-white/5 text-gray-300">${formatInline(cell)}</td>`
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
      html += `<h4 class="font-semibold text-white mt-5 mb-2 text-base">${formatInline(trimmed.slice(5))}</h4>`
    } else if (trimmed.startsWith('### ')) {
      html += `<h3 class="font-semibold text-gray-100 mt-6 mb-2 text-lg">${formatInline(trimmed.slice(4))}</h3>`
    } else if (trimmed.startsWith('## ')) {
      html += `<h2 class="font-bold text-white mt-8 mb-3 text-xl border-b border-white/10 pb-2">${formatInline(trimmed.slice(3))}</h2>`
    } else if (trimmed.startsWith('# ')) {
      html += `<h1 class="font-bold text-white mt-6 mb-4 text-2xl">${formatInline(trimmed.slice(2))}</h1>`
    } else if (trimmed === '---') {
      html += '<hr class="my-6 border-white/10">'
    } else if (trimmed.startsWith('- ')) {
      html += `<div class="flex gap-2 ml-3 my-1"><span class="text-sparq-lime mt-0.5">•</span><span class="text-gray-300">${formatInline(trimmed.slice(2))}</span></div>`
    } else if (trimmed === '') {
      html += '<div class="h-3"></div>'
    } else {
      html += `<p class="my-2 text-gray-300 leading-relaxed">${formatInline(trimmed)}</p>`
    }
  }

  if (inTable || tableHeaders.length > 0) html += flushTable()
  return html
}

export default function PublicReportClient({ token }: { token: string }) {
  const [report, setReport] = useState<PublicReport | null>(null)
  const [loading, setLoading] = useState(true)
  const [notFound, setNotFound] = useState(false)
  const [copied, setCopied] = useState(false)

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://sparq-agent-backend.up.railway.app'

  useEffect(() => {
    fetch(`${backendUrl}/api/reports/public/${token}`)
      .then(r => {
        if (!r.ok) throw new Error('not found')
        return r.json()
      })
      .then(data => { setReport(data); setLoading(false) })
      .catch(() => { setNotFound(true); setLoading(false) })
  }, [token])

  const handleCopyLink = () => {
    navigator.clipboard.writeText(window.location.href)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-sparq-lime" />
      </div>
    )
  }

  if (notFound || !report) {
    return (
      <div className="min-h-screen bg-[#0a0a0a] flex items-center justify-center px-4">
        <div className="text-center max-w-md">
          <div className="w-16 h-16 mx-auto mb-6 rounded-2xl bg-[#141414] border border-white/10 flex items-center justify-center">
            <svg className="w-8 h-8 text-white/30" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.172 16.172a4 4 0 015.656 0M9 10h.01M15 10h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
            </svg>
          </div>
          <h2 className="text-2xl font-bold text-white mb-2">Report Not Found</h2>
          <p className="text-gray-500 mb-8">This link may have expired or be invalid.</p>
          <Link href="/" className="inline-flex items-center gap-2 px-6 py-3 bg-sparq-lime text-sparq-charcoal font-bold rounded-xl hover:bg-sparq-lime-dark transition-all">
            Go to SPARQ Agent →
          </Link>
        </div>
      </div>
    )
  }

  const meta = REPORT_TYPE_META[report.report_type] || REPORT_TYPE_META.research
  const athleteName = [report.first_name, report.last_name].filter(Boolean).join(' ')
  const athleteInfo = [
    report.position,
    report.graduation_year ? `Class of ${report.graduation_year}` : null,
    [report.city, report.state].filter(Boolean).join(', ') || null,
  ].filter(Boolean).join(' · ')

  return (
    <div className="min-h-screen bg-[#0a0a0a]">
      {/* Nav */}
      <nav className="border-b border-white/[0.06] sticky top-0 z-10 bg-[#0a0a0a]/95 backdrop-blur-sm">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-3 flex items-center justify-between gap-3">
          <Link href="/" className="flex items-center gap-2.5 flex-shrink-0">
            <div className="w-7 h-7 rounded-lg bg-[#141414] border border-white/10 flex items-center justify-center">
              <span className="text-sparq-lime font-black text-xs">S</span>
            </div>
            <span className="text-white font-bold text-sm hidden sm:block">SPARQ Agent</span>
          </Link>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyLink}
              className="flex items-center gap-1.5 px-3 py-1.5 bg-white/5 border border-white/10 text-gray-400 text-sm rounded-lg hover:bg-white/10 hover:text-white transition-all"
            >
              {copied ? (
                <>
                  <svg className="w-3.5 h-3.5 text-sparq-lime" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                  <span className="text-sparq-lime">Copied!</span>
                </>
              ) : (
                <>
                  <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935-2.186 2.25 2.25 0 0 0-3.935 2.186Zm0-12.814a2.25 2.25 0 1 0 3.933 2.185 2.25 2.25 0 0 0-3.933-2.185Z" />
                  </svg>
                  Copy link
                </>
              )}
            </button>

            <Link
              href="/sign-up"
              className="px-4 py-1.5 bg-sparq-lime text-sparq-charcoal font-bold text-sm rounded-lg hover:bg-sparq-lime-dark transition-all"
            >
              Get My Report →
            </Link>
          </div>
        </div>
      </nav>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-8 sm:py-12">
        {/* Athlete header */}
        <div className="flex items-start gap-4 mb-8">
          <div className="w-14 h-14 sm:w-16 sm:h-16 bg-gradient-to-br from-sparq-lime/30 to-sparq-lime/10 rounded-2xl flex items-center justify-center flex-shrink-0 border border-sparq-lime/20">
            <span className="text-sparq-lime font-black text-xl sm:text-2xl">
              {report.first_name?.[0]}{report.last_name?.[0]}
            </span>
          </div>
          <div>
            <h1 className="text-2xl sm:text-3xl font-black text-white leading-tight">{athleteName}</h1>
            {athleteInfo && <p className="text-gray-400 text-sm mt-1">{athleteInfo}</p>}
            <div className="flex items-center gap-2 mt-2.5">
              <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/5 border border-white/10 text-gray-400 text-xs font-medium rounded-full">
                {meta.icon} {meta.label}
              </span>
              <span className="text-gray-600 text-xs">
                {new Date(report.created_at).toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' })}
              </span>
            </div>
          </div>
        </div>

        {/* Report document */}
        <div className="bg-[#111111] border border-white/[0.08] rounded-2xl overflow-hidden">
          {/* Report title bar */}
          <div className="border-b border-white/[0.06] px-6 sm:px-10 py-5">
            <h2 className="text-lg sm:text-xl font-bold text-white">{report.title}</h2>
            {report.summary && (
              <p className="text-gray-500 text-sm mt-1 leading-relaxed">{report.summary}</p>
            )}
          </div>

          {/* Report content */}
          <div className="px-6 sm:px-10 py-8">
            <div
              dangerouslySetInnerHTML={{ __html: formatReportContent(report.content) }}
            />
          </div>
        </div>

        {/* Footer CTA */}
        <div className="mt-10 mb-4 bg-gradient-to-b from-[#111] to-[#0d0d0d] border border-sparq-lime/20 rounded-2xl px-6 py-10 text-center relative overflow-hidden">
          <div className="absolute -top-16 -right-16 w-48 h-48 rounded-full bg-sparq-lime/5 blur-3xl pointer-events-none" />
          <div className="relative">
            <div className="text-sparq-lime text-xs font-bold uppercase tracking-wider mb-3">
              ⚡ Powered by SPARQ Agent
            </div>
            <h3 className="text-2xl sm:text-3xl font-black text-white mb-3 leading-tight">
              This report took SPARQ Agent <span className="text-sparq-lime">30 seconds.</span>
            </h3>
            <p className="text-gray-500 text-base mb-8 max-w-lg mx-auto">
              College recruiters charge $5,000+ for this level of analysis. SPARQ does it instantly, for free.
            </p>
            <Link
              href="/sign-up"
              className="inline-flex items-center gap-2 px-8 py-4 bg-sparq-lime text-sparq-charcoal text-base font-black rounded-xl hover:bg-sparq-lime-dark transition-all hover:scale-105 shadow-lg shadow-sparq-lime/20"
            >
              Generate My Report →
            </Link>
          </div>
        </div>
      </main>
    </div>
  )
}
