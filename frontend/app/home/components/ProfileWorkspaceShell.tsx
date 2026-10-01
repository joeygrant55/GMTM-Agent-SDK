'use client'

import Link from 'next/link'
import { createContext, useCallback, useContext, useState } from 'react'
import { signOutOfSparq, useSparqSession } from '@/app/_lib/useSparqSession'
import { usePathname, useRouter } from 'next/navigation'
import SparqLogo from '@/components/SparqLogo'
import { ParentNoticeScreen, SwitchAccountLink, useEntryNotice } from './ParentNoticeGate'

export type CareerView = 'home' | 'portfolio' | 'opportunities' | 'progress'

const CareerNavigation = createContext<{ view: CareerView; revision: number; setView: (view: CareerView) => void } | null>(null)

export function useCareerNavigation() {
  const navigation = useContext(CareerNavigation)
  if (!navigation) throw new Error('Career navigation requires the profile shell.')
  return navigation
}

const navigationItems: Array<{ view: CareerView; label: string }> = [
  { view: 'home', label: 'Home' }, { view: 'portfolio', label: 'Portfolio' },
  { view: 'opportunities', label: 'Opportunities' }, { view: 'progress', label: 'Progress' },
]

function CareerShell({ children, userId }: { children: React.ReactNode; userId?: string }) {
  const { notice, accept } = useEntryNotice(userId)
  const blocked = notice.phase === 'ended' || (notice.required && !notice.accepted)
  const [navigation, setNavigation] = useState<{ view: CareerView; revision: number }>({ view: 'home', revision: 0 })
  const pathname = usePathname()
  const router = useRouter()
  // Views live on /home/inbox; from another page (colleges) the nav goes back there.
  const setView = useCallback((view: CareerView) => {
    setNavigation(previous => ({ view, revision: previous.revision + 1 }))
    if (pathname !== '/home/inbox') router.push('/home/inbox')
  }, [pathname, router])
  const { view } = navigation

  return (
    <CareerNavigation.Provider value={{ ...navigation, setView }}>
    <div className="min-h-[100dvh] bg-sparq-charcoal font-display text-white">
      <a href="#profile-main" className="sr-only z-50 rounded-lg bg-sparq-lime p-3 text-sparq-charcoal focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to profile</a>
      <header className="border-b border-white/10">
        <div className="mx-auto flex min-h-[72px] max-w-[1424px] flex-wrap items-center justify-between gap-x-5 px-6 lg:px-10">
          <Link href="/home" onClick={event => { event.preventDefault(); setView('home') }} aria-label="SPARQ home" className="inline-flex min-h-16 items-center focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime"><SparqLogo className="w-28 sm:w-32" /></Link>
          <nav aria-label="Athlete workspace" className="order-3 flex w-full justify-between gap-2 overflow-x-auto sm:order-none sm:mr-auto sm:ml-10 sm:w-auto sm:justify-start sm:gap-6 lg:ml-24 lg:gap-8">
            {navigationItems.map(item => <button key={item.view} type="button" onClick={() => setView(item.view)} aria-current={view === item.view ? 'page' : undefined} className={`inline-flex min-h-12 shrink-0 items-center border-b-[3px] px-1 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-sparq-lime sm:min-h-[72px] sm:px-2 sm:text-sm ${view === item.view ? 'border-sparq-lime text-white' : 'border-transparent text-gray-400 hover:text-white'}`}>{item.label}</button>)}
          </nav>
          <div className="flex items-center gap-3">
            {notice.required && <SwitchAccountLink />}
            <a href="https://gmtm.com" target="_blank" rel="noopener noreferrer" aria-label="Back to GMTM (opens in a new tab)" className="inline-flex min-h-11 items-center gap-1 text-xs text-gray-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime">Back to GMTM <span aria-hidden="true">↗</span></a>
            <button type="button" onClick={() => { void signOutOfSparq() }} className="inline-flex min-h-11 items-center text-xs text-gray-400 hover:text-white focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime">Sign out</button>
          </div>
        </div>
      </header>
      <main id="profile-main" tabIndex={-1} className="mx-auto w-full max-w-[1424px] px-6 outline-none lg:px-10">
        {notice.phase === 'loading' && userId ? <p role="status" className="py-16 text-center text-gray-400">Loading…</p>
          : blocked ? <ParentNoticeScreen notice={notice} accept={accept} /> : children}
      </main>
    </div>
    </CareerNavigation.Provider>
  )
}

export default function ProfileWorkspaceShell({ children }: { children: React.ReactNode }) {
  const { isLoaded, user } = useSparqSession()
  return <CareerShell key={isLoaded ? user?.id || 'signed-out' : 'loading'} userId={user?.id}>{children}</CareerShell>
}
