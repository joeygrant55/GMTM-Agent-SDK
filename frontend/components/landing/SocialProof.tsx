'use client'

import { SectionHeader } from './_primitives/SectionHeader'
import { Reveal, Stagger, staggerItem } from './_primitives/Reveal'
import { LimeAura } from './_primitives/LimeAura'
import { motion } from 'framer-motion'

const HERO_QUOTE = {
  body:
    'I went from zero offers and no idea where to start, to a shortlist of 8 programs and a coach replying in a week. My dad would\u2019ve paid $5,000 for what this thing does in an hour.',
  author: 'Marcus D.',
  role: 'QB · Class of 2027 · Texas',
}

const QUOTES = [
  {
    body:
      '"My athlete asked a question at 11pm on a Sunday and had a full scouting report by Monday morning. That\u2019s not a service — that\u2019s an unfair advantage."',
    author: 'Coach Ramirez',
    role: 'HS Football · Florida',
  },
  {
    body:
      '"It wrote a cleaner email to a Big Ten assistant than I would have. And I\u2019m a parent who read three recruiting books."',
    author: 'Alicia K.',
    role: 'Parent · Class of 2026 VB',
  },
  {
    body:
      '"Fit reports actually tell you why. Roster openings, offense style, academic index. I stopped cold-emailing random schools."',
    author: 'Devon L.',
    role: 'PG · Class of 2026 · Ohio',
  },
]

const PROGRAMS = [
  'Rice', 'SMU', 'Tulane', 'Yale', 'Vanderbilt', 'Air Force', 'Stanford', 'Princeton', 'Duke', 'Northwestern', 'Notre Dame', 'Baylor',
]

export function SocialProof() {
  return (
    <section className="relative overflow-hidden py-24 sm:py-32 lg:py-40">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          eyebrow="Early reactions"
          title={
            <>
              Athletes, coaches, and parents<br />
              who stopped guessing.
            </>
          }
        />

        {/* Hero quote */}
        <div className="relative mt-16">
          <LimeAura size={480} opacity={0.14} className="-top-20 left-1/2 -translate-x-1/2" />
          <Reveal>
            <div className="relative overflow-hidden rounded-3xl border border-white/10 bg-sparq-charcoal-light/70 p-10 sm:p-14">
              <div
                aria-hidden
                className="pointer-events-none absolute -left-4 -top-10 select-none font-display text-[200px] leading-none text-sparq-lime/20"
              >
                &ldquo;
              </div>
              <p className="relative max-w-3xl font-display text-2xl font-medium leading-snug tracking-tight text-white sm:text-3xl">
                {HERO_QUOTE.body}
              </p>
              <div className="relative mt-8 flex items-center gap-4">
                <div className="h-11 w-11 rounded-full bg-gradient-to-br from-sparq-lime/80 to-sparq-lime/30 ring-1 ring-sparq-lime/40" />
                <div>
                  <div className="text-sm font-semibold text-white">{HERO_QUOTE.author}</div>
                  <div className="text-xs text-white/50">{HERO_QUOTE.role}</div>
                </div>
              </div>
            </div>
          </Reveal>
        </div>

        {/* Supporting */}
        <Stagger className="mt-6 grid grid-cols-1 gap-4 md:grid-cols-3">
          {QUOTES.map((q) => (
            <motion.div
              key={q.author}
              variants={staggerItem}
              className="rounded-2xl border border-white/8 bg-white/[0.025] p-6 transition-colors hover:border-white/20"
            >
              <p className="text-sm leading-relaxed text-white/75">{q.body}</p>
              <div className="mt-5 flex items-center gap-3">
                <div className="h-8 w-8 rounded-full bg-white/10" />
                <div>
                  <div className="text-xs font-semibold text-white">{q.author}</div>
                  <div className="text-[11px] text-white/45">{q.role}</div>
                </div>
              </div>
            </motion.div>
          ))}
        </Stagger>

        {/* Programs marquee */}
        <div className="mt-20">
          <div className="mb-5 text-center text-eyebrow uppercase text-white/35">
            Programs in the SPARQ database
          </div>
          <div className="relative overflow-hidden [mask-image:linear-gradient(to_right,transparent,black_10%,black_90%,transparent)]">
            <div className="flex w-max animate-marquee gap-12 py-2">
              {[...PROGRAMS, ...PROGRAMS].map((p, i) => (
                <span
                  key={`${p}-${i}`}
                  className="shrink-0 font-display text-xl font-medium tracking-tight text-white/35 transition-colors hover:text-white/70"
                >
                  {p}
                </span>
              ))}
            </div>
          </div>
          <div className="mt-4 text-center text-[11px] text-white/30">
            Illustrative. Full coverage includes every active NCAA, NAIA, and NJCAA women’s flag football program.
          </div>
        </div>
      </div>
    </section>
  )
}
