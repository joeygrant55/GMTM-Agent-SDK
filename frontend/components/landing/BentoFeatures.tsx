'use client'

import Image from 'next/image'
import { motion } from 'framer-motion'
import { SectionHeader } from './_primitives/SectionHeader'
import { Reveal, Stagger, staggerItem } from './_primitives/Reveal'

type Feature = {
  title: string
  body: string
  image: string
  span?: string
  accent?: boolean
}

const FEATURES: Feature[] = [
  {
    title: 'Match to programs that actually want you.',
    body: 'Pulls from 2,900 programs, filters by coach needs, roster openings, academic fit, and region — not just rankings.',
    image: '/images/college-matching.png',
    span: 'lg:col-span-2 lg:row-span-2',
    accent: true,
  },
  {
    title: 'Know exactly where you rank.',
    body: 'Benchmarks your metrics against 75,000 real athletes at your position.',
    image: '/images/profile-analysis.png',
    span: 'lg:col-span-2',
  },
  {
    title: 'Skip hours of recruiting research.',
    body: 'Coaching staff, depth chart, recruiting class, NIL — researched in seconds.',
    image: '/images/deep-research.png',
    span: 'lg:col-span-2',
  },
  {
    title: 'Send the email coaches actually open.',
    body: 'Personalized to your real stats and their current recruiting needs.',
    image: '/images/coach-outreach.png',
    span: 'lg:col-span-2',
  },
  {
    title: 'Find camps that move the needle.',
    body: 'Combines, showcases, verified-metric days — near you.',
    image: '/images/camp-finder.png',
  },
  {
    title: 'Walk into every meeting with a report.',
    body: 'Every session saves to a report you own — share with coaches and family.',
    image: '/images/saved-reports.png',
  },
]

export function BentoFeatures() {
  return (
    <section id="features" className="relative py-24 sm:py-32 lg:py-40">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          eyebrow="What it does"
          title={
            <>
              Six tools. One agent.
              <br />
              Built for one job:{' '}
              <span className="text-sparq-lime">getting you recruited.</span>
            </>
          }
          sub="Every feature is built on real data — not a blog post, not a vibe. You get the same research an expensive consultant runs, delivered in the time it takes to read this paragraph."
        />

        <Stagger className="mt-16 grid grid-cols-1 gap-4 md:grid-cols-2 lg:grid-cols-4 lg:grid-rows-3">
          {FEATURES.map((f) => (
            <motion.div
              key={f.title}
              variants={staggerItem}
              className={f.span ?? ''}
            >
              {f.accent ? <HeroCard f={f} /> : <SmallCard f={f} />}
            </motion.div>
          ))}
        </Stagger>
      </div>
    </section>
  )
}

function HeroCard({ f }: { f: Feature }) {
  return (
    <div className="group relative h-full min-h-[340px] overflow-hidden rounded-2xl border border-sparq-lime/30 bg-gradient-to-br from-sparq-lime/[0.08] via-sparq-lime/[0.02] to-transparent p-8 shadow-card transition-all hover:border-sparq-lime/50 hover:shadow-lime-glow">
      {/* Image backdrop */}
      <div className="absolute inset-0 -z-10">
        <Image src={f.image} alt="" fill sizes="(min-width: 1024px) 50vw, 100vw" className="object-cover opacity-30 transition-transform duration-700 group-hover:scale-105" />
        <div className="absolute inset-0 bg-gradient-to-t from-sparq-charcoal via-sparq-charcoal/60 to-transparent" />
      </div>

      {/* Living content: animated fit bars */}
      <div className="pointer-events-none absolute right-6 top-6 w-44 rounded-xl border border-white/10 bg-sparq-charcoal/70 p-3 backdrop-blur-md">
        <div className="mb-2 flex items-center justify-between text-[10px] uppercase tracking-widest text-white/40">
          <span>Live matches</span>
          <span className="h-1.5 w-1.5 rounded-full bg-sparq-lime" />
        </div>
        {[94, 88, 82].map((v, i) => (
          <div key={i} className="mb-1.5 last:mb-0 flex items-center gap-2">
            <div className="h-5 w-5 flex-none rounded bg-white/10 text-[9px] leading-5 text-white/50 text-center">
              {['RU', 'YA', 'TU'][i]}
            </div>
            <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-white/10">
              <motion.div
                className="h-full bg-sparq-lime"
                initial={{ width: 0 }}
                whileInView={{ width: `${v}%` }}
                viewport={{ once: true, margin: '-10% 0px' }}
                transition={{ duration: 1, delay: i * 0.15, ease: [0.22, 1, 0.36, 1] }}
              />
            </div>
            <span className="text-[10px] tabular text-sparq-lime">{v}%</span>
          </div>
        ))}
      </div>

      <div className="relative mt-auto flex h-full flex-col justify-end">
        <div className="mb-3 text-eyebrow uppercase text-sparq-lime/80">Flagship</div>
        <h3 className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">
          {f.title}
        </h3>
        <p className="mt-4 max-w-md text-white/60">{f.body}</p>
      </div>
    </div>
  )
}

function SmallCard({ f }: { f: Feature }) {
  return (
    <div className="group relative h-full min-h-[220px] overflow-hidden rounded-2xl border border-white/10 bg-white/[0.025] p-6 transition-all hover:border-white/25 hover:bg-white/[0.04] hover:shadow-lime-glow-sm">
      <div className="relative grid h-full grid-cols-[1fr,auto] gap-4">
        <div className="flex flex-col justify-end">
          <h3 className="font-display text-xl font-semibold tracking-tight text-white">
            {f.title}
          </h3>
          <p className="mt-2 text-sm text-white/55 leading-relaxed">{f.body}</p>
        </div>
        <div className="relative h-24 w-24 overflow-hidden rounded-xl border border-white/5 bg-sparq-charcoal-light/50 transition-all duration-500 group-hover:-translate-y-1 group-hover:scale-[1.03]">
          <Image src={f.image} alt="" fill sizes="96px" className="object-cover opacity-80" />
        </div>
      </div>
      {/* subtle hover lime ring */}
      <div className="pointer-events-none absolute inset-0 rounded-2xl ring-1 ring-inset ring-sparq-lime/0 transition-colors duration-300 group-hover:ring-sparq-lime/20" />
    </div>
  )
}
