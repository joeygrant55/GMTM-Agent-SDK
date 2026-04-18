'use client'

import { useRef } from 'react'
import { motion, useScroll, useTransform } from 'framer-motion'
import { SectionHeader } from './_primitives/SectionHeader'
import { Reveal } from './_primitives/Reveal'

const STEPS = [
  {
    n: '01',
    title: 'Create your profile',
    body: 'Sign up, connect your athlete profile, add film and socials. Two minutes.',
    mock: <ProfileMock />,
  },
  {
    n: '02',
    title: 'Ask your agent',
    body: 'Any question about recruiting. The agent researches the web, searches SPARQ data, and writes back.',
    mock: <ChatMock />,
  },
  {
    n: '03',
    title: 'Take action',
    body: 'Email coaches, lock camps, build a report. Walk into every meeting prepared.',
    mock: <ReportMock />,
  },
]

export function HowItWorks() {
  const ref = useRef<HTMLDivElement>(null)
  const { scrollYProgress } = useScroll({ target: ref, offset: ['start 80%', 'end 30%'] })
  const scaleX = useTransform(scrollYProgress, [0, 1], [0, 1])

  return (
    <section id="how" className="relative border-y border-white/5 bg-sparq-charcoal-light/40 py-24 sm:py-32 lg:py-40">
      <div className="mx-auto max-w-7xl px-6">
        <SectionHeader
          eyebrow="How it works"
          title={
            <>
              Three steps.
              <br />
              Then the agent does the work.
            </>
          }
          sub="You bring your profile. The agent brings 2,900 programs, every recent coaching move, and every tool you'd need. Then you send emails and show up prepared."
        />

        <div ref={ref} className="mt-20 relative">
          {/* Horizontal progress line on desktop */}
          <div className="pointer-events-none absolute left-0 right-0 top-[72px] hidden lg:block">
            <div className="relative mx-auto h-[2px] w-[88%] overflow-hidden rounded-full bg-white/8">
              <motion.div
                style={{ scaleX }}
                className="absolute inset-0 origin-left bg-gradient-to-r from-sparq-lime via-sparq-lime/80 to-sparq-lime/30"
              />
            </div>
          </div>

          <div className="grid grid-cols-1 gap-14 lg:grid-cols-3 lg:gap-10">
            {STEPS.map((s, i) => (
              <Reveal key={s.n} delay={i * 0.1} className="relative">
                <div className="relative z-10 mb-8 flex h-[144px] items-start justify-center lg:justify-start">
                  <div className="relative">
                    <div className="relative flex h-14 w-14 items-center justify-center rounded-full border border-sparq-lime/40 bg-sparq-charcoal font-display text-sm font-semibold tracking-widest text-sparq-lime">
                      {s.n}
                      <span className="absolute inset-0 -z-10 rounded-full bg-sparq-lime/10 blur-xl" />
                    </div>
                  </div>
                </div>
                <h3 className="font-display text-2xl font-semibold tracking-tight text-white">
                  {s.title}
                </h3>
                <p className="mt-3 max-w-sm text-white/55 leading-relaxed">{s.body}</p>
                <div className="mt-8">{s.mock}</div>
              </Reveal>
            ))}
          </div>
        </div>
      </div>
    </section>
  )
}

function ProfileMock() {
  return (
    <div className="rounded-2xl border border-white/8 bg-sparq-charcoal/60 p-5 backdrop-blur-sm">
      <div className="mb-4 flex items-center gap-3">
        <div className="h-10 w-10 rounded-full bg-gradient-to-br from-sparq-lime/70 to-sparq-lime/30 ring-1 ring-sparq-lime/40" />
        <div>
          <div className="text-sm font-semibold">Jordan M.</div>
          <div className="text-xs text-white/40">QB · Class of 2027 · Dallas, TX</div>
        </div>
      </div>
      <div className="grid grid-cols-3 gap-2 text-center">
        {[
          ['6\'2"', 'Height'],
          ['4.62', '40-yard'],
          ['4.1', 'GPA'],
        ].map(([v, k]) => (
          <div key={k} className="rounded-lg border border-white/5 bg-white/[0.02] py-2">
            <div className="text-sm font-semibold text-sparq-lime tabular">{v}</div>
            <div className="text-[10px] uppercase tracking-widest text-white/40">{k}</div>
          </div>
        ))}
      </div>
    </div>
  )
}

function ChatMock() {
  return (
    <div className="space-y-2 rounded-2xl border border-white/8 bg-sparq-charcoal/60 p-5 backdrop-blur-sm">
      <div className="flex justify-end">
        <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-sparq-lime/15 px-3 py-2 text-xs text-white ring-1 ring-sparq-lime/30">
          Which D2 programs recruit 5&apos;10&quot; point guards?
        </div>
      </div>
      <div className="flex items-center gap-2 pl-1 text-xs text-white/50">
        <span className="relative block h-[3px] w-20 overflow-hidden rounded-full bg-white/10">
          <span className="absolute inset-y-0 block bg-sparq-lime animate-thinking-progress" />
        </span>
        Searching 2,900 programs…
      </div>
      <div className="flex">
        <div className="max-w-[90%] rounded-2xl rounded-bl-sm bg-white/[0.05] px-3 py-2 text-xs text-white/80 ring-1 ring-white/10">
          Found 14 programs with open 2027 PG spots and academic fit…
        </div>
      </div>
    </div>
  )
}

function ReportMock() {
  return (
    <div className="rounded-2xl border border-white/8 bg-sparq-charcoal/60 p-5 backdrop-blur-sm">
      <div className="mb-3 flex items-center justify-between">
        <div className="text-xs font-semibold text-white">College Fit Report</div>
        <div className="text-[10px] uppercase tracking-widest text-sparq-lime/80">Saved · Mar 4</div>
      </div>
      <div className="space-y-2">
        {[
          ['Rice Owls', 94],
          ['Yale Bulldogs', 88],
          ['Tulane Green Wave', 84],
        ].map(([n, v]) => (
          <div key={n as string} className="flex items-center gap-3">
            <div className="flex-1 text-xs text-white/80">{n}</div>
            <div className="h-1 w-20 overflow-hidden rounded-full bg-white/10">
              <div className="h-full bg-sparq-lime" style={{ width: `${v}%` }} />
            </div>
            <div className="w-9 text-right text-[11px] font-semibold text-sparq-lime tabular">{v}%</div>
          </div>
        ))}
      </div>
      <button className="mt-4 w-full rounded-lg border border-white/10 px-3 py-2 text-xs text-white/70 hover:bg-white/5">
        Share with coach →
      </button>
    </div>
  )
}
