'use client'

import { motion } from 'framer-motion'
import { Reveal } from './_primitives/Reveal'
import { LimeAura } from './_primitives/LimeAura'

const EASE = [0.22, 1, 0.36, 1] as const

export function TheShift() {
  return (
    <section className="relative overflow-hidden py-28 sm:py-36 lg:py-44">
      <LimeAura size={600} opacity={0.12} className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" />
      <div className="relative mx-auto max-w-4xl px-6 text-center">
        <Reveal>
          <div className="mb-8 inline-flex items-center gap-2 text-eyebrow uppercase text-sparq-lime/80">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-sparq-lime" />
            The shift
          </div>
        </Reveal>
        <motion.h2
          initial={{ opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-15% 0px' }}
          transition={{ duration: 0.8, ease: EASE }}
          className="font-display text-display-lg font-semibold tracking-tight leading-[1.05]"
        >
          Recruiting consultants charge families{' '}
          <span className="text-white/50">$5,000 a year</span> to do what an AI can do in an afternoon.{' '}
          <br className="hidden sm:block" />
          <span className="text-sparq-lime">We charge $29.</span>
        </motion.h2>

        <Reveal delay={0.2}>
          <div className="mx-auto mt-16 grid max-w-3xl grid-cols-1 gap-px overflow-hidden rounded-2xl bg-white/5 sm:grid-cols-2">
            <Column
              title="Traditional recruiting service"
              rows={[
                '$5,000+ per year',
                'Bandwidth limited to one consultant',
                'Updates on their schedule',
                'Generic outreach templates',
                'Paywalled once you cancel',
              ]}
              muted
            />
            <Column
              title="SPARQ Agent"
              rows={[
                '$29 per month',
                'Searches 2,900 programs in seconds',
                'Available the minute you need it',
                'Outreach drafted to your real metrics',
                'Reports yours forever',
              ]}
            />
          </div>
        </Reveal>
      </div>
    </section>
  )
}

function Column({ title, rows, muted = false }: { title: string; rows: string[]; muted?: boolean }) {
  return (
    <div
      className={`relative bg-sparq-charcoal p-8 text-left ${
        muted ? 'text-white/45' : 'text-white'
      }`}
    >
      <div
        className={`text-eyebrow uppercase ${
          muted ? 'text-white/35' : 'text-sparq-lime/80'
        }`}
      >
        {title}
      </div>
      <ul className="mt-5 space-y-3 text-[15px]">
        {rows.map((r) => (
          <li key={r} className="flex items-start gap-3">
            <span
              className={`mt-1.5 block h-1.5 w-1.5 flex-none rounded-full ${
                muted ? 'bg-white/25' : 'bg-sparq-lime'
              }`}
            />
            <span>{r}</span>
          </li>
        ))}
      </ul>
    </div>
  )
}
