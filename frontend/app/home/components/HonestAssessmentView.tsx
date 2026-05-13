'use client'

import { useEffect, useState } from 'react'
import { Artifact } from './artifactStatus'

interface PercentileBar {
  label: string
  value?: number | string
  warn?: boolean
  note?: string
}

interface HonestAssessmentPayload {
  verdict?: string
  percentile_bars?: PercentileBar[]
  reality_check?: string
  plan_b?: string
  one_action?: string
}

interface Props {
  artifact: Artifact
  onPayloadChange?: (payload: Record<string, unknown>) => void
  editable?: boolean
}

function Bar({ item }: { item: PercentileBar }) {
  const numeric = typeof item.value === 'number' ? Math.max(0, Math.min(100, item.value)) : null
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
          {numeric !== null ? `${numeric}` : item.value !== undefined ? String(item.value) : ''}
          {numeric !== null ? <span className="text-gray-500"> / 100</span> : null}
        </span>
      </div>
      {numeric !== null && (
        <div className="h-1.5 bg-white/[0.06] rounded-full overflow-hidden">
          <div className={`h-full ${barColor} rounded-full transition-all`} style={{ width: `${numeric}%` }} />
        </div>
      )}
      {item.note && <div className="text-[11px] text-gray-500 italic">{item.note}</div>}
    </div>
  )
}

export default function HonestAssessmentView({ artifact, onPayloadChange, editable = true }: Props) {
  const initial = (artifact.payload || {}) as HonestAssessmentPayload
  const [verdict, setVerdict] = useState(initial.verdict ?? '')
  const [realityCheck, setRealityCheck] = useState(initial.reality_check ?? '')
  const [planB, setPlanB] = useState(initial.plan_b ?? '')
  const [oneAction, setOneAction] = useState(initial.one_action ?? '')

  useEffect(() => {
    setVerdict(initial.verdict ?? '')
    setRealityCheck(initial.reality_check ?? '')
    setPlanB(initial.plan_b ?? '')
    setOneAction(initial.one_action ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact.id])

  useEffect(() => {
    onPayloadChange?.({
      ...initial,
      verdict,
      reality_check: realityCheck,
      plan_b: planB,
      one_action: oneAction,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [verdict, realityCheck, planB, oneAction])

  const readOnlyClass = 'opacity-70 cursor-not-allowed'
  const textareaBase =
    'w-full bg-transparent border border-white/10 rounded-xl p-3 text-sm text-gray-200 leading-relaxed focus:border-sparq-lime/40 focus:outline-none'

  const bars = initial.percentile_bars ?? []

  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6 space-y-6">
      <div>
        <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1.5">Verdict</div>
        <textarea
          value={verdict}
          onChange={(e) => setVerdict(e.target.value)}
          readOnly={!editable}
          rows={Math.max(2, verdict.split('\n').length)}
          className={`w-full bg-transparent border-0 text-base font-bold text-white leading-snug focus:outline-none resize-none ${
            editable ? '' : readOnlyClass
          }`}
        />
      </div>

      {bars.length > 0 && (
        <div>
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-3">Where you stand</div>
          <div className="space-y-3">
            {bars.map((item, i) => (
              <Bar key={i} item={item} />
            ))}
          </div>
        </div>
      )}

      <div className="grid md:grid-cols-2 gap-4">
        <div>
          <div className="text-[10px] uppercase tracking-wide text-amber-300/80 mb-1.5">Reality check</div>
          <textarea
            value={realityCheck}
            onChange={(e) => setRealityCheck(e.target.value)}
            readOnly={!editable}
            rows={Math.max(4, realityCheck.split('\n').length + 1)}
            className={`${textareaBase} ${editable ? '' : readOnlyClass}`}
          />
        </div>
        <div>
          <div className="text-[10px] uppercase tracking-wide text-sparq-lime/80 mb-1.5">Plan B</div>
          <textarea
            value={planB}
            onChange={(e) => setPlanB(e.target.value)}
            readOnly={!editable}
            rows={Math.max(4, planB.split('\n').length + 1)}
            className={`${textareaBase} ${editable ? '' : readOnlyClass}`}
          />
        </div>
      </div>

      <div className="bg-sparq-lime/10 border border-sparq-lime/30 rounded-xl p-4">
        <div className="text-[10px] uppercase tracking-wide text-sparq-lime mb-1.5">Do this next</div>
        <textarea
          value={oneAction}
          onChange={(e) => setOneAction(e.target.value)}
          readOnly={!editable}
          rows={Math.max(1, oneAction.split('\n').length)}
          className={`w-full bg-transparent border-0 text-base font-semibold text-white focus:outline-none resize-none ${
            editable ? '' : readOnlyClass
          }`}
        />
      </div>
    </div>
  )
}
