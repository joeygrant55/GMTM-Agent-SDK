'use client'

import Link from 'next/link'
import { motion } from 'framer-motion'
import { SectionHeader } from './_primitives/SectionHeader'
import { Reveal } from './_primitives/Reveal'
import { LimeAura } from './_primitives/LimeAura'
import { FAQ } from './FAQ'

const FREE = {
  name: 'Free',
  price: '$0',
  cadence: '/month',
  perks: [
    '3 conversations per month',
    'Basic profile analysis',
    'Camp & combine finder',
    '1 saved report',
  ],
  cta: { label: 'Get started', href: '/onboarding/search' },
}

const PREMIUM = {
  name: 'Premium',
  price: '$29',
  cadence: '/month',
  perks: [
    'Unlimited conversations',
    'Deep college fit reports with reasons',
    'Coach email drafting',
    'Recruiting calendar alerts',
    'Unlimited saved reports',
    'Priority research queue',
  ],
  cta: { label: 'Start free trial', href: '/onboarding/search' },
}

export function Pricing() {
  return (
    <section id="pricing" className="relative overflow-hidden py-24 sm:py-32 lg:py-40">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          align="center"
          eyebrow="Pricing"
          title={
            <>
              Less than <span className="line-through decoration-sparq-lime/60 decoration-2">one hour</span>{' '}
              with a recruiting consultant.
              <br />
              <span className="text-sparq-lime">Forever.</span>
            </>
          }
          sub={`$29/month for the full agent, or a free tier that\u2019ll get you started. Cancel anytime — your reports are yours.`}
        />

        <div className="mx-auto mt-16 grid max-w-5xl grid-cols-1 gap-6 lg:grid-cols-2">
          <Reveal className="h-full">
            <Card tier={FREE} />
          </Reveal>
          <Reveal delay={0.1} className="h-full">
            <PremiumCard />
          </Reveal>
        </div>

        <div className="mt-24">
          <FAQ />
        </div>
      </div>
    </section>
  )
}

function Card({ tier }: { tier: typeof FREE }) {
  return (
    <div className="flex h-full flex-col rounded-3xl border border-white/10 bg-white/[0.025] p-8 sm:p-10">
      <div className="text-eyebrow uppercase text-white/45">{tier.name}</div>
      <div className="mt-5 flex items-baseline gap-2">
        <span className="font-display text-6xl font-semibold tracking-tight text-white">
          {tier.price}
        </span>
        <span className="text-sm text-white/50">{tier.cadence}</span>
      </div>
      <div className="mt-1 text-sm text-white/40">For athletes just getting started.</div>
      <ul className="mt-8 space-y-3.5">
        {tier.perks.map((p) => (
          <Check key={p}>{p}</Check>
        ))}
      </ul>
      <Link
        href={tier.cta.href}
        className="mt-auto inline-flex items-center justify-center gap-1.5 rounded-full border border-white/20 px-6 py-3 text-sm font-semibold text-white hover:bg-white/5 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sparq-lime focus-visible:ring-offset-2 focus-visible:ring-offset-sparq-charcoal"
      >
        {tier.cta.label}
        <span>→</span>
      </Link>
    </div>
  )
}

function PremiumCard() {
  return (
    <div className="relative h-full">
      <LimeAura size={520} opacity={0.22} pulse className="left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2" />
      <div className="relative h-full rounded-3xl gradient-border gradient-border-animated bg-sparq-charcoal-light/80 shadow-lime-glow">
        <div className="relative flex h-full flex-col rounded-3xl p-8 sm:p-10">
          <motion.div
            initial={{ y: -6, opacity: 0 }}
            whileInView={{ y: 0, opacity: 1 }}
            viewport={{ once: true }}
            transition={{ type: 'spring', stiffness: 300, damping: 20 }}
            className="absolute -top-3 left-8 rounded-full bg-sparq-lime px-3 py-1 text-[10px] font-bold uppercase tracking-widest text-sparq-charcoal"
          >
            Most popular
          </motion.div>
          <div className="text-eyebrow uppercase text-sparq-lime/80">{PREMIUM.name}</div>
          <div className="mt-5 flex items-baseline gap-2">
            <span className="font-display text-7xl font-semibold tracking-tight text-white">
              {PREMIUM.price}
            </span>
            <span className="text-sm text-white/50">{PREMIUM.cadence}</span>
          </div>
          <div className="mt-2 text-sm text-white/55">
            vs <span className="text-white/35 line-through">$5,000/yr</span> at NCSA or IMG — per year.
          </div>
          <ul className="mt-8 space-y-3.5">
            {PREMIUM.perks.map((p) => (
              <Check key={p} accent>
                {p}
              </Check>
            ))}
          </ul>
          <Link
            href={PREMIUM.cta.href}
            className="mt-auto inline-flex items-center justify-center gap-1.5 rounded-full bg-sparq-lime px-6 py-3 text-sm font-bold text-sparq-charcoal shadow-lime-glow-sm hover:bg-sparq-lime-light focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sparq-lime focus-visible:ring-offset-2 focus-visible:ring-offset-sparq-charcoal"
          >
            {PREMIUM.cta.label}
            <span>→</span>
          </Link>
        </div>
      </div>
    </div>
  )
}

function Check({ children, accent = false }: { children: React.ReactNode; accent?: boolean }) {
  return (
    <li className="flex items-start gap-3">
      <span
        className={`mt-0.5 flex h-5 w-5 flex-none items-center justify-center rounded-full ${
          accent ? 'bg-sparq-lime text-sparq-charcoal' : 'border border-white/15 text-white/70'
        }`}
      >
        <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 fill-none stroke-current" strokeWidth={1.8} strokeLinecap="round" strokeLinejoin="round">
          <polyline points="1.8,5 4.2,7.3 8.2,2.8" />
        </svg>
      </span>
      <span className={`text-[15px] ${accent ? 'text-white' : 'text-white/70'}`}>{children}</span>
    </li>
  )
}
