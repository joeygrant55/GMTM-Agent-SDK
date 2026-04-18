'use client'

import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { Reveal } from './_primitives/Reveal'

const FAQS = [
  {
    q: 'Can I cancel anytime?',
    a: 'Yes. Cancel from your dashboard in two clicks. Your saved reports stay yours.',
  },
  {
    q: 'Why is this so much cheaper than NCSA or IMG?',
    a: 'We don\u2019t sell you a consultant. We sell you an AI that draws on the same data the consultants use — 75,000 athletes, 2,900 programs, 7,832 scholarship offers — and works on your schedule, not theirs.',
  },
  {
    q: 'Does it work for D2, D3, and NAIA?',
    a: 'Yes. Our database covers NCAA D1/D2/D3 and NAIA programs, plus JUCO for select sports. The agent matches you across every division that fits your metrics and academics.',
  },
  {
    q: 'Do I need verified SPARQ metrics to get useful matches?',
    a: 'No. Self-reported metrics work for fit-matching and research. Verified SPARQ metrics unlock stronger coach-facing reports — we tell you when a camp near you can verify.',
  },
  {
    q: 'Does the agent contact coaches for me?',
    a: 'No. The agent drafts the email — you send it from your own inbox. Coaches want to hear from athletes, not bots. The drafts use your real metrics and the coach\u2019s current recruiting needs.',
  },
  {
    q: 'What sports do you support today?',
    a: 'Football, basketball, baseball, softball, volleyball, soccer, and track & field at launch. Lacrosse, hockey, and swimming are next.',
  },
]

export function FAQ() {
  return (
    <div className="mx-auto max-w-3xl">
      <Reveal>
        <div className="mb-8 text-center text-eyebrow uppercase text-sparq-lime/80">
          Common questions
        </div>
      </Reveal>
      <div className="space-y-2">
        {FAQS.map((f, i) => (
          <Item key={f.q} q={f.q} a={f.a} defaultOpen={i === 0} />
        ))}
      </div>
    </div>
  )
}

function Item({ q, a, defaultOpen = false }: { q: string; a: string; defaultOpen?: boolean }) {
  const [open, setOpen] = useState(defaultOpen)
  return (
    <div className="overflow-hidden rounded-xl border border-white/8 bg-white/[0.02]">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center justify-between gap-6 px-5 py-5 text-left text-[15px] font-medium text-white hover:bg-white/[0.02]"
      >
        <span>{q}</span>
        <motion.span
          animate={{ rotate: open ? 45 : 0 }}
          transition={{ duration: 0.3, ease: [0.22, 1, 0.36, 1] }}
          className="flex h-7 w-7 flex-none items-center justify-center rounded-full border border-white/15 text-white/60"
          aria-hidden
        >
          <svg viewBox="0 0 10 10" className="h-2.5 w-2.5 fill-current">
            <rect x="4.25" y="0" width="1.5" height="10" rx="0.75" />
            <rect x="0" y="4.25" width="10" height="1.5" rx="0.75" />
          </svg>
        </motion.span>
      </button>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            key="body"
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.4, ease: [0.22, 1, 0.36, 1] }}
          >
            <div className="px-5 pb-6 text-[14px] leading-relaxed text-white/60">{a}</div>
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  )
}
