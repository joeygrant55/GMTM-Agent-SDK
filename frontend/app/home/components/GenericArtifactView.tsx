'use client'

import { Artifact } from './artifactStatus'

// Lightweight renderer for artifact types whose dedicated views ship in P2/P3 (research_brief,
// honest_assessment, etc.). Keeps the V2 demo loop end-to-end without blocking on later phases.

export default function GenericArtifactView({ artifact }: { artifact: Artifact }) {
  const payload = (artifact.payload || {}) as Record<string, unknown>

  const renderValue = (key: string, value: unknown) => {
    if (value === null || value === undefined) return null
    if (typeof value === 'string') {
      return <p className="text-sm text-gray-200 whitespace-pre-wrap leading-relaxed">{value}</p>
    }
    if (typeof value === 'number' || typeof value === 'boolean') {
      return <span className="text-sm text-gray-200">{String(value)}</span>
    }
    if (Array.isArray(value)) {
      return (
        <ul className="text-sm text-gray-200 space-y-1">
          {value.map((item, i) => (
            <li key={i} className="flex items-start gap-2">
              <span className="text-sparq-lime">•</span>
              <span>{typeof item === 'string' ? item : JSON.stringify(item)}</span>
            </li>
          ))}
        </ul>
      )
    }
    if (typeof value === 'object') {
      return (
        <pre className="text-xs text-gray-300 bg-black/30 border border-white/5 rounded-lg p-3 overflow-x-auto">
          {JSON.stringify(value, null, 2)}
        </pre>
      )
    }
    return null
  }

  const friendlyKey = (k: string) =>
    k.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())

  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6 space-y-5">
      {Object.entries(payload).map(([key, value]) => (
        <div key={key}>
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1.5">{friendlyKey(key)}</div>
          {renderValue(key, value)}
        </div>
      ))}
    </div>
  )
}
