'use client'

import { useState, useEffect, useRef } from 'react'

interface ShareCardProps {
  athleteId: string
  name: string
  sport?: string
  position?: string
  rating?: number
  stats?: string[]
  topMatch?: string
}

export default function ShareCard({
  athleteId,
  name,
  sport = 'Football',
  position = 'ATH',
  rating = 0,
  stats = [],
  topMatch = '',
}: ShareCardProps) {
  const [visible, setVisible] = useState(false)
  const [copied, setCopied] = useState(false)
  const cardRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const t = setTimeout(() => setVisible(true), 100)
    return () => clearTimeout(t)
  }, [])

  const shareUrl = `https://sparq-agent.vercel.app/athlete/${athleteId}?share=true`
  const ogParams = new URLSearchParams({
    name,
    sport,
    position,
    rating: String(rating),
    ...(stats[0] ? { stat1: stats[0] } : {}),
    ...(stats[1] ? { stat2: stats[1] } : {}),
    ...(stats[2] ? { stat3: stats[2] } : {}),
    ...(stats[3] ? { stat4: stats[3] } : {}),
    ...(topMatch ? { match: topMatch } : {}),
  })
  const ogUrl = `https://sparq-agent.vercel.app/api/og/athlete?${ogParams.toString()}`

  const initials = name.split(' ').map(w => w[0]).join('').slice(0, 2).toUpperCase()

  const handleShare = async () => {
    if (navigator.share) {
      try {
        await navigator.share({ title: `${name} — SPARQ Profile`, url: shareUrl })
      } catch { /* user cancelled */ }
    } else {
      await navigator.clipboard.writeText(shareUrl)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    }
  }

  const handleDownload = async () => {
    try {
      const res = await fetch(ogUrl)
      const blob = await res.blob()
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${name.replace(/\s+/g, '-').toLowerCase()}-sparq-card.png`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      console.error('Download failed:', err)
    }
  }

  return (
    <div
      ref={cardRef}
      className={`transition-all duration-700 ease-out ${
        visible ? 'opacity-100 scale-100' : 'opacity-0 scale-95'
      }`}
    >
      {/* Card */}
      <div className="relative overflow-hidden rounded-2xl border border-white/10 bg-gradient-to-br from-[#141414] to-[#0a0a0a]">
        {/* Glow effects */}
        <div className="absolute -top-24 -right-24 w-72 h-72 rounded-full bg-[#c8ff00]/5 blur-3xl pointer-events-none" />
        <div className="absolute -bottom-20 -left-20 w-56 h-56 rounded-full bg-[#c8ff00]/3 blur-3xl pointer-events-none" />

        <div className="relative p-6 sm:p-8">
          <div className="flex flex-col sm:flex-row items-center gap-6">
            {/* Left — info */}
            <div className="flex-1 text-center sm:text-left">
              <div className="inline-flex px-3 py-1 bg-[#c8ff00]/10 border border-[#c8ff00]/20 rounded-full text-[#c8ff00] text-xs font-bold uppercase tracking-wider mb-3">
                {sport} · {position}
              </div>
              <h2 className="text-3xl sm:text-4xl font-black text-white leading-tight tracking-tight">
                {name}
              </h2>

              {stats.length > 0 && (
                <div className="flex flex-wrap gap-2 mt-4 justify-center sm:justify-start">
                  {stats.map((stat, i) => (
                    <span
                      key={i}
                      className="px-3 py-1.5 bg-white/5 border border-white/8 rounded-lg text-gray-300 text-sm font-medium"
                    >
                      {stat}
                    </span>
                  ))}
                </div>
              )}

              {topMatch && (
                <p className="mt-3 text-gray-500 text-sm">
                  Top Match: <span className="text-[#c8ff00] font-bold">{topMatch}</span>
                </p>
              )}
            </div>

            {/* Right — SPARQ Rating */}
            <div className="flex flex-col items-center flex-shrink-0">
              <div className="relative w-36 h-36 sm:w-44 sm:h-44 rounded-full bg-gradient-to-br from-[#c8ff00]/12 to-[#c8ff00]/3 border-2 border-[#c8ff00]/30 flex items-center justify-center">
                <div className="absolute inset-[-12px] rounded-full bg-[#c8ff00]/8 blur-xl pointer-events-none" />
                <div className="relative text-center">
                  <div className="text-[10px] font-bold text-gray-500 uppercase tracking-widest">SPARQ</div>
                  <div className="text-5xl sm:text-6xl font-black text-[#c8ff00] leading-none">{rating || '—'}</div>
                  <div className="text-[10px] font-semibold text-gray-600 mt-1">RATING</div>
                </div>
              </div>
              <div className="mt-3 w-10 h-10 rounded-lg bg-[#c8ff00]/12 border border-[#c8ff00]/25 flex items-center justify-center">
                <span className="text-[#c8ff00] text-sm font-black">{initials}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Bottom bar */}
        <div className="relative border-t border-white/5 px-6 py-3 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <div className="w-5 h-5 rounded bg-[#c8ff00] flex items-center justify-center">
              <span className="text-black text-[10px] font-black">S</span>
            </div>
            <span className="text-gray-600 text-xs">Powered by SPARQ</span>
          </div>
          <span className="text-gray-700 text-xs">sparq-agent.vercel.app</span>
        </div>
      </div>

      {/* Action Buttons */}
      <div className="flex gap-3 mt-4">
        <button
          onClick={handleShare}
          className="flex-1 flex items-center justify-center gap-2 px-5 py-3 bg-[#c8ff00] text-black font-bold text-sm rounded-xl hover:bg-[#b8ef00] transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M7.217 10.907a2.25 2.25 0 1 0 0 2.186m0-2.186c.18.324.283.696.283 1.093s-.103.77-.283 1.093m0-2.186 9.566-5.314m-9.566 7.5 9.566 5.314m0 0a2.25 2.25 0 1 0 3.935-2.186 2.25 2.25 0 0 0-3.935 2.186Zm0-12.814a2.25 2.25 0 1 0 3.933 2.185 2.25 2.25 0 0 0-3.933-2.185Z" />
          </svg>
          {copied ? 'Link Copied!' : 'Share My Profile'}
        </button>
        <button
          onClick={handleDownload}
          className="px-5 py-3 bg-white/5 border border-white/10 text-gray-300 font-bold text-sm rounded-xl hover:bg-white/10 transition-all hover:scale-[1.02] active:scale-[0.98]"
        >
          <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24" strokeWidth={2.5}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 0 0 5.25 21h13.5A2.25 2.25 0 0 0 21 18.75V16.5M16.5 12 12 16.5m0 0L7.5 12m4.5 4.5V3" />
          </svg>
        </button>
      </div>
    </div>
  )
}
