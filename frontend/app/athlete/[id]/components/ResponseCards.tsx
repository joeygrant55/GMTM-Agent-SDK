'use client'

import { useState, useEffect } from 'react'

/* ═══════════════════════════════════════════════
   Interfaces
   ═══════════════════════════════════════════════ */

export interface CollegeMatchData {
  school: string
  matchPercent: number
  details: string[]
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
   CollegeMatchCard
   ═══════════════════════════════════════════════ */

export function CollegeMatchCard({
  data,
  index = 0,
}: {
  data: CollegeMatchData
  index?: number
}) {
  const [animated, setAnimated] = useState(false)
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    const t = setTimeout(() => setAnimated(true), 100 + index * 100)
    return () => clearTimeout(t)
  }, [index])

  const ratingColor =
    data.matchPercent >= 80
      ? 'bg-[#c8ff00]'
      : data.matchPercent >= 60
        ? 'bg-yellow-400'
        : 'bg-red-400'

  return (
    <div
      className="flex-shrink-0 w-[min(100%,320px)] snap-center bg-[#141414] border border-white/[0.06] rounded-xl p-4 transition-all duration-300 hover:border-[#c8ff00]/30 hover:-translate-y-0.5"
      style={{
        opacity: animated ? 1 : 0,
        transform: animated ? 'translateY(0)' : 'translateY(8px)',
        transition: `opacity 0.4s ease ${index * 100}ms, transform 0.4s ease ${index * 100}ms`,
      }}
    >
      {/* Hero: match % */}
      <div className="flex items-baseline gap-2 mb-2">
        <span className="text-3xl font-bold text-white font-display">
          {data.matchPercent}%
        </span>
        <span className="text-xs text-white/40 uppercase tracking-wider">match</span>
      </div>

      {/* Bar */}
      <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden mb-3">
        <div
          className={`h-full ${ratingColor} rounded-full transition-all duration-700 ease-out`}
          style={{ width: animated ? `${data.matchPercent}%` : '0%' }}
        />
      </div>

      {/* School name */}
      <h4 className="font-bold text-white text-lg font-display mb-2">{data.school}</h4>

      {/* Details */}
      {data.details.length > 0 && (
        <div className="space-y-1 mb-3">
          {data.details.slice(0, 3).map((d, i) => (
            <div key={i} className="flex items-start gap-1.5">
              <span className="text-[#c8ff00] text-xs mt-0.5">•</span>
              <span className="text-xs text-white/55 leading-snug">{d}</span>
            </div>
          ))}
        </div>
      )}

      {/* Action buttons */}
      <div className="flex gap-2 mt-auto pt-1">
        <button
          onClick={() => setSaved(!saved)}
          className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium transition-all ${
            saved
              ? 'bg-[#c8ff00]/20 text-[#c8ff00] border border-[#c8ff00]/30'
              : 'bg-white/[0.04] text-white/50 border border-white/[0.06] hover:border-[#c8ff00]/30 hover:text-[#c8ff00]'
          }`}
        >
          <svg className="w-3.5 h-3.5" fill={saved ? 'currentColor' : 'none'} stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4.318 6.318a4.5 4.5 0 000 6.364L12 20.364l7.682-7.682a4.5 4.5 0 00-6.364-6.364L12 7.636l-1.318-1.318a4.5 4.5 0 00-6.364 0z" />
          </svg>
          {saved ? 'Saved' : 'Save'}
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#c8ff00] text-[#0a0a0a] hover:bg-[#d4ff33] transition-colors">
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
          </svg>
          Email Coach
        </button>
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   CampCard
   ═══════════════════════════════════════════════ */

export function CampCard({ data }: { data: CampData }) {
  return (
    <div className="bg-[#141414] border border-white/[0.06] rounded-xl p-4 hover:border-[#c8ff00]/30 hover:-translate-y-0.5 transition-all duration-200">
      <div className="flex items-start gap-3">
        <div className="w-8 h-8 rounded-lg bg-[#c8ff00]/10 flex items-center justify-center flex-shrink-0">
          <svg className="w-4 h-4 text-[#c8ff00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
        </div>
        <div className="flex-1 min-w-0">
          <h4 className="font-semibold text-white text-sm">{data.name}</h4>
          <div className="flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
            {data.date && <span className="text-xs text-white/40">📅 {data.date}</span>}
            {data.location && <span className="text-xs text-white/40">📍 {data.location}</span>}
            {data.cost && <span className="text-xs text-[#c8ff00]">💰 {data.cost}</span>}
          </div>
        </div>
        {data.url ? (
          <a
            href={data.url}
            target="_blank"
            rel="noopener noreferrer"
            className="px-3 py-1.5 bg-[#c8ff00] text-[#0a0a0a] text-xs font-semibold rounded-lg hover:bg-[#d4ff33] transition-colors flex-shrink-0"
          >
            Learn More
          </a>
        ) : (
          <button className="px-3 py-1.5 border border-[#c8ff00]/30 text-[#c8ff00] text-xs font-medium rounded-lg hover:bg-[#c8ff00]/10 transition-colors flex-shrink-0">
            Learn More
          </button>
        )}
      </div>
    </div>
  )
}

/* ═══════════════════════════════════════════════
   EmailPreviewCard
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
    <div className="bg-[#141414] border border-white/[0.06] rounded-xl overflow-hidden hover:border-[#c8ff00]/30 transition-all duration-200">
      {/* Email header bar */}
      <div className="px-4 py-2.5 bg-white/[0.02] border-b border-white/[0.04] flex items-center gap-2">
        <svg className="w-4 h-4 text-[#c8ff00]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
        </svg>
        <span className="text-xs font-medium text-white/60">Email Draft</span>
      </div>

      <div className="p-4 space-y-2">
        <div className="text-xs">
          <span className="text-white/30">To: </span>
          <span className="text-white/70">{data.to}</span>
        </div>
        <div className="text-xs">
          <span className="text-white/30">Subject: </span>
          <span className="text-white/80 font-medium">{data.subject}</span>
        </div>
        <div className="h-px bg-white/[0.04] my-2" />
        <div className="text-xs text-white/55 leading-relaxed whitespace-pre-wrap max-h-40 overflow-y-auto">
          {data.body.length > 500 ? data.body.slice(0, 500) + '...' : data.body}
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 py-3 border-t border-white/[0.04] flex gap-2">
        <button
          onClick={handleCopy}
          className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-white/[0.04] text-white/50 border border-white/[0.06] hover:border-[#c8ff00]/30 hover:text-[#c8ff00] transition-all"
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
              Copy Email
            </>
          )}
        </button>
        <button className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-[#c8ff00] text-[#0a0a0a] hover:bg-[#d4ff33] transition-colors">
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
      ? { bar: 'bg-[#c8ff00]', text: 'text-[#c8ff00]' }
      : data.rating === 'average'
        ? { bar: 'bg-yellow-400', text: 'text-yellow-400' }
        : { bar: 'bg-red-400', text: 'text-red-400' }

  return (
    <div className="bg-[#141414] border border-white/[0.06] rounded-xl p-4 hover:border-[#c8ff00]/30 hover:-translate-y-0.5 transition-all duration-200">
      <div className="text-xs text-white/40 uppercase tracking-wider mb-1">{data.metric}</div>
      <div className={`text-2xl font-bold font-display ${color.text}`}>{data.value}</div>
      {data.comparison && (
        <div className="text-xs text-white/40 mt-1">{data.comparison}</div>
      )}
      {/* Mini bar */}
      <div className="h-1 bg-white/[0.06] rounded-full overflow-hidden mt-2">
        <div
          className={`h-full ${color.bar} rounded-full`}
          style={{
            width:
              data.rating === 'good' ? '85%' : data.rating === 'average' ? '55%' : '30%',
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
