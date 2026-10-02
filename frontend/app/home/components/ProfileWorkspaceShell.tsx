'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { signOutOfSparq, useSparqSession } from '@/app/_lib/useSparqSession'
import { ParentNoticeScreen, SwitchAccountLink, useEntryNotice } from './ParentNoticeGate'
import SparqLogo from '@/components/SparqLogo'

const focus = 'focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-4 focus-visible:outline-jr-lime'

// One URL per page, so back, refresh and deep links work. /home/footage (all footage and
// results) stays reachable from Home's "See all"; it is not a tab.
export const TABS = [
  { href: '/home', label: 'Home', match: (path: string) => path === '/home' || path === '/home/inbox' },
  { href: '/home/colleges', label: 'Colleges', match: (path: string) => path.startsWith('/home/colleges') },
  { href: '/home/emails', label: 'Emails', match: (path: string) => path === '/home/emails' },
  { href: '/home/card', label: 'My card', match: (path: string) => path === '/home/card' || path === '/home/footage' },
] as const

export function activeTab(pathname: string | null): string | null {
  return TABS.find(tab => tab.match(pathname || ''))?.href || null
}

// Rendered once per page load. The page (children) mounts only after the session and the
// parent notice are known, so it is never mounted, torn down and mounted again; a first
// click (nav tab, heart) is not lost to a remount (2026-10-02 live smoke, B1).
function CareerShell({ children, sessionLoaded, userId }: { children: React.ReactNode; sessionLoaded: boolean; userId?: string }) {
  const { notice, accept } = useEntryNotice(userId)
  const blocked = notice.phase === 'ended' || (notice.required && !notice.accepted)
  const waiting = !sessionLoaded || (!!userId && notice.phase === 'loading')
  const active = activeTab(usePathname())

  return (
    <div className="min-h-[100dvh] bg-jr-ground font-display text-jr-text">
      <a href="#profile-main" className="sr-only z-50 rounded-lg bg-jr-lime p-3 text-jr-ground focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to profile</a>
      <header className="border-b border-jr-line">
        <div className="mx-auto flex min-h-[72px] max-w-[1344px] items-center justify-between gap-6 px-4 md:px-8 lg:px-12">
          <div className="flex items-center gap-12">
            <Link href="/home" aria-label="SPARQ home" className={`inline-flex min-h-11 shrink-0 items-center ${focus}`}><SparqLogo className="w-[112px] md:w-[128px]" /></Link>
            <nav aria-label="Athlete workspace" className="hidden gap-2 md:flex">
              {TABS.map(tab => <Link key={tab.href} href={tab.href} prefetch={false} aria-current={active === tab.href ? 'page' : undefined}
                className={`rounded-full px-4 py-2.5 text-[15px] ${focus} ${active === tab.href ? 'bg-jr-raised font-semibold text-white' : 'text-jr-muted hover:text-white'}`}>{tab.label}</Link>)}
            </nav>
          </div>
          <div className="flex items-center gap-4 text-sm text-jr-muted">
            {notice.required && <SwitchAccountLink />}
            <a href="https://gmtm.com" target="_blank" rel="noopener noreferrer" aria-label="Back to GMTM (opens in a new tab)" className={`hidden min-h-11 items-center hover:text-white sm:inline-flex ${focus}`}>Back to GMTM</a>
            <button type="button" onClick={() => { void signOutOfSparq() }} className={`inline-flex min-h-11 items-center hover:text-white ${focus}`}>Sign out</button>
          </div>
        </div>
      </header>
      <main id="profile-main" tabIndex={-1} className="mx-auto w-full max-w-[1344px] px-4 pb-28 outline-none md:px-8 md:pb-12 lg:px-12">
        {waiting ? <p role="status" className="py-16 text-center text-jr-muted">Loading…</p>
          : blocked ? <ParentNoticeScreen notice={notice} accept={accept} /> : children}
      </main>
      {/* Phone (<768px): the same four pages as a bottom tab bar. */}
      <nav aria-label="Athlete workspace tabs" className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-4 border-t border-jr-line bg-[#0F0F12] px-2 pb-[max(env(safe-area-inset-bottom),12px)] pt-2 md:hidden">
        {TABS.map(tab => <Link key={tab.href} href={tab.href} prefetch={false} aria-current={active === tab.href ? 'page' : undefined}
          className={`flex min-h-11 items-center justify-center rounded-lg px-1 text-[13px] ${focus} ${active === tab.href ? 'font-bold text-jr-lime' : 'text-jr-muted'}`}>{tab.label}</Link>)}
      </nav>
    </div>
  )
}

export default function ProfileWorkspaceShell({ children }: { children: React.ReactNode }) {
  const { isLoaded, user } = useSparqSession()
  return <CareerShell sessionLoaded={isLoaded} userId={user?.id}>{children}</CareerShell>
}
