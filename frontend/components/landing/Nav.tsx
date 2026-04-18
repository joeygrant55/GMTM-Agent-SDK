'use client'

import Link from 'next/link'
import Image from 'next/image'
import { useState } from 'react'
import { motion, useScroll, useTransform, AnimatePresence } from 'framer-motion'

const LINKS = [
  { href: '#features', label: 'Features' },
  { href: '#how', label: 'How it works' },
  { href: '#pricing', label: 'Pricing' },
  { href: '/demo', label: 'Demo' },
]

function AuthButtons({ onClick }: { onClick?: () => void }) {
  return (
    <>
      <Link
        href="/sign-in"
        onClick={onClick}
        className="text-sm text-white/70 hover:text-white transition-colors"
      >
        Sign in
      </Link>
      <Link
        href="/onboarding/search"
        onClick={onClick}
        className="group inline-flex items-center gap-1.5 rounded-full bg-sparq-lime px-4 py-2 text-sm font-semibold text-sparq-charcoal transition-all hover:bg-sparq-lime-light hover:shadow-lime-glow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sparq-lime focus-visible:ring-offset-2 focus-visible:ring-offset-sparq-charcoal"
      >
        Get started
        <span className="transition-transform group-hover:translate-x-0.5">→</span>
      </Link>
    </>
  )
}

export function Nav() {
  const { scrollY } = useScroll()
  const bg = useTransform(scrollY, [0, 60], ['rgba(10,10,10,0)', 'rgba(10,10,10,0.72)'])
  const border = useTransform(scrollY, [0, 60], ['rgba(255,255,255,0)', 'rgba(255,255,255,0.06)'])
  const blur = useTransform(scrollY, [0, 60], ['blur(0px)', 'blur(12px)'])
  const [open, setOpen] = useState(false)

  return (
    <>
      <motion.nav
        style={{
          backgroundColor: bg,
          borderBottomColor: border,
          backdropFilter: blur,
          WebkitBackdropFilter: blur as unknown as string,
        }}
        className="fixed inset-x-0 top-0 z-50 border-b"
      >
        <div className="mx-auto flex max-w-7xl items-center justify-between px-6 py-4">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="relative h-8 w-8 overflow-hidden rounded-lg">
              <Image src="/sparq-logo.jpg" alt="SPARQ" fill sizes="32px" />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight">
              SPARQ <span className="text-white/50">Agent</span>
            </span>
          </Link>
          <div className="hidden items-center gap-8 md:flex">
            {LINKS.map((l) => (
              <Link
                key={l.href}
                href={l.href}
                className="text-sm text-white/60 transition-colors hover:text-white"
              >
                {l.label}
              </Link>
            ))}
          </div>
          <div className="hidden items-center gap-4 md:flex">
            <AuthButtons />
          </div>
          <button
            aria-label="Open menu"
            onClick={() => setOpen(true)}
            className="md:hidden rounded-md p-2 text-white/70 hover:text-white"
          >
            <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
              <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      </motion.nav>

      <AnimatePresence>
        {open && (
          <motion.div
            key="backdrop"
            className="fixed inset-0 z-[60] bg-sparq-charcoal/80 md:hidden"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={() => setOpen(false)}
          >
            <motion.aside
              key="panel"
              className="absolute right-0 top-0 h-full w-[84%] max-w-sm border-l border-white/10 bg-sparq-charcoal p-6"
              initial={{ x: '100%' }}
              animate={{ x: 0 }}
              exit={{ x: '100%' }}
              transition={{ duration: 0.35, ease: [0.22, 1, 0.36, 1] }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="mb-8 flex items-center justify-between">
                <span className="font-display text-lg font-semibold">SPARQ Agent</span>
                <button
                  aria-label="Close menu"
                  onClick={() => setOpen(false)}
                  className="rounded-md p-2 text-white/70 hover:text-white"
                >
                  <svg className="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={1.8}>
                    <path d="M6 6l12 12M6 18L18 6" strokeLinecap="round" />
                  </svg>
                </button>
              </div>
              <div className="flex flex-col gap-4">
                {LINKS.map((l) => (
                  <Link
                    key={l.href}
                    href={l.href}
                    onClick={() => setOpen(false)}
                    className="text-lg text-white/80 hover:text-white"
                  >
                    {l.label}
                  </Link>
                ))}
              </div>
              <div className="mt-8 flex flex-col gap-3">
                <AuthButtons onClick={() => setOpen(false)} />
              </div>
            </motion.aside>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  )
}
