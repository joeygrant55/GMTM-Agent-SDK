'use client'

import { useState } from 'react'
import { CombineResult, formatValue, groupByEvent, percentileLine, rankLine } from './combineResults'

const TIER_STYLE: Record<string, string> = {
  'Official In-Person': 'bg-sparq-lime/10 text-sparq-lime border-sparq-lime/30',
  'Remote App-Captured': 'bg-amber-400/10 text-amber-300 border-amber-400/30',
}

function ResultRow({ r }: { r: CombineResult }) {
  const rank = rankLine(r)
  const pct = percentileLine(r)
  const tierClass = TIER_STYLE[r.trust_tier] || TIER_STYLE['Remote App-Captured']
  return (
    <div className="py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
      <div className="flex items-baseline gap-3 sm:w-[240px] flex-shrink-0">
        <span className="text-2xl font-black text-sparq-lime tabular-nums">{formatValue(r)}</span>
        <span className="text-sm font-medium text-white truncate">{r.drill}</span>
      </div>
      <div className="flex-1 min-w-0 text-xs text-gray-400 leading-relaxed">
        {rank && <div className="text-white/80">{rank}</div>}
        {pct && <div>{pct}</div>}
        {!rank && !pct && <div className="text-gray-600">No rank yet</div>}
      </div>
      <div className="flex items-center gap-2 flex-shrink-0">
        <span className={`px-2 py-0.5 text-[10px] font-bold uppercase tracking-wide rounded-full border ${tierClass}`}>
          {r.trust_tier}
        </span>
        {r.video_uri && (
          <a
            href={r.video_uri}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium text-white bg-white/5 border border-white/10 rounded-lg hover:border-sparq-lime/40 hover:text-sparq-lime transition-colors"
          >
            <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
            Watch
          </a>
        )}
      </div>
    </div>
  )
}

export default function CombineResultsCard({ results }: { results: CombineResult[] }) {
  // Backend order is newest event first; the first group starts open, the rest collapsed.
  const [openEventId, setOpenEventId] = useState<number | null>(null)
  if (!results || results.length === 0) return null
  const groups = groupByEvent(results)
  const activeId = openEventId ?? groups[0].event_id

  return (
    <div className="bg-gradient-to-br from-sparq-lime/[0.10] via-white/[0.04] to-transparent border border-sparq-lime/30 rounded-2xl p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3 mb-3">
        <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-sparq-lime">Combine results</div>
        <span className="text-[11px] text-gray-500 flex-shrink-0">
          {results.length} drill{results.length !== 1 ? 's' : ''}
          {groups.length > 1 ? ` · ${groups.length} events` : ''}
        </span>
      </div>

      <div className="space-y-2">
        {groups.map(g => {
          const open = g.event_id === activeId
          return (
            <div key={g.event_id} className={open ? '' : 'border border-white/[0.06] rounded-xl'}>
              <button
                type="button"
                onClick={() => setOpenEventId(g.event_id)}
                disabled={open}
                className={`w-full flex items-center justify-between gap-3 text-left ${
                  open ? 'cursor-default' : 'px-3 py-2.5 hover:bg-white/[0.03] rounded-xl transition-colors'
                }`}
              >
                <h3 className={`font-bold font-display leading-tight truncate ${open ? 'text-white' : 'text-white/70 text-sm'}`}>
                  {g.event_name}
                </h3>
                <span className="text-[11px] text-gray-500 flex-shrink-0">
                  {g.results.length} drill{g.results.length !== 1 ? 's' : ''}
                  {!open && ' · show'}
                </span>
              </button>
              {open && (
                <div className="divide-y divide-white/[0.06]">
                  {g.results.map((r, i) => (
                    <ResultRow key={`${r.event_id}-${r.drill}-${i}`} r={r} />
                  ))}
                </div>
              )}
            </div>
          )
        })}
      </div>

      <p className="text-[11px] text-gray-600 mt-3">
        Remote App-Captured results were self-recorded on video and are not verified in person.
      </p>
    </div>
  )
}
