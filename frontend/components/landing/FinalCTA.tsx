'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { LimeAura } from './_primitives/LimeAura'
import { Reveal } from './_primitives/Reveal'

const PLACEHOLDERS = [
  'Which D2 schools recruit 5\u201910" point guards in California?',
  'Draft an email to the Vandy baseball coach.',
  'What camps should I attend this summer?',
  'Who\u2019s recruiting 2027 QBs in the SEC right now?',
  'Compare Ivy admissions odds vs. Patriot League for my GPA.',
]

export function FinalCTA() {
  const [idx, setIdx] = useState(0)
  const [q, setQ] = useState('')
  const router = useRouter()

  useEffect(() => {
    const t = setInterval(() => setIdx((i) => (i + 1) % PLACEHOLDERS.length), 3200)
    return () => clearInterval(t)
  }, [])

  function submit(e?: React.FormEvent) {
    e?.preventDefault()
    const query = (q || PLACEHOLDERS[idx]).trim()
    router.push(`/onboarding/search?intent=ask&q=${encodeURIComponent(query)}`)
  }

  return (
    <section className="relative overflow-hidden py-24 sm:py-32 lg:py-40">
      <LimeAura size={780} opacity={0.18} className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" pulse />
      <div className="relative mx-auto max-w-4xl px-6 text-center">
        <Reveal>
          <div className="mb-5 text-eyebrow uppercase text-sparq-lime/80">Your move</div>
        </Reveal>
        <Reveal delay={0.05}>
          <h2 className="font-display text-display-lg font-semibold tracking-tight text-white">
            Ask your first question.
          </h2>
        </Reveal>
        <Reveal delay={0.1}>
          <p className="mt-5 text-lg text-white/55">
            Three free. No card. The agent goes to work immediately.
          </p>
        </Reveal>

        <Reveal delay={0.2}>
          <form
            onSubmit={submit}
            className="mx-auto mt-12 flex max-w-2xl items-center gap-2 rounded-full gradient-border bg-sparq-charcoal-light/80 px-2 py-2 shadow-card"
          >
            <div className="relative ml-3 flex-1">
              <input
                value={q}
                onChange={(e) => setQ(e.target.value)}
                className="peer w-full bg-transparent py-3 text-[15px] text-white outline-none placeholder:text-transparent"
                aria-label="Ask the agent"
              />
              {!q && (
                <div className="pointer-events-none absolute inset-0 flex items-center overflow-hidden">
                  <AnimatePresence mode="wait">
                    <motion.span
                      key={idx}
                      initial={{ y: 18, opacity: 0 }}
                      animate={{ y: 0, opacity: 1 }}
                      exit={{ y: -18, opacity: 0 }}
                      transition={{ duration: 0.45, ease: [0.22, 1, 0.36, 1] }}
                      className="block truncate text-[15px] text-white/40"
                    >
                      {PLACEHOLDERS[idx]}
                    </motion.span>
                  </AnimatePresence>
                </div>
              )}
            </div>
            <button
              type="submit"
              aria-label="Ask"
              className="flex h-11 w-11 flex-none items-center justify-center rounded-full bg-sparq-lime text-sparq-charcoal transition-all hover:bg-sparq-lime-light hover:shadow-lime-glow-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sparq-lime focus-visible:ring-offset-2 focus-visible:ring-offset-sparq-charcoal"
            >
              <svg viewBox="0 0 16 16" className="h-4 w-4 fill-current">
                <path d="M1 7h11.586L8.293 2.707l1.414-1.414L15.414 7l-5.707 5.707-1.414-1.414L12.586 7H1V7z" />
              </svg>
            </button>
          </form>
        </Reveal>

        <Reveal delay={0.3}>
          <div className="mt-10 flex flex-wrap items-center justify-center gap-x-6 gap-y-2 text-[12px] text-white/40">
            <Dot /> <span>75K athletes of real data</span>
            <Dot /> <span>2,900 programs</span>
            <Dot /> <span>$29/mo · cancel anytime</span>
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Dot() {
  return <span aria-hidden className="inline-block h-1 w-1 rounded-full bg-sparq-lime" />
}
