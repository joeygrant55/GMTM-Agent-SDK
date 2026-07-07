'use client'

import { CountUp } from './_primitives/CountUp'
import { Reveal, Stagger, staggerItem } from './_primitives/Reveal'
import { motion } from 'framer-motion'

export function ProofBar() {
  return (
    <section className="relative border-y border-white/5 bg-white/[0.015]">
      <div className="pointer-events-none absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-sparq-lime/40 to-transparent" />
      <div className="pointer-events-none absolute inset-x-0 bottom-0 h-px bg-gradient-to-r from-transparent via-sparq-lime/40 to-transparent" />
      <Stagger className="mx-auto grid max-w-7xl grid-cols-2 gap-y-10 px-6 py-16 md:grid-cols-5 md:gap-0 md:divide-x md:divide-white/5">
        <Stat value={68} suffix="" label="Athletes sent to 2026 USA Flag national team trials" />
        <Stat value={64.6} suffix="%" format={(n) => n.toFixed(1)} label="Of Adult Men trial invites came through our combines" />
        <Stat value={100} suffix="+" label="College flag programs — most recruiting founding rosters" />
        <Stat value={131000} suffix="" format={(n) => `${(n / 1000).toFixed(0)}K`} label="Verified performance metrics" />
        <ShiftStat />
      </Stagger>
    </section>
  )
}

function Stat({
  value,
  suffix = '',
  label,
  format,
}: {
  value: number
  suffix?: string
  label: string
  format?: (n: number) => string
}) {
  return (
    <motion.div variants={staggerItem} className="flex flex-col items-center px-6 text-center md:items-start md:text-left">
      <div className="font-display text-3xl font-semibold tracking-tight text-white sm:text-4xl">
        <CountUp to={value} format={format} suffix={suffix} />
      </div>
      <div className="mt-2 text-sm text-white/50">{label}</div>
    </motion.div>
  )
}

function ShiftStat() {
  return (
    <motion.div variants={staggerItem} className="col-span-2 flex flex-col items-center px-6 text-center md:col-span-1 md:items-start md:text-left">
      <div className="flex items-baseline gap-3">
        <span className="font-display text-xl text-white/35 line-through">$5,000</span>
        <span className="font-display text-3xl font-semibold tracking-tight text-sparq-lime sm:text-4xl">$29</span>
      </div>
      <div className="mt-2 text-sm text-white/50">Per month, not per year</div>
    </motion.div>
  )
}
