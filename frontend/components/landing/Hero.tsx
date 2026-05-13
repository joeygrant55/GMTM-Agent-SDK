'use client'

import Link from 'next/link'
import Image from 'next/image'
import { motion } from 'framer-motion'
import { LiveDemoPreview } from './LiveDemoPreview'
import { LimeAura } from './_primitives/LimeAura'
import { Reveal } from './_primitives/Reveal'

const EASE = [0.22, 1, 0.36, 1] as const

export function Hero() {
  return (
    <section className="relative overflow-hidden pt-28 sm:pt-36 lg:pt-44 pb-20 lg:pb-28">
      {/* Background image + overlays */}
      <div aria-hidden className="absolute inset-0 -z-10">
        <Image
          src="/images/hero-bg.png"
          alt=""
          fill
          priority
          sizes="100vw"
          className="object-cover opacity-[0.10]"
        />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top,rgba(200,255,0,0.08),transparent_60%)]" />
        <div className="absolute inset-0 bg-gradient-to-b from-sparq-charcoal/60 via-sparq-charcoal/80 to-sparq-charcoal" />
        <GridBackdrop />
      </div>

      <LimeAura size={720} opacity={0.18} className="right-[-180px] top-[120px] hidden lg:block" />
      <LimeAura size={520} opacity={0.1} className="left-[-160px] top-[300px] hidden lg:block" />

      <div className="relative mx-auto grid max-w-7xl grid-cols-1 gap-12 px-6 lg:grid-cols-12 lg:items-center lg:gap-16">
        {/* Left */}
        <div className="relative z-10 lg:col-span-6">
          <Reveal>
            <div className="mb-7 inline-flex items-center gap-2 rounded-full border border-white/10 bg-white/[0.03] px-3 py-1 text-xs">
              <span className="relative flex h-2 w-2">
                <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-sparq-lime opacity-60" />
                <span className="relative inline-flex h-2 w-2 rounded-full bg-sparq-lime" />
              </span>
              <span className="tracking-wider text-white/70">LIVE · AI AGENT ONLINE</span>
            </div>
          </Reveal>

          <motion.h1
            initial={{ opacity: 0, y: 18 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.8, ease: EASE }}
            className="font-display text-display-xl font-semibold tracking-tight text-white"
          >
            The recruiting platform
            <br className="hidden sm:block" /> built for{' '}
            <span className="relative whitespace-nowrap text-sparq-lime">
              women&rsquo;s flag football
              <svg
                aria-hidden
                viewBox="0 0 300 16"
                className="absolute left-0 right-0 -bottom-2 w-full"
                preserveAspectRatio="none"
              >
                <motion.path
                  d="M2 10 C 60 2, 150 2, 298 8"
                  fill="none"
                  stroke="#c8ff00"
                  strokeWidth="2"
                  strokeLinecap="round"
                  initial={{ pathLength: 0, opacity: 0 }}
                  animate={{ pathLength: 1, opacity: 0.8 }}
                  transition={{ duration: 1.1, delay: 0.6, ease: EASE }}
                />
              </svg>
            </span>
            .
          </motion.h1>

          <Reveal delay={0.2}>
            <p className="mt-8 max-w-xl text-lg text-white/60 leading-relaxed">
              Every active college program. <span className="text-white">Reach, Target, Likely</span>{' '}
              matches based on your stats, class year, and where you want to play. The recruiting
              consultant your family couldn&rsquo;t afford &mdash; for{' '}
              <span className="text-white">$29/month</span>.
            </p>
          </Reveal>

          <Reveal delay={0.3}>
            <div className="mt-10 flex flex-wrap items-center gap-3">
              <Link
                href="/onboarding/search"
                className="group inline-flex items-center gap-2 rounded-full bg-sparq-lime px-6 py-3.5 text-base font-semibold text-sparq-charcoal shadow-lime-glow transition-all hover:bg-sparq-lime-light hover:shadow-lime-glow focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-sparq-lime focus-visible:ring-offset-2 focus-visible:ring-offset-sparq-charcoal"
              >
                Start free
                <span className="transition-transform group-hover:translate-x-0.5">→</span>
              </Link>
              <Link
                href="/demo"
                className="inline-flex items-center gap-2 rounded-full border border-white/15 bg-white/[0.03] px-6 py-3.5 text-base font-medium text-white transition-colors hover:bg-white/[0.08]"
              >
                <span className="flex h-5 w-5 items-center justify-center rounded-full bg-white/10">
                  <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 fill-white">
                    <polygon points="2,1 9,5 2,9" />
                  </svg>
                </span>
                Watch the demo
              </Link>
            </div>
          </Reveal>

          <Reveal delay={0.45}>
            <div className="mt-12 flex flex-wrap items-center gap-x-6 gap-y-2 text-eyebrow uppercase text-white/35">
              <span>71 active college programs</span>
              <Dot />
              <span>NCAA · NAIA · NJCAA</span>
              <Dot />
              <span>LA28 Olympic sport</span>
            </div>
          </Reveal>
        </div>

        {/* Right — live demo */}
        <motion.div
          initial={{ opacity: 0, y: 30, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.9, delay: 0.3, ease: EASE }}
          className="relative lg:col-span-6"
        >
          <LimeAura size={560} opacity={0.22} className="inset-0 m-auto" />
          <LiveDemoPreview />
        </motion.div>
      </div>
    </section>
  )
}

function Dot() {
  return <span aria-hidden className="inline-block h-1 w-1 rounded-full bg-white/25" />
}

function GridBackdrop() {
  return (
    <div
      className="absolute inset-0 opacity-[0.15]"
      style={{
        backgroundImage:
          'linear-gradient(to right, rgba(255,255,255,0.06) 1px, transparent 1px), linear-gradient(to bottom, rgba(255,255,255,0.06) 1px, transparent 1px)',
        backgroundSize: '56px 56px',
        maskImage: 'radial-gradient(ellipse at top, black 40%, transparent 75%)',
        WebkitMaskImage: 'radial-gradient(ellipse at top, black 40%, transparent 75%)',
      }}
    />
  )
}
