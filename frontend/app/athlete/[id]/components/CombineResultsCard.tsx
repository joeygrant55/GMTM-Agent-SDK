'use client'

import { CombineResult, formatValue, percentileLine, rankLine } from './combineResults'

const TIER_STYLE: Record<string, string> = {
  'Official In-Person': 'bg-sparq-lime/10 text-sparq-lime border-sparq-lime/30',
  'Remote App-Captured': 'bg-amber-400/10 text-amber-300 border-amber-400/30',
}

export default function CombineResultsCard({ results }: { results: CombineResult[] }) {
  if (!results || results.length === 0) return null
  // Results arrive newest event first and may span several combines. Show the newest
  // event's drills; older combines are counted so the athlete knows they exist.
  const newestEventId = results[0].event_id
  const eventName = results[0].event_name
  const shown = results.filter(r => r.event_id === newestEventId)
  const olderEvents = new Set(results.filter(r => r.event_id !== newestEventId).map(r => r.event_id)).size

  return (
    <div className="bg-gradient-to-br from-sparq-lime/[0.10] via-white/[0.04] to-transparent border border-sparq-lime/30 rounded-2xl p-5 sm:p-6">
      <div className="flex items-start justify-between gap-3 mb-4">
        <div className="min-w-0">
          <div className="text-[10px] font-bold uppercase tracking-[0.2em] text-sparq-lime mb-1">Combine results</div>
          <h3 className="font-bold text-white font-display leading-tight truncate">{eventName}</h3>
        </div>
        <span className="text-[11px] text-gray-500 flex-shrink-0">
          {shown.length} drill{shown.length !== 1 ? 's' : ''}
          {olderEvents > 0 ? ` · ${olderEvents} older combine${olderEvents !== 1 ? 's' : ''}` : ''}
        </span>
      </div>

      <div className="divide-y divide-white/[0.06]">
        {shown.map((r, i) => {
          const rank = rankLine(r)
          const pct = percentileLine(r)
          const tierClass = TIER_STYLE[r.trust_tier] || TIER_STYLE['Remote App-Captured']
          return (
            <div key={`${r.event_id}-${r.drill}-${i}`} className="py-3 flex flex-col sm:flex-row sm:items-center gap-2 sm:gap-4">
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
        })}
      </div>

      <p className="text-[11px] text-gray-600 mt-3">
        Remote App-Captured results were self-recorded on video and are not verified in person.
      </p>
    </div>
  )
}
