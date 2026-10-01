'use client'

import { useEffect, useRef, useState } from 'react'
import Link from 'next/link'
import { usePathname, useSearchParams } from 'next/navigation'
import { useSparqSession } from '@/app/_lib/useSparqSession'
import SignOutButton from '@/components/SignOutButton'
import CombineHelpProvider, { useCombineHelp } from './CombineHelpProvider'
import CombineHelpPanel from './CombineHelpPanel'
import { supportedCombineEvent } from './currentCombine'

// The focused surface never mounts the legacy sidebar, inbox or recruiting panel.
export default function CombineWorkspaceShell({ children }: { children: React.ReactNode }) {
  return <CombineHelpProvider><CombineWorkspaceFrame>{children}</CombineWorkspaceFrame></CombineHelpProvider>
}

function CombineWorkspaceFrame({ children }: { children: React.ReactNode }) {
  const [panel, setPanel] = useState<'navigation' | 'help' | null>(null)
  const pathname = usePathname()
  const params = useSearchParams()
  const rawEvent = params.get('event_id')
  const eventId = rawEvent && /^\d+$/.test(rawEvent) ? supportedCombineEvent(Number(rawEvent)) : null
  const { user } = useSparqSession()
  const navigationButton = useRef<HTMLButtonElement>(null)
  const helpButton = useRef<HTMLButtonElement>(null)
  const helpHeading = useRef<HTMLDivElement>(null)
  const help = useCombineHelp()
  const nextMove = eventId ? `/home/inbox?event_id=${eventId}` : '/home/inbox'

  useEffect(() => { setPanel(null) }, [pathname, rawEvent])
  useEffect(() => {
    if (help?.openRequest) setPanel('help')
  }, [help?.openRequest])
  useEffect(() => {
    if (panel !== 'help') return
    const frame = requestAnimationFrame(() => helpHeading.current?.querySelector<HTMLElement>('h2')?.focus())
    return () => cancelAnimationFrame(frame)
  }, [panel, help?.openRequest])
  useEffect(() => {
    if (!panel) return
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape') return
      setPanel(null)
      ;(panel === 'help' ? helpButton : navigationButton).current?.focus()
    }
    window.addEventListener('keydown', escape)
    return () => window.removeEventListener('keydown', escape)
  }, [panel])

  return (
    <div className="flex h-[100dvh] min-w-0 flex-col overflow-hidden bg-sparq-charcoal font-display text-white">
      <header className="flex shrink-0 items-center justify-between gap-2 border-b border-white/10 px-4 py-2 lg:hidden">
        <span className="font-black text-sparq-lime">SPARQ</span>
        <div className="flex gap-2">
          <button ref={navigationButton} type="button" aria-expanded={panel === 'navigation'} aria-controls="combine-workspace-navigation" onClick={() => setPanel(value => value === 'navigation' ? null : 'navigation')} className="min-h-11 rounded-lg border border-white/20 px-3 text-sm font-semibold">{panel === 'navigation' ? 'Close menu' : 'Menu'}</button>
          <button ref={helpButton} type="button" aria-expanded={panel === 'help'} aria-controls="combine-workspace-help" onClick={() => { if (panel === 'help') setPanel(null); else help?.openHelp() }} className="min-h-11 rounded-lg border border-white/20 px-3 text-sm font-semibold">{panel === 'help' ? 'Close help' : 'Ask SPARQ'}</button>
        </div>
      </header>
      <div className="flex min-h-0 min-w-0 flex-1">
        <aside id="combine-workspace-navigation" className={`${panel === 'navigation' ? 'flex' : 'hidden'} min-w-0 w-full flex-col overflow-y-auto border-r border-white/10 p-4 lg:flex lg:w-[220px] lg:shrink-0`}>
          <div className="flex items-center gap-2">
            <img src="/sparq-logo.jpg" alt="SPARQ" className="h-8 w-8 rounded-md" />
            <span className="text-lg font-black text-sparq-lime">SPARQ</span>
          </div>
          <nav aria-label="Combine navigation" className="mt-8">
            <Link href={nextMove} aria-current="page" onClick={() => setPanel(null)} className="flex min-h-11 items-center rounded-lg bg-white/10 px-3 text-sm font-semibold">My next move</Link>
          </nav>
          <div className="mt-auto flex items-center gap-3 border-t border-white/10 pt-4">
            <SignOutButton />
            <span className="truncate text-sm text-gray-300">Athlete</span>
          </div>
        </aside>
        <main id="combine-workspace-main" className={`${panel ? 'hidden lg:block' : 'block'} min-w-0 flex-1 overflow-y-auto`}>{children}</main>
        <div ref={helpHeading} id="combine-workspace-help" aria-label="SPARQ combine help" className={`${panel === 'help' ? 'block' : 'hidden'} min-w-0 w-full overflow-hidden lg:block lg:w-[300px] lg:shrink-0 [&>div]:h-full [&>div]:w-full`}>
          <CombineHelpPanel />
        </div>
      </div>
    </div>
  )
}
