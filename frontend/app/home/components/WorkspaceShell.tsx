'use client'

import dynamic from 'next/dynamic'
import { useEffect, useRef, useState } from 'react'
import { usePathname } from 'next/navigation'
import CombineHelpProvider, { useCombineHelp } from './CombineHelpProvider'

const WorkspaceSidebar = dynamic(() => import('./WorkspaceSidebar'), { ssr: false })
const WorkspaceAIPanel = dynamic(() => import('./WorkspaceAIPanel'), { ssr: false })

// One instance of each panel: responsive visibility must not duplicate chat sessions.
export default function WorkspaceShell({ children }: { children: React.ReactNode }) {
  return <CombineHelpProvider><WorkspaceFrame>{children}</WorkspaceFrame></CombineHelpProvider>
}

function WorkspaceFrame({ children }: { children: React.ReactNode }) {
  const [panel, setPanel] = useState<'navigation' | 'help' | null>(null)
  const pathname = usePathname()
  const navigationButton = useRef<HTMLButtonElement>(null)
  const helpButton = useRef<HTMLButtonElement>(null)
  const combineHelp = useCombineHelp()
  useEffect(() => { setPanel(null) }, [pathname])
  useEffect(() => {
    if (!combineHelp?.openRequest) return
    setPanel('help')
  }, [combineHelp?.openRequest])
  useEffect(() => {
    if (panel !== 'help' || !combineHelp?.openRequest) return
    const frame = requestAnimationFrame(() => document.querySelector<HTMLElement>('#workspace-help h2')?.focus())
    return () => cancelAnimationFrame(frame)
  }, [panel, combineHelp?.openRequest])
  useEffect(() => {
    if (!panel) return
    const escape = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        setPanel(null)
        ;(panel === 'help' ? helpButton : navigationButton).current?.focus()
      }
    }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [panel])

  return (
    <div className="flex h-[100dvh] min-w-0 flex-col overflow-hidden bg-sparq-charcoal font-display text-white">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-4 py-2 lg:hidden">
        <span className="font-black text-sparq-lime">SPARQ</span>
        <div className="flex gap-2">
          <button ref={navigationButton} type="button" aria-expanded={panel === 'navigation'} aria-controls="workspace-navigation" onClick={() => setPanel(p => p === 'navigation' ? null : 'navigation')} className="min-h-11 rounded-lg border border-white/20 px-3 text-sm font-semibold">{panel === 'navigation' ? 'Close menu' : 'Menu'}</button>
          <button ref={helpButton} type="button" aria-expanded={panel === 'help'} aria-controls="workspace-help" onClick={() => { if (panel === 'help') setPanel(null); else if (combineHelp?.enabled) combineHelp.openHelp(); else setPanel('help') }} className="min-h-11 rounded-lg border border-white/20 px-3 text-sm font-semibold">{panel === 'help' ? 'Close help' : 'Ask SPARQ'}</button>
        </div>
      </header>
      <div className="flex min-h-0 min-w-0 flex-1">
        <div id="workspace-navigation" className={`${panel === 'navigation' ? 'block' : 'hidden'} min-w-0 w-full overflow-y-auto lg:block lg:w-auto lg:shrink-0 [&>aside]:w-full [&>aside]:min-h-full [&>aside]:h-auto lg:[&>aside]:w-[220px]`} onClick={e => { if ((e.target as HTMLElement).closest('a')) setPanel(null) }}>
          <WorkspaceSidebar />
        </div>
        <main id="workspace-main" className={`${panel ? 'hidden lg:block' : 'block'} min-w-0 flex-1 overflow-y-auto`}>{children}</main>
        <div id="workspace-help" aria-label="SPARQ help" className={`${panel === 'help' ? 'block' : 'hidden'} min-w-0 w-full overflow-hidden lg:block lg:w-[300px] lg:shrink-0 [&>div]:h-full [&>div]:w-full`}>
          <WorkspaceAIPanel />
        </div>
      </div>
    </div>
  )
}
