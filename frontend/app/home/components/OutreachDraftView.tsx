'use client'

import { useEffect, useState } from 'react'
import { Artifact } from './artifactStatus'

interface OutreachPayload {
  to_name?: string
  to_email?: string
  school?: string
  subject?: string
  body?: string
  personalization_notes?: string[]
}

interface Props {
  artifact: Artifact
  onPayloadChange?: (payload: Record<string, unknown>) => void
  editable?: boolean
}

export default function OutreachDraftView({ artifact, onPayloadChange, editable = true }: Props) {
  const initial = (artifact.payload || {}) as OutreachPayload
  const [subject, setSubject] = useState(initial.subject ?? '')
  const [body, setBody] = useState(initial.body ?? '')
  const [toEmail, setToEmail] = useState(initial.to_email ?? '')

  // Re-sync if a parent iteration replaces the artifact in place.
  useEffect(() => {
    setSubject(initial.subject ?? '')
    setBody(initial.body ?? '')
    setToEmail(initial.to_email ?? '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact.id])

  useEffect(() => {
    onPayloadChange?.({
      ...initial,
      subject,
      body,
      to_email: toEmail,
    })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [subject, body, toEmail])

  const inputBase =
    'w-full bg-transparent border-0 border-b border-white/10 focus:border-sparq-lime/60 focus:outline-none text-white py-2'
  const readOnlyClass = 'opacity-70 cursor-not-allowed'

  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-6">
      <div className="space-y-3">
        <div className="grid grid-cols-[80px_1fr] items-center">
          <span className="text-xs uppercase tracking-wide text-gray-500">To</span>
          <input
            type="email"
            value={toEmail}
            onChange={(e) => setToEmail(e.target.value)}
            readOnly={!editable}
            className={`${inputBase} ${editable ? '' : readOnlyClass}`}
            placeholder="coach@school.edu"
          />
        </div>
        {initial.to_name && (
          <div className="grid grid-cols-[80px_1fr] items-center">
            <span className="text-xs uppercase tracking-wide text-gray-500">Coach</span>
            <span className="text-sm text-gray-300">
              {initial.to_name}
              {initial.school ? <span className="text-gray-500"> · {initial.school}</span> : null}
            </span>
          </div>
        )}
        <div className="grid grid-cols-[80px_1fr] items-center">
          <span className="text-xs uppercase tracking-wide text-gray-500">Subject</span>
          <input
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            readOnly={!editable}
            className={`${inputBase} ${editable ? '' : readOnlyClass}`}
          />
        </div>
      </div>

      <textarea
        value={body}
        onChange={(e) => setBody(e.target.value)}
        readOnly={!editable}
        rows={Math.max(8, body.split('\n').length + 1)}
        className={`mt-4 w-full bg-transparent border border-white/10 rounded-xl p-4 text-sm text-gray-100 leading-relaxed focus:border-sparq-lime/40 focus:outline-none ${
          editable ? '' : readOnlyClass
        }`}
      />

      {Array.isArray(initial.personalization_notes) && initial.personalization_notes.length > 0 && (
        <div className="mt-4 pt-4 border-t border-white/10">
          <div className="text-[10px] uppercase tracking-wide text-gray-500 mb-2">Drafter personalized this email using</div>
          <ul className="text-sm text-gray-300 space-y-1">
            {initial.personalization_notes.map((n, i) => (
              <li key={i} className="flex items-start gap-2">
                <span className="text-sparq-lime">•</span>
                <span>{n}</span>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  )
}
