'use client'

import Link from 'next/link'
import { createContext, useCallback, useContext, useState } from 'react'
import { UserButton, useUser } from '@clerk/nextjs'

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

function CareerShell({ children }: { children: React.ReactNode }) {
  const [navigation, setNavigation] = useState<{ view: CareerView; revision: number }>({ view: 'home', revision: 0 })
  const setView = useCallback((view: CareerView) => setNavigation(previous => ({ view, revision: previous.revision + 1 })), [])
  const { view } = navigation

  return (
    <CareerNavigation.Provider value={{ ...navigation, setView }}>
    <div className="min-h-[100dvh] bg-sparq-charcoal font-display text-white">
      <a href="#profile-main" className="sr-only z-50 rounded-lg bg-sparq-lime p-3 text-sparq-charcoal focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to profile</a>
      <header className="border-b border-white/10">
        <div className="mx-auto flex min-h-[72px] max-w-[1424px] flex-wrap items-center justify-between gap-x-5 px-6 lg:px-10">
          <Link href="/home" onClick={event => { event.preventDefault(); setView('home') }} aria-label="SPARQ home" className="inline-flex min-h-16 items-center text-3xl font-black tracking-[-0.06em] text-sparq-lime focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-sparq-lime">SPARQ</Link>
          <nav aria-label="Athlete workspace" className="order-3 flex w-full justify-between gap-2 overflow-x-auto sm:order-none sm:mr-auto sm:ml-10 sm:w-auto sm:justify-start sm:gap-6 lg:ml-24 lg:gap-8">
            {navigationItems.map(item => <button key={item.view} type="button" onClick={() => setView(item.view)} aria-current={view === item.view ? 'page' : undefined} className={`inline-flex min-h-12 shrink-0 items-center border-b-[3px] px-1 text-xs font-medium transition-colors focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-[-4px] focus-visible:outline-sparq-lime sm:min-h-[72px] sm:px-2 sm:text-sm ${view === item.view ? 'border-sparq-lime text-white' : 'border-transparent text-gray-400 hover:text-white'}`}>{item.label}</button>)}
          </nav>
          <div className="flex items-center gap-3">
            <span className="hidden text-xs text-gray-500 lg:inline">Private workspace</span>
            <UserButton />
          </div>
        </div>
      </header>
      <main id="profile-main" tabIndex={-1} className="mx-auto w-full max-w-[1424px] px-6 outline-none lg:px-10">{children}</main>
    </div>
    </CareerNavigation.Provider>
  )
}

export default function ProfileWorkspaceShell({ children }: { children: React.ReactNode }) {
  const { isLoaded, user } = useUser()
  return <CareerShell key={isLoaded ? user?.id || 'signed-out' : 'loading'}>{children}</CareerShell>
}
