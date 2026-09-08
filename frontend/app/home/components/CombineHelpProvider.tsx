'use client'

import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { useUser } from '@clerk/nextjs'
import { usePathname, useSearchParams } from 'next/navigation'
import { CurrentCombine } from './currentCombine'

interface CombineHelpContextValue {
  clerkId: string | null
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
  const { user, isLoaded } = useUser()
  const pathname = usePathname()
  const query = useSearchParams()
  const enabled = pathname === '/home' || pathname === '/home/inbox'
  const clerkId = isLoaded ? user?.id ?? null : null
  // Clear the entire help lifetime before another account/event can be rendered.
  const scope = enabled ? `combine:${query.get('event_id') ?? ''}` : 'recruiting'
  return <CombineHelpScope key={`${clerkId ?? 'signed-out'}:${scope}`} clerkId={clerkId} enabled={enabled}>{children}</CombineHelpScope>
}

function CombineHelpScope({ clerkId, enabled, children }: { clerkId: string | null; enabled: boolean; children: React.ReactNode }) {
  const [snapshot, setSnapshot] = useState<CurrentCombine | null>(null)
  const [taskId, setTaskId] = useState<number | null>(null)
  const [openRequest, setOpenRequest] = useState(0)
  const publishSnapshot = useCallback((next: CurrentCombine | null) => {
    if (next && next.clerk_id !== clerkId) return
    setSnapshot(next)
    setTaskId(previous => next?.activities.some(a => a.task_id === previous) ? previous : null)
  }, [clerkId])
  const openHelp = useCallback((requested: number | null = null) => {
    if (requested !== null && !snapshot?.activities.some(a => a.task_id === requested)) return
    setTaskId(requested)
    setOpenRequest(n => n + 1)
  }, [snapshot])
  const value = useMemo(() => ({ clerkId, enabled, snapshot, taskId, openRequest, publishSnapshot, openHelp }), [clerkId, enabled, snapshot, taskId, openRequest, publishSnapshot, openHelp])
  return <CombineHelpContext.Provider value={value}>{children}</CombineHelpContext.Provider>
}
