'use client'

import { Artifact } from './artifactStatus'

// Lightweight renderer for artifact types whose dedicated views ship in P2/P3 (research_brief,
// honest_assessment, etc.). Keeps the V2 demo loop end-to-end without blocking on later phases.

interface LabeledValue {
  label: string
  value?: unknown
  warn?: boolean
  note?: string
}

function isLabeledValueArray(items: unknown[]): items is LabeledValue[] {
  return (
    items.length > 0 &&
    items.every((it) => typeof it === 'object' && it !== null && 'label' in (it as Record<string, unknown>))
  )
}

function PercentileBar({ item }: { item: LabeledValue }) {
  const value = typeof item.value === 'number' ? Math.max(0, Math.min(100, item.value)) : null
  const barColor = item.warn ? 'bg-amber-400' : 'bg-sparq-lime'
  const labelColor = item.warn ? 'text-amber-200' : 'text-gray-200'
  return (
    <div className="space-y-1">
      <div className="flex items-baseline justify-between">
        <span className={`text-sm font-medium ${labelColor}`}>
          {item.warn && <span className="mr-1">⚠️</span>}
          {item.label}
        </span>
        <span className="text-xs text-gray-400">
          {value !== null ? `${value}` : item.value !== undefined ? String(item.value) : ''}
          {value !== null ? <span className="text-gray-500"> / 100</span> : null}
        </span>
      </div>
      {value !== null && (
        <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
          <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${value}%` }} />
        </div>
      )}
      {item.note && <div className="text-[11px] text-gray-500 italic">{item.note}</div>}
    </div>
  )
}

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
      // All-objects array with a `label` key → labeled value list (with bars when value is numeric).
      if (isLabeledValueArray(value as unknown[])) {
        return (
          <div className="space-y-3">
            {(value as LabeledValue[]).map((item, i) => (
              <PercentileBar key={i} item={item} />
            ))}
          </div>
        )
      }
      // Strings / primitives → bullet list.
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
