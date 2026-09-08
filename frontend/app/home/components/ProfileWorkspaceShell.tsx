'use client'

import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'

export default function ProfileWorkspaceShell({ children }: { children: React.ReactNode }) {
  return (
    <div className="min-h-[100dvh] bg-sparq-charcoal font-display text-white">
      <a href="#profile-main" className="sr-only z-50 rounded-lg bg-sparq-lime p-3 text-sparq-charcoal focus:not-sr-only focus:absolute focus:left-4 focus:top-4">Skip to profile</a>
      <header className="border-b border-white/10">
        <div className="mx-auto flex min-h-20 max-w-6xl items-center justify-between gap-4 px-5 sm:px-8">
          <Link href="/home" aria-label="SPARQ home" className="text-2xl font-black tracking-[-0.06em] text-sparq-lime">SPARQ</Link>
          <div className="flex items-center gap-5">
            <span className="text-xs font-medium tracking-wide text-gray-400">Private profile</span>
            <UserButton />
          </div>
        </div>
      </header>
      <main id="profile-main" tabIndex={-1}>{children}</main>
    </div>
  )
}
