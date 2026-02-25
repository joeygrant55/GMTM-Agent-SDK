'use client'

import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { UserButton, useUser } from '@clerk/nextjs'

const NAV_ITEMS = [
  { label: '🏠 Home', href: '/home' },
  { label: '🎓 Colleges', href: '/home/colleges' },
  { label: '✉️ Outreach', href: '/home/outreach' },
]

const COMING_SOON_ITEMS = [
  { label: '📅 Timeline', status: 'Coming Soon' },
  { label: '👤 Profile', status: 'Coming Soon' },
]

export default function WorkspaceSidebar() {
  const pathname = usePathname()
  const { user } = useUser()

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
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block px-3 py-2 text-sm ${
                active
                  ? 'bg-white/10 text-white rounded-lg'
                  : 'text-gray-500 hover:text-gray-300 rounded-lg'
              }`}
            >
              {item.label}
            </Link>
          )
        })}

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
