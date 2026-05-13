'use client'

import { useEffect, useState } from 'react'
import { Artifact } from './artifactStatus'

interface ResearchBriefPayload {
  school?: string
  headline?: string
  body?: string
  next_actions?: string[]
}

interface Props {
  artifact: Artifact
  onPayloadChange?: (payload: Record<string, unknown>) => void
  editable?: boolean
}

export default function ResearchBriefView({ artifact, onPayloadChange, editable = true }: Props) {
  const initial = (artifact.payload || {}) as ResearchBriefPayload
  const [body, setBody] = useState(initial.body ?? '')
  const [nextActions, setNextActions] = useState<string[]>(initial.next_actions ?? [])

  useEffect(() => {
    setBody(initial.body ?? '')
    setNextActions(initial.next_actions ?? [])
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact.id])

  useEffect(() => {
    onPayloadChange?.({
      ...initial,
      body,
      next_actions: nextActions,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [body, nextActions])

  const readOnlyClass = 'opacity-70 cursor-not-allowed'

  const updateAction = (i: number, value: string) => {
    setNextActions((prev) => prev.map((a, idx) => (idx === i ? value : a)))
  }

  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
      {(initial.school || initial.headline) && (
        <div className="mb-5 pb-4 border-b border-white/10">
          {initial.school && (
            <div className="inline-flex items-center gap-1.5 text-[10px] uppercase tracking-wide text-sparq-lime bg-sparq-lime/10 border border-sparq-lime/20 rounded-full px-2 py-0.5 mb-2">
              {initial.school}
            </div>
          )}
          {initial.headline && (
            <div className="text-lg font-bold text-white leading-tight">{initial.headline}</div>
          )}
        </div>
      )}

      <div>
        <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-1.5">Brief</div>
        <textarea
          value={body}
          onChange={(e) => setBody(e.target.value)}
          readOnly={!editable}
          rows={Math.max(6, body.split('\n').length + 1)}
          className={`w-full bg-transparent border border-white/10 rounded-xl p-4 text-sm text-gray-100 leading-relaxed focus:border-sparq-lime/40 focus:outline-none ${
            editable ? '' : readOnlyClass
          }`}
        />
      </div>

      {nextActions.length > 0 && (
        <div className="mt-5">
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-2">Next actions</div>
          <ol className="space-y-2">
            {nextActions.map((action, i) => (
              <li key={i} className="flex items-start gap-3">
                <span className="shrink-0 w-5 h-5 rounded-full bg-sparq-lime/15 text-sparq-lime text-[11px] font-bold flex items-center justify-center mt-0.5">
                  {i + 1}
                </span>
                <input
                  value={action}
                  onChange={(e) => updateAction(i, e.target.value)}
                  readOnly={!editable}
                  className={`flex-1 bg-transparent border-0 border-b border-white/10 focus:border-sparq-lime/60 focus:outline-none text-sm text-gray-200 py-1 ${
                    editable ? '' : readOnlyClass
                  }`}
                />
              </li>
            ))}
          </ol>
        </div>
      )}
    </div>
  )
}
