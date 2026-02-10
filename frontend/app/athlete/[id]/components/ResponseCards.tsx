'use client'

import { useState, useEffect } from 'react'

/* ═══════════════════════════════════════════════
   Interfaces
   ═══════════════════════════════════════════════ */

export interface CollegeMatchData {
  school: string
  matchPercent: number
  details: string[]
  conference?: string
  scholarshipChance?: string
  rosterNeed?: string
  coach?: string
  coachTitle?: string
  schemeFit?: string
}

export interface CampData {
  name: string
  date?: string
  location?: string
  cost?: string
  url?: string
}

export interface EmailPreviewData {
  to: string
  subject: string
  body: string
}

export interface StatData {
  metric: string
  value: string
  comparison?: string
  rating: 'good' | 'average' | 'needs-work'
}

export interface ActionOption {
  number: number
  text: string
}

/* ═══════════════════════════════════════════════
   School Color Map
   ═══════════════════════════════════════════════ */

const SCHOOL_COLORS: Record<string, string> = {
  'TCU': '#4D1979', 'Baylor': '#154734', 'Arkansas': '#9D2235',
  'Oklahoma State': '#FF6600', 'Oklahoma St': '#FF6600',
  'Texas Tech': '#CC0000', 'Houston': '#C8102E', 'Alabama': '#9E1B32',
  'LSU': '#461D7C', 'Georgia': '#BA0C2F', 'Ohio State': '#BB0000',
  'Michigan': '#00274C', 'Florida': '#0021A5', 'Texas': '#BF5700',
  'Texas A&M': '#500000', 'Auburn': '#0C2340', 'Tennessee': '#FF8200',
  'Oregon': '#154733', 'USC': '#990000', 'Penn State': '#041E42',
  'Clemson': '#F56600', 'Notre Dame': '#0C2340', 'Miami': '#F47321',
  'Florida State': '#782F40', 'Wisconsin': '#C5050C', 'Iowa': '#FFCD00',
  'Nebraska': '#E41C38', 'Stanford': '#8C1515', 'UCLA': '#2D68C4',
  'Washington': '#4B2E83', 'Colorado': '#CFB87C', 'Arizona': '#CC0033',
  'Arizona State': '#8C1D40', 'Utah': '#CC0000', 'Kentucky': '#0033A0',
  'Mississippi State': '#660000', 'Ole Miss': '#CE1126', 'South Carolina': '#73000A',
  'Missouri': '#F1B82D', 'Vanderbilt': '#866D4B', 'Duke': '#003087',
  'North Carolina': '#7BAFD4', 'NC State': '#CC0000', 'Virginia': '#232D4B',
  'Virginia Tech': '#660000', 'Wake Forest': '#9E7E38', 'Pittsburgh': '#003594',
  'Syracuse': '#D44500', 'Boston College': '#98002E', 'Louisville': '#AD0000',
  'SMU': '#0033A0', 'Cal': '#003262', 'Kansas': '#0051BA',
  'Kansas State': '#512888', 'Iowa State': '#C8102E', 'West Virginia': '#002855',
  'UCF': '#BA9B37', 'Cincinnati': '#E00122', 'BYU': '#002E5D',
}

function getSchoolColor(name: string): string {
  // Try exact match first, then partial
  if (SCHOOL_COLORS[name]) return SCHOOL_COLORS[name]
  for (const [key, color] of Object.entries(SCHOOL_COLORS)) {
    if (name.toLowerCase().includes(key.toLowerCase()) || key.toLowerCase().includes(name.toLowerCase())) {
      return color
    }
  }
  return '#c8ff00' // fallback to lime
}

function getSchoolAbbrev(name: string): string {
  // Common abbreviations
  const abbrevs: Record<string, string> = {
    'TCU': 'TCU', 'LSU': 'LSU', 'USC': 'USC', 'UCLA': 'UCLA', 'UCF': 'UCF',
    'BYU': 'BYU', 'SMU': 'SMU', 'NC State': 'NCS', 'Ole Miss': 'OLE',
  }
  if (abbrevs[name]) return abbrevs[name]
  // Take first 3 chars of significant words
  const words = name.replace(/University|of|the|College/gi, '').trim().split(/\s+/)
  if (words.length === 1) return words[0].slice(0, 3).toUpperCase()
  return words.map(w => w[0]).join('').toUpperCase().slice(0, 3)
}

/* ═══════════════════════════════════════════════
   CollegeMatchCard — /demo-style expandable
   ═══════════════════════════════════════════════ */

