'use client'

import { useCallback, useEffect, useRef, useState } from 'react'
import { apiFetch } from '@/app/_lib/api'

export interface CareerGoal { text: string; destination: string | null; timeframe: string | null }
export interface CareerDraft {
  kind: 'summary' | 'introduction'
  text: string
  goal: string
  destination: string
  selected_evidence_ids: string[]
  selected_material_ids: string[]
  inputs_changed: boolean
}
export type WorkKind = 'goal_saved' | 'goal_removed' | 'featured_saved' | 'featured_removed' | 'draft_saved' | 'draft_removed'
export const workLabels: Record<WorkKind, string> = {
  goal_saved: 'Goal saved', goal_removed: 'Goal removed', featured_saved: 'Featured film chosen',
  featured_removed: 'Featured film removed', draft_saved: 'Draft saved', draft_removed: 'Draft removed',
}
export interface CareerWorkspace {
  state: 'ready'
  owner_scope: string
  link_revision: string
  version: number
  goal: CareerGoal | null
  featured_source_id: string | null
  draft: CareerDraft | null
  recent_work: { id: string; kind: WorkKind; at: string }[]
  updated_at: string | null
}
export type CareerChanges = Partial<Pick<CareerWorkspace, 'goal' | 'featured_source_id' | 'draft'>>
type WorkspaceError = { kind: 'conflict' | 'link' | 'unavailable' | 'invalid'; message: string }
const record = (v: unknown): v is Record<string, unknown> => !!v && typeof v === 'object' && !Array.isArray(v)
const text = (v: unknown, max: number): v is string => typeof v === 'string' && v.length <= max && !/[\u0000-\u0008\u000b\u000c\u000e-\u001f\u007f]/.test(v)
const nullable = (v: unknown, max: number) => v === null || text(v, max)
const date = (v: unknown): v is string => typeof v === 'string' && /^\d{4}-\d{2}-\d{2}T(?:[01]\d|2[0-3]):[0-5]\d:[0-5]\d(?:\.\d{1,6})?(?:Z|\+00:00)$/.test(v)
  && Number.isFinite(Date.parse(v)) && new Date(v).toISOString().slice(0, 10) === v.slice(0, 10)
const sourceId = (v: unknown, kind: 'metric' | 'material' | 'film') => {
  if (typeof v !== 'string') return false
  const pattern = kind === 'metric' ? /^metric-([1-9][0-9]{0,15})$/ : kind === 'film' ? /^film-([1-9][0-9]{0,15})$/ : /^(?:film-([1-9][0-9]{0,15})|submission-([1-9][0-9]{0,15})-[0-9a-f]{16})$/
  const match = pattern.exec(v)
  return !!match && Number.isSafeInteger(Number(match[1] || match[2]))
}
const ids = (v: unknown, max: number, kind: 'metric' | 'material') => Array.isArray(v) && v.length <= max && new Set(v).size === v.length && v.every(id => sourceId(id, kind))

export function readCareerWorkspace(value: unknown): CareerWorkspace {
  const invalid = () => new Error('Your saved work could not be confirmed.')
  if (!record(value) || value.state !== 'ready' || typeof value.link_revision !== 'string' || !/^[a-f0-9]{64}$/.test(value.link_revision)
    || typeof value.owner_scope !== 'string' || !/^[a-f0-9]{64}$/.test(value.owner_scope)
    || !Number.isSafeInteger(value.version) || Number(value.version) < 0 || Number(value.version) > 2147483647
    || !(value.updated_at === null || date(value.updated_at))
    || !(value.featured_source_id === null || sourceId(value.featured_source_id, 'film'))) throw invalid()
  if (value.goal !== null && (!record(value.goal) || !text(value.goal.text, 600) || !value.goal.text.trim() || !nullable(value.goal.destination, 200) || !nullable(value.goal.timeframe, 100))) throw invalid()
  if (value.draft !== null) {
    const d = value.draft
    if (!record(d) || !['summary', 'introduction'].includes(String(d.kind)) || !text(d.text, 20000)
      || !text(d.goal, 600) || !text(d.destination, 200) || !ids(d.selected_evidence_ids, 20, 'metric')
      || !ids(d.selected_material_ids, 30, 'material') || typeof d.inputs_changed !== 'boolean') throw invalid()
  }
  if (!Array.isArray(value.recent_work) || value.recent_work.length > 20 || !value.recent_work.every(item => record(item)
    && text(item.id, 120) && typeof item.kind === 'string' && Object.prototype.hasOwnProperty.call(workLabels, item.kind) && date(item.at)
    && new RegExp(`^[1-9][0-9]*:${item.kind}$`).test(item.id) && Number(item.id.split(':')[0]) <= Number(value.version))) throw invalid()
  if (new Set(value.recent_work.map(item => item.id)).size !== value.recent_work.length) throw invalid()
  return value as unknown as CareerWorkspace
}

