// V2 cowork canvas — artifact status & specialist metadata.
// Status colors live here so every surface (Inbox cards, viewer header, sidebar badges) stays consistent.

export type ArtifactState =
  | 'draft'
  | 'ready_for_review'
  | 'approved'
  | 'sent'
  | 'queued'
  | 'send_failed'
  | 'archived'
  | 'rejected'
  | 'iterating'

export type ArtifactType =
  | 'research_brief'
  | 'outreach_draft'
  | 'daily_digest'
  | 'honest_assessment'
  | 'film_breakdown'
  | 'plan_b_pathways'
  | 'compliance_alert'

export type SpecialistId =
  | 'scout'
  | 'drafter'
  | 'analyst'
  | 'watchdog'
  | 'film_analyst'

export interface StatusStyle {
  label: string
  className: string
}

// Amber 'honest' is intentional — makes the truth-teller signal visible at a glance.
export const STATUS_STYLES: Record<ArtifactState | 'honest', StatusStyle> = {
  draft: { label: 'Draft', className: 'bg-white/10 text-gray-300 border border-white/10' },
  ready_for_review: {
    label: 'Ready',
    className: 'bg-sparq-lime/20 text-sparq-lime border border-sparq-lime/30',
  },
  approved: { label: 'Approved', className: 'bg-emerald-500/20 text-emerald-300 border border-emerald-500/30' },
  sent: { label: 'Sent', className: 'bg-blue-500/20 text-blue-300 border border-blue-500/30' },
  queued: { label: 'Queued', className: 'bg-amber-500/15 text-amber-200 border border-amber-500/30' },
  send_failed: { label: 'Send Failed', className: 'bg-red-500/20 text-red-300 border border-red-500/30' },
  archived: { label: 'Archived', className: 'bg-white/5 text-gray-500 border border-white/10' },
  rejected: { label: 'Discarded', className: 'bg-red-500/10 text-red-300/70 border border-red-500/20' },
  iterating: {
    label: 'Iterating',
    className: 'bg-sparq-lime/10 text-sparq-lime border border-sparq-lime/20 animate-pulse',
  },
  honest: {
    label: 'Honest',
    className: 'bg-amber-500/20 text-amber-200 border border-amber-500/30',
  },
}

export function pillForArtifact(state: ArtifactState, type: ArtifactType): StatusStyle {
  // Honest assessments override the state pill — even when 'ready_for_review' they should read as 'Honest'.
  if (type === 'honest_assessment' && state === 'ready_for_review') return STATUS_STYLES.honest
  return STATUS_STYLES[state] ?? STATUS_STYLES.draft
}

export interface SpecialistMeta {
  id: SpecialistId
  name: string
  emoji: string
  blurb: string
}

export const SPECIALISTS: Record<SpecialistId, SpecialistMeta> = {
  scout: { id: 'scout', name: 'Scout', emoji: '🔍', blurb: 'Researches programs — rosters, depth charts, coaching staff' },
  drafter: { id: 'drafter', name: 'Drafter', emoji: '✉️', blurb: 'Composes outreach to coaches in your voice' },
  analyst: { id: 'analyst', name: 'Analyst', emoji: '📊', blurb: 'Honest assessment + Plan B pathways' },
  watchdog: { id: 'watchdog', name: 'Watchdog', emoji: '👁️', blurb: 'NCAA compliance + scam detection' },
  film_analyst: { id: 'film_analyst', name: 'Film', emoji: '🎬', blurb: 'Vision-based film breakdowns' },
}

export const ARTIFACT_TYPE_LABEL: Record<ArtifactType, string> = {
  research_brief: 'Research Brief',
  outreach_draft: 'Outreach Draft',
  daily_digest: 'Daily Digest',
  honest_assessment: 'Honest Assessment',
  film_breakdown: 'Film Breakdown',
  plan_b_pathways: 'Plan B Pathways',
  compliance_alert: 'Compliance Alert',
}

export const ARTIFACT_TYPE_ICON: Record<ArtifactType, string> = {
  research_brief: '🔍',
  outreach_draft: '✉️',
  daily_digest: '🗓️',
  honest_assessment: '📊',
  film_breakdown: '🎬',
  plan_b_pathways: '🧭',
  compliance_alert: '⚠️',
}

export interface Artifact {
  id: number
  clerk_id: string
  type: ArtifactType
  state: ArtifactState
  agent_id: SpecialistId | null
  parent_artifact_id: number | null
  title: string | null
  summary: string | null
  payload: Record<string, unknown>
  sources: Array<{ label: string; url?: string }>
  created_at: string | null
  updated_at: string | null
  actions?: Array<{ id: number; kind: string; performed_by?: string; performed_at: string }>
}