export function CollegeMatchCard({
  data,
  index = 0,
}: {
  data: CollegeMatchData
  index?: number
}) {
  const [animated, setAnimated] = useState(false)
  const [expanded, setExpanded] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 100 + index * 150)
    return () => clearTimeout(t)
  }, [index])

  const color = getSchoolColor(data.school)
  const abbrev = getSchoolAbbrev(data.school)

  const chanceColor =
    data.matchPercent >= 85 ? 'text-green-400' :
    data.matchPercent >= 70 ? 'text-yellow-400' :
    'text-orange-400'

  const chanceLabel =
    data.matchPercent >= 85 ? 'High' :
    data.matchPercent >= 70 ? 'Medium-High' :
    data.matchPercent >= 55 ? 'Medium' : 'Developing'

  return (
    <div
      className="transition-all duration-500"
      style={{
        opacity: animated ? 1 : 0,
        transform: animated ? 'translateY(0)' : 'translateY(8px)',
        transitionDelay: `${index * 150}ms`,
      }}
    >
      <div
        onClick={() => setExpanded(!expanded)}
        className={`bg-white/[0.04] border rounded-2xl overflow-hidden cursor-pointer transition-all duration-300 hover:bg-white/[0.06] ${
          expanded ? 'border-[#c8ff00]/40 ring-1 ring-[#c8ff00]/10' : 'border-white/[0.08]'
        }`}
      >
        <div className="p-4 sm:p-5">
          <div className="flex items-center gap-4">
            {/* School Badge */}
            <div
              className="w-12 h-12 rounded-xl flex items-center justify-center font-black text-white text-xs flex-shrink-0 shadow-lg"
              style={{ backgroundColor: color }}
            >
              {abbrev}
            </div>

            {/* Info */}
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-white font-bold text-base">{data.school}</span>
                {data.conference && (
                  <span className="px-2 py-0.5 bg-white/5 rounded text-[10px] text-gray-400 font-medium">
                    {data.conference}
                  </span>
                )}
              </div>
              <p className="text-gray-500 text-xs mt-0.5 truncate">
                {data.rosterNeed || (data.details[0] && data.details[0].length < 60 ? data.details[0] : '')}
              </p>
            </div>

            {/* Score */}
            <div className="text-right flex-shrink-0">
              <div className="text-3xl font-black text-[#c8ff00] leading-none">{data.matchPercent}%</div>
              <div className={`text-[10px] font-semibold mt-0.5 ${chanceColor}`}>
                {data.scholarshipChance || chanceLabel}
              </div>
            </div>
          </div>

          {/* Match bar */}
          <div className="mt-3 h-1.5 bg-white/5 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full bg-gradient-to-r from-[#c8ff00] to-[#d4ff33] transition-all duration-1000 ease-out"
              style={{ width: animated ? `${data.matchPercent}%` : '0%' }}
            />
          </div>

          {/* Top reason always visible */}
          {data.details.length > 0 && (
            <div className="mt-3 flex items-start gap-2 text-xs">
              <span className="text-[#c8ff00] mt-px flex-shrink-0">✓</span>
              <span className="text-gray-400">{data.details[0]}</span>
            </div>
          )}
        </div>

        {/* Expanded Details */}
        {expanded && (
          <div className="border-t border-white/5 p-4 sm:p-5 bg-black/20 space-y-4">
            {(data.coach || data.coachTitle) && (
              <div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Position Coach</div>
                {data.coach && <div className="text-white font-semibold text-sm">{data.coach}</div>}
                {data.coachTitle && <div className="text-gray-500 text-xs">{data.coachTitle}</div>}
              </div>
            )}

            {data.schemeFit && (
              <div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1.5">Scheme Fit</div>
                <div className="text-gray-300 text-xs leading-relaxed">{data.schemeFit}</div>
              </div>
            )}

            {data.details.length > 0 && (
              <div>
                <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-2">Why You Match</div>
                <div className="space-y-1.5">
                  {data.details.map((r, j) => (
                    <div key={j} className="flex items-start gap-2 text-xs">
                      <span className="text-[#c8ff00] mt-px flex-shrink-0">✓</span>
                      <span className="text-gray-400">{r}</span>
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Action row */}
            <div className="flex gap-2 pt-1">
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#c8ff00] text-[#0a0a0a] hover:bg-[#d4ff33] transition-colors">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
                </svg>
                Email Coach
              </button>
              <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] text-white/50 border border-white/[0.06] hover:border-[#c8ff00]/30 hover:text-[#c8ff00] transition-all">
                <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 5a2 2 0 012-2h10a2 2 0 012 2v16l-7-3.5L5 21V5z" />
                </svg>
                Save
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   CampCard
   ═══════════════════════════════════════════════ */

export function CampCard({ data }: { data: CampData }) {
  return (
    <div className="bg-white/[0.04] border border-white/[0.08] rounded-2xl p-4 hover:border-[#c8ff00]/30 transition-all duration-200">
      <div className="flex items-start gap-3">
        <div className="w-10 h-10 rounded-xl bg-[#c8ff00]/10 border border-[#c8ff00]/20 flex items-center justify-center flex-shrink-0">
          <svg className="w-5 h-5 text-[#c8ff00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-bold text-white text-sm">{data.name}</h4>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1.5">
            {data.date && (
              <span className="flex items-center gap-1 text-xs text-gray-400">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/></svg>
                {data.date}
              </span>
            )}
            {data.location && (
              <span className="flex items-center gap-1 text-xs text-gray-400">
                <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z"/></svg>
                {data.location}
              </span>
            )}
            {data.cost && (
              <span className="text-xs text-[#c8ff00] font-medium">{data.cost}</span>
            )}
          </div>
        </div>
        {data.url ? (
          <a
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-[#c8ff00] text-[#0a0a0a] text-xs font-bold rounded-lg hover:bg-[#d4ff33] transition-colors flex-shrink-0"
          >
            Details →
          </a>
        ) : (
          <button className="px-3 py-1.5 border border-[#c8ff00]/30 text-[#c8ff00] text-xs font-medium rounded-lg hover:bg-[#c8ff00]/10 transition-colors flex-shrink-0">
            Details →
          </button>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   EmailPreviewCard — /demo style with typewriter feel
   ═══════════════════════════════════════════════ */

export function EmailPreviewCard({ data }: { data: EmailPreviewData }) {
  const [copied, setCopied] = useState(false)

  const fullText = `To: ${data.to}\nSubject: ${data.subject}\n\n${data.body}`

  const handleCopy = () => {
    navigator.clipboard.writeText(fullText)
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <div className="bg-gradient-to-br from-white/[0.06] to-white/[0.02] border border-white/10 rounded-2xl overflow-hidden">
      {/* Email header */}
      <div className="px-5 py-3 border-b border-white/10 flex items-center gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#c8ff00]/10 border border-[#c8ff00]/20 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-[#c8ff00]" fill="currentColor" viewBox="0 0 20 20">
            <path d="M2.003 5.884L10 9.882l7.997-3.998A2 2 0 0016 4H4a2 2 0 00-1.997 1.884z"/>
            <path d="M18 8.118l-8 4-8-4V14a2 2 0 002 2h12a2 2 0 002-2V8.118z"/>
          </svg>
        </div>
        <div>
          <h3 className="text-white font-bold text-sm">Draft Outreach</h3>
          <p className="text-gray-500 text-[11px]">To: {data.to}</p>
        </div>
      </div>

      <div className="p-5">
        <div className="mb-3">
          <span className="text-[10px] text-gray-500 uppercase tracking-wider">Subject</span>
          <div className="text-white font-medium text-sm mt-0.5">{data.subject}</div>
        </div>
        <div className="bg-black/30 rounded-xl p-4 text-sm text-gray-300 font-mono leading-relaxed whitespace-pre-wrap max-h-60 overflow-y-auto">
          {data.body}
        </div>
      </div>

      {/* Actions */}
      <div className="px-5 py-3 border-t border-white/[0.06] flex flex-wrap gap-2">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-bold bg-[#c8ff00] text-[#0a0a0a] hover:bg-[#d4ff33] transition-colors"
        >
          {copied ? (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
              </svg>
              Copied!
            </>
          ) : (
            <>
              <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
              </svg>
              Copy to Clipboard
            </>
          )}
        </button>
        <button className="flex items-center gap-1.5 px-4 py-2 rounded-lg text-xs font-medium bg-white/5 border border-white/10 text-gray-300 hover:bg-white/10 transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
          </svg>
          Edit &amp; Send
        </button>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   StatCard
   ═══════════════════════════════════════════════ */

export function StatCard({ data }: { data: StatData }) {
  const color =
    data.rating === 'good'
      ? { bar: 'bg-[#c8ff00]', text: 'text-[#c8ff00]', bg: 'bg-[#c8ff00]/10 border-[#c8ff00]/20' }
      : data.rating === 'average'
        ? { bar: 'bg-yellow-400', text: 'text-yellow-400', bg: 'bg-yellow-400/10 border-yellow-400/20' }
        : { bar: 'bg-red-400', text: 'text-red-400', bg: 'bg-red-400/10 border-red-400/20' }

  return (
    <div className={`rounded-xl px-3 py-3 border ${color.bg}`}>
      <div className="text-[10px] text-gray-500 uppercase tracking-wider mb-1">{data.metric}</div>
      <div className={`text-xl font-black font-display ${color.text}`}>{data.value}</div>
      {data.comparison && (
        <div className="text-[11px] text-gray-400 mt-1">{data.comparison}</div>
      )}
      {/* Mini bar */}
      <div className="h-1 bg-white/[0.06] rounded-full overflow-hidden mt-2">
        <div
          className={`h-full ${color.bar} rounded-full transition-all duration-700`}
          style={{
            width: data.rating === 'good' ? '85%' : data.rating === 'average' ? '55%' : '30%',
          }}
        />
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   ActionButtons
   ═══════════════════════════════════════════════ */

export function ActionButtons({
  options,
  onAction,
}: {
  options: ActionOption[]
  onAction: (text: string) => void
}) {
  return (
    <div className="flex flex-wrap gap-2 mt-2">
      {options.map((opt) => (
        <button
          key={opt.number}
          onClick={() => onAction(opt.text)}
          className="px-4 py-2 rounded-full text-xs font-medium border border-[#c8ff00]/30 text-[#c8ff00] hover:bg-[#c8ff00]/10 active:bg-[#c8ff00] active:text-[#0a0a0a] transition-all"
        >
          {opt.text}
        </button>
      ))}
    </div>
  )
}
