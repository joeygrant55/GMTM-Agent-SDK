'use client'

import { apiFetch } from '@/app/_lib/api'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { UserButton, useUser } from '@clerk/nextjs'
import { useEffect, useState } from 'react'

const DEFAULT_BACKEND_URL = 'https://focused-essence-production-9809.up.railway.app'

interface NavItem {
  label: string
  href: string
  badgeKey?: 'inbox' | 'outreach_drafts' | 'active_agents'
  divider?: boolean
}

const NAV_ITEMS: NavItem[] = [
  { label: '📥 Inbox', href: '/home/inbox', badgeKey: 'inbox' },
  { label: '🎓 Colleges', href: '/home/colleges' },
  { label: '✉️ Outreach', href: '/home/outreach', badgeKey: 'outreach_drafts' },
  { label: '👤 Profile', href: '/home/profile' },
  { label: '📅 Timeline', href: '/home/timeline' },
]

const COMING_SOON_ITEMS: { label: string; status: string }[] = [
  { label: '🧭 Plan', status: 'soon' },
  { label: '🎬 Film', status: 'soon' },
  { label: '✨ Activity', status: 'soon' },
]

interface Badges {
  inbox: number
  outreach_drafts: number
  active_agents: number
}

export default function WorkspaceSidebar() {
  const pathname = usePathname()
  const { user, isLoaded } = useUser()
  const [badges, setBadges] = useState<Badges>({ inbox: 0, outreach_drafts: 0, active_agents: 0 })

  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || DEFAULT_BACKEND_URL

  useEffect(() => {
    if (!isLoaded || !user?.id) return
    let cancelled = false
    const load = () => {
      apiFetch(`${backendUrl}/api/workspace/badges/${user.id}`)
        .then((res) => res.json())
        .then((data) => {
          if (cancelled) return
          setBadges({
            inbox: Number(data?.inbox) || 0,
            outreach_drafts: Number(data?.outreach_drafts) || 0,
            active_agents: Number(data?.active_agents) || 0,
          })
        })
        .catch(() => {})
    }
    load()
    const interval = setInterval(load, 30_000)
    return () => {
      cancelled = true
      clearInterval(interval)
    }
  }, [backendUrl, isLoaded, user?.id])

  const isActive = (href: string) => {
    if (href === '/home') return pathname === '/home'
    return pathname === href || pathname.startsWith(`${href}/`)
  }

  return (
    <aside className="w-[220px] h-screen bg-sparq-charcoal border-r border-white/10 flex flex-col p-4">
      <div className="flex items-center gap-2 px-1">
        <img src="/sparq-logo.jpg" alt="SPARQ" className="w-8 h-8 rounded-md" />
        <span className="text-sparq-lime font-black text-lg">SPARQ</span>
      </div>

      <nav className="mt-8 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = isActive(item.href)
          const count = item.badgeKey ? badges[item.badgeKey] : 0
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between px-3 py-2 text-sm rounded-lg ${
                active ? 'bg-white/10 text-white' : 'text-gray-500 hover:text-gray-300'
              }`}
            >
              <span>{item.label}</span>
              {count > 0 && (
                <span className="text-[10px] font-bold bg-sparq-lime/20 text-sparq-lime border border-sparq-lime/30 rounded-md px-1.5 py-0.5">
                  {count}
                </span>
              )}
            </Link>
          )
        })}

        <div className="pt-3 mt-3 border-t border-white/5" />
        {COMING_SOON_ITEMS.map((item) => (
          <div key={item.label} className="px-3 py-2 rounded-lg text-gray-600 text-sm flex items-center justify-between">
            <span>{item.label}</span>
            <span className="text-[10px] uppercase tracking-wide">{item.status}</span>
          </div>
        ))}
      </nav>

      <div className="mt-auto border-t border-white/10 pt-4">
        <div className="flex items-center gap-3 px-1">
          <UserButton />
          <span className="text-sm text-gray-300 truncate">{user?.firstName || 'Athlete'}</span>
        </div>
      </div>
    </aside>
  )
}