// This hook stores only confirmed server state. The caller keeps authored edits
// separately so save failures, refreshes and competing tabs cannot replace them.
export function useCareerWorkspace(onScopeLost: () => void) {
  const [snapshot, setSnapshot] = useState<CareerWorkspace | null>(null)
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState<WorkspaceError | null>(null)
  const [blocked, setBlocked] = useState(false)
  const current = useRef<CareerWorkspace | null>(null)
  const active = useRef<AbortController | null>(null)
  const mounted = useRef(false)
  const locked = useRef(false)
  const scopeLost = useRef(onScopeLost)
  scopeLost.current = onScopeLost

  const loseScope = useCallback(() => {
    current.current = null; setSnapshot(null); scopeLost.current()
  }, [])

  const request = useCallback(async (changes?: CareerChanges): Promise<CareerWorkspace | null> => {
    if (!mounted.current || active.current || changes && (locked.current || !current.current)) return null
    const before = current.current
    const controller = new AbortController()
    active.current = controller
    if (changes) setSaving(true); else setLoading(true)
    setError(null)
    const timer = window.setTimeout(() => {
      controller.abort()
      if (mounted.current && active.current === controller) {
        active.current = null; locked.current = true; setBlocked(true); setLoading(false); setSaving(false)
        setError({ kind: 'unavailable', message: changes ? 'Your save could not be confirmed. Your edits are still here.' : 'Your saved work took too long to load. Try again in a moment.' })
      }
    }, 30000)
    controller.signal.addEventListener('abort', () => window.clearTimeout(timer), { once: true })
    try {
      const response = await apiFetch('/api/athlete/workspace', {
        method: changes ? 'PATCH' : 'GET', signal: controller.signal, cache: 'no-store',
        ...(changes ? { headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ link_revision: before!.link_revision, expected_version: before!.version, changes }) } : {}),
      })
      if (!mounted.current || controller.signal.aborted) return null
      if (!response.ok) {
        const body: unknown = await response.json().catch(() => null)
        if (!mounted.current || controller.signal.aborted) return null
        const code = record(body) ? body.code : null
        if (code === 'workspace_link_changed' || code === 'workspace_unlinked' || response.status === 401 || response.status === 403) {
          loseScope(); setError({ kind: 'link', message: 'Your profile connection changed. Reload your saved work to continue.' })
        } else if (code === 'workspace_conflict') {
          setError({ kind: 'conflict', message: 'Your saved work changed in another window.' })
        } else {
          setError({ kind: response.status === 400 || response.status === 422 ? 'invalid' : 'unavailable', message: changes ? 'Your save could not be confirmed. Your edits are still here.' : 'Your saved work is unavailable. Your GMTM profile is still yours.' })
        }
        locked.current = true; setBlocked(true)
        return null
      }
      const next = readCareerWorkspace(await response.json())
      if (!mounted.current || controller.signal.aborted) return null
      if (before && next.link_revision !== before.link_revision) loseScope()
      current.current = next; setSnapshot(next); locked.current = false; setBlocked(false)
      return next
    } catch {
      if (mounted.current && active.current === controller) {
        // A timed-out mutation may have committed. Re-read before another write.
        locked.current = true; setBlocked(true)
        setError({ kind: 'unavailable', message: changes ? 'Your save could not be confirmed. Your edits are still here.' : 'Your saved work could not be loaded. Try again in a moment.' })
      }
      return null
    } finally {
      window.clearTimeout(timer)
      if (active.current === controller) {
        active.current = null
        if (mounted.current) { setLoading(false); setSaving(false) }
      }
    }
  }, [loseScope])

  useEffect(() => {
    mounted.current = true; void request()
    return () => { mounted.current = false; active.current?.abort(); active.current = null }
  }, [request])
  const reload = useCallback(() => request(), [request])
  const save = useCallback((changes: CareerChanges) => request(changes), [request])
  const invalidateScope = useCallback(() => {
    active.current?.abort(); active.current = null
    loseScope(); locked.current = true; setBlocked(true); setLoading(false); setSaving(false)
    setError({ kind: 'link', message: 'Your profile connection changed. Reload your saved work to continue.' })
  }, [loseScope])
  return { snapshot, loading, saving, error, blocked, reload, save, invalidateScope }
}
