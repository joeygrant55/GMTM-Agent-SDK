import Link from 'next/link'
import Image from 'next/image'

const COLS: { title: string; links: { label: string; href: string }[] }[] = [
  {
    title: 'Product',
    links: [
      { label: 'Features', href: '#features' },
      { label: 'Pricing', href: '#pricing' },
      { label: 'Live demo', href: '/demo' },
      { label: 'Roadmap', href: '#' },
    ],
  },
  {
    title: 'Company',
    links: [
      { label: 'About', href: '#' },
      { label: 'Careers', href: '#' },
      { label: 'Contact', href: 'mailto:hello@sparqagent.ai' },
      { label: 'Press', href: '#' },
    ],
  },
  {
    title: 'Resources',
    links: [
      { label: 'Live demo', href: '/demo' },
      { label: 'Contact', href: 'mailto:hello@sparqagent.ai' },
      { label: 'Privacy', href: '/privacy' },
      { label: 'Terms', href: '/terms' },
    ],
  },
]

export function Footer() {
  return (
    <footer className="relative overflow-hidden border-t border-white/5 bg-sparq-dark">
      <div className="mx-auto max-w-7xl px-6 pt-20 pb-12">
        <div className="grid grid-cols-2 gap-10 md:grid-cols-4 lg:grid-cols-5">
          <div className="col-span-2 lg:col-span-2">
            <Link href="/" className="flex items-center gap-2.5">
              <div className="relative h-8 w-8 overflow-hidden rounded-lg">
                <Image src="/sparq-logo.jpg" alt="SPARQ" fill sizes="32px" />
              </div>
              <span className="font-display text-lg font-semibold tracking-tight">
                SPARQ <span className="text-white/50">Agent</span>
              </span>
            </Link>
            <p className="mt-5 max-w-sm text-sm leading-relaxed text-white/45">
              The AI recruiting agent for flag football. Powered by the SPARQ testing USA Flag
              Football selects national team athletes from.
            </p>
            <div className="mt-6 flex items-center gap-2">
              <Link href="#" aria-label="X" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 text-white/60 hover:border-white/30 hover:text-white">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24"><path d="M17.53 3H20.5l-6.5 7.43L22 21h-6.06l-4.74-6.2L5.78 21H2.8l6.97-7.96L2 3h6.22l4.29 5.67L17.53 3zm-1.06 16h1.64L7.62 4.88H5.87L16.47 19z" /></svg>
              </Link>
              <Link href="#" aria-label="Instagram" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 text-white/60 hover:border-white/30 hover:text-white">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24"><path d="M12 2c2.72 0 3.06.01 4.12.06 1.06.05 1.79.22 2.43.47a4.9 4.9 0 011.77 1.15 4.9 4.9 0 011.15 1.77c.25.64.42 1.37.47 2.43.05 1.06.06 1.4.06 4.12s-.01 3.06-.06 4.12c-.05 1.06-.22 1.79-.47 2.43a4.9 4.9 0 01-1.15 1.77 4.9 4.9 0 01-1.77 1.15c-.64.25-1.37.42-2.43.47-1.06.05-1.4.06-4.12.06s-3.06-.01-4.12-.06c-1.06-.05-1.79-.22-2.43-.47a4.9 4.9 0 01-1.77-1.15 4.9 4.9 0 01-1.15-1.77c-.25-.64-.42-1.37-.47-2.43C2.01 15.06 2 14.72 2 12s.01-3.06.06-4.12c.05-1.06.22-1.79.47-2.43A4.9 4.9 0 013.68 3.68 4.9 4.9 0 015.45 2.53c.64-.25 1.37-.42 2.43-.47C8.94 2.01 9.28 2 12 2zm0 5a5 5 0 100 10 5 5 0 000-10zm0 2a3 3 0 110 6 3 3 0 010-6zm5.25-3.5a1.25 1.25 0 100 2.5 1.25 1.25 0 000-2.5z" /></svg>
              </Link>
              <Link href="#" aria-label="YouTube" className="flex h-9 w-9 items-center justify-center rounded-full border border-white/10 text-white/60 hover:border-white/30 hover:text-white">
                <svg className="h-4 w-4 fill-current" viewBox="0 0 24 24"><path d="M23.5 7.1a3 3 0 00-2.1-2.1C19.6 4.5 12 4.5 12 4.5s-7.6 0-9.4.5A3 3 0 00.5 7.1 31 31 0 000 12a31 31 0 00.5 4.9 3 3 0 002.1 2.1c1.8.5 9.4.5 9.4.5s7.6 0 9.4-.5a3 3 0 002.1-2.1A31 31 0 0024 12a31 31 0 00-.5-4.9zM9.6 15.3V8.7l6.3 3.3-6.3 3.3z" /></svg>
              </Link>
            </div>
          </div>

          {COLS.map((c) => (
            <div key={c.title}>
              <div className="text-eyebrow uppercase text-white/35">{c.title}</div>
              <ul className="mt-5 space-y-3 text-sm">
                {c.links.map((l) => (
                  <li key={l.label}>
                    <Link href={l.href} className="text-white/65 transition-colors hover:text-white">
                      {l.label}
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
          ))}
        </div>

        <div className="mt-16 flex flex-col items-start justify-between gap-4 border-t border-white/5 pt-6 text-xs text-white/40 sm:flex-row sm:items-center">
          <div>&copy; 2026 SPARQ Agent. All rights reserved.</div>
          <div className="flex items-center gap-2">
            <span className="inline-flex h-2 w-2 rounded-full bg-sparq-lime" />
            All systems normal
          </div>
        </div>
      </div>

      <div
        aria-hidden
        className="pointer-events-none select-none overflow-hidden px-6 pb-6"
      >
        <div className="font-display text-[14vw] font-semibold leading-[0.85] tracking-[-0.05em] text-white/[0.035]">
          SPARQ AGENT
        </div>
      </div>
    </footer>
  )
}
