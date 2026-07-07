import Link from 'next/link'
import Image from 'next/image'
import type { ReactNode } from 'react'

export function LegalPage({ title, updated, children }: { title: string; updated: string; children: ReactNode }) {
  return (
    <div className="min-h-screen bg-sparq-charcoal text-white">
      <header className="border-b border-white/5">
        <div className="mx-auto flex max-w-3xl items-center justify-between px-6 py-5">
          <Link href="/" className="flex items-center gap-2.5">
            <div className="relative h-8 w-8 overflow-hidden rounded-lg">
              <Image src="/sparq-logo.jpg" alt="SPARQ" fill sizes="32px" />
            </div>
            <span className="font-display text-lg font-semibold tracking-tight">
              SPARQ <span className="text-white/50">Agent</span>
            </span>
          </Link>
          <nav className="flex items-center gap-5 text-sm text-white/60">
            <Link href="/privacy" className="hover:text-white">Privacy</Link>
            <Link href="/terms" className="hover:text-white">Terms</Link>
          </nav>
        </div>
      </header>

      <main className="mx-auto max-w-3xl px-6 py-14">
        <h1 className="font-display text-3xl font-semibold tracking-tight">{title}</h1>
        <p className="mt-2 text-sm text-white/40">Last updated: {updated}</p>
        <div className="legal-prose mt-10 space-y-8 text-[15px] leading-relaxed text-white/75 [&_h2]:font-display [&_h2]:text-xl [&_h2]:font-semibold [&_h2]:text-white [&_h3]:font-semibold [&_h3]:text-white/90 [&_ul]:list-disc [&_ul]:space-y-2 [&_ul]:pl-6 [&_a]:text-sparq-lime [&_a]:underline-offset-2 hover:[&_a]:underline">
          {children}
        </div>
      </main>

      <footer className="border-t border-white/5">
        <div className="mx-auto max-w-3xl px-6 py-8 text-xs text-white/40">
          &copy; 2026 SPARQ Agent. Questions about these policies:{' '}
          <a href="mailto:hello@sparqagent.ai" className="text-white/60 hover:text-white">hello@sparqagent.ai</a>
        </div>
      </footer>
    </div>
  )
}
