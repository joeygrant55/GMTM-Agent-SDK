'use client'

import CombineResultsCard from '@/app/athlete/[id]/components/CombineResultsCard'
import { readCombineResults } from '@/app/athlete/[id]/components/combineResults'

export interface AthleteHomeProfile {
  clerk_id: string
  combine_results?: unknown
  hudl_url?: string | null
}

export default function AthleteStartingPoint({ profile }: { profile: AthleteHomeProfile }) {
  const results = readCombineResults(profile)

  return (
    <div className="space-y-5">
      <section aria-labelledby="your-evidence-title" className="space-y-3">
        <div>
          <h2 id="your-evidence-title" className="text-lg font-bold">Your performance evidence</h2>
          <p className="mt-1 text-sm text-gray-400">Results returned from your linked GMTM record, with event context and capture method.</p>
        </div>
        {results.length > 0 ? (
          <CombineResultsCard results={results} />
        ) : (
          <div className="rounded-2xl border border-white/10 bg-white/[0.04] p-5">
            <p className="font-semibold text-gray-200">No combine results returned for this profile</p>
            <p className="mt-2 text-sm text-gray-400">Your combine activities and submissions are shown separately above. You can work on them before numeric results appear here.</p>
          </div>
        )}
      </section>
    </div>
  )
}
