'use client'

import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import { usePathname, useSearchParams } from 'next/navigation'
import { CurrentCombine } from './currentCombine'

interface CombineHelpContextValue {
  ownerId: string | null
  enabled: boolean
  snapshot: CurrentCombine | null
  taskId: number | null
  openRequest: number
  publishSnapshot: (snapshot: CurrentCombine | null) => void
  openHelp: (taskId?: number | null) => void
}

const CombineHelpContext = createContext<CombineHelpContextValue | null>(null)
export const useCombineHelp = () => useContext(CombineHelpContext)

export default function CombineHelpProvider({ children }: { children: React.ReactNode }) {
  const { user, isLoaded } = useSparqSession()
  const pathname = usePathname()
  const query = useSearchParams()
  const enabled = pathname === '/home' || pathname === '/home/inbox'
  const ownerId = isLoaded ? user?.id ?? null : null
  // Clear the entire help lifetime before another account/event can be rendered.
  const scope = enabled ? `combine:${query.get('event_id') ?? ''}` : 'recruiting'
  return <CombineHelpScope key={`${ownerId ?? 'signed-out'}:${scope}`} ownerId={ownerId} enabled={enabled}>{children}</CombineHelpScope>
}

function CombineHelpScope({ ownerId, enabled, children }: { ownerId: string | null; enabled: boolean; children: React.ReactNode }) {
  const [snapshot, setSnapshot] = useState<CurrentCombine | null>(null)
  const [taskId, setTaskId] = useState<number | null>(null)
  const [openRequest, setOpenRequest] = useState(0)
  const publishSnapshot = useCallback((next: CurrentCombine | null) => {
    if (next && next.clerk_id !== ownerId) return
    setSnapshot(next)
    setTaskId(previous => next?.activities.some(a => a.task_id === previous) ? previous : null)
  }, [ownerId])
  const openHelp = useCallback((requested: number | null = null) => {
    if (requested !== null && !snapshot?.activities.some(a => a.task_id === requested)) return
    setTaskId(requested)
    setOpenRequest(n => n + 1)
  }, [snapshot])
  const value = useMemo(() => ({ ownerId, enabled, snapshot, taskId, openRequest, publishSnapshot, openHelp }), [ownerId, enabled, snapshot, taskId, openRequest, publishSnapshot, openHelp])
  return <CombineHelpContext.Provider value={value}>{children}</CombineHelpContext.Provider>
}
