'use client'

import { useEffect, useReducer, useRef } from 'react'
import { motion, AnimatePresence, useInView, useReducedMotion } from 'framer-motion'

const EASE = [0.22, 1, 0.36, 1] as const

const USER_MSG = "I'm a 6'2\" QB in Texas. 4.1 GPA, 1180 SAT. Where can I play D1?"
const AGENT_MSG =
  "Based on your metrics, academics, and region, you're a competitive recruit at Group of 5 and Ivy programs. Here are 5 programs actively recruiting your profile:"

type College = {
  monogram: string
  name: string
  conference: string
  fit: number
  reason: string
}

const COLLEGES: College[] = [
  {
    monogram: 'RU',
    name: 'Rice University',
    conference: 'American',
    fit: 94,
    reason: 'Active 2027 QB search · Pro-style offense · Texas pipeline',
  },
  {
    monogram: 'SMU',
    name: 'SMU Mustangs',
    conference: 'ACC',
    fit: 91,
    reason: 'Spread offense fit · In-state advantage · Strong academics match',
  },
  {
    monogram: 'TU',
    name: 'Tulane',
    conference: 'American',
    fit: 88,
    reason: 'QB class of 2027 open · Southern recruiting footprint',
  },
  {
    monogram: 'YA',
    name: 'Yale',
    conference: 'Ivy',
    fit: 86,
    reason: 'Academic index strong · Likely FAFSA fit · Pro-style system',
  },
  {
    monogram: 'AF',
    name: 'Air Force',
    conference: 'Mountain West',
    fit: 82,
    reason: 'Option offense · Character profile match · Nationwide recruiting',
  },
]

type Step =
  | { kind: 'idle' }
  | { kind: 'user'; typed: number }
  | { kind: 'thinking' }
  | { kind: 'agent'; typed: number }
  | { kind: 'cards'; shown: number }
  | { kind: 'rest' }

type Action = { type: 'tick'; payload?: number } | { type: 'advance' } | { type: 'reset' }

function reduce(state: Step, action: Action): Step {
  switch (action.type) {
    case 'reset':
      return { kind: 'idle' }
    case 'advance':
      switch (state.kind) {
        case 'idle':
          return { kind: 'user', typed: 0 }
        case 'user':
          return { kind: 'thinking' }
        case 'thinking':
          return { kind: 'agent', typed: 0 }
        case 'agent':
          return { kind: 'cards', shown: 0 }
        case 'cards':
          return { kind: 'rest' }
        case 'rest':
          return { kind: 'idle' }
      }
    case 'tick':
      if (state.kind === 'user')
        return { kind: 'user', typed: Math.min(USER_MSG.length, state.typed + 1) }
      if (state.kind === 'agent')
        return { kind: 'agent', typed: Math.min(AGENT_MSG.length, state.typed + 2) }
      if (state.kind === 'cards')
        return { kind: 'cards', shown: Math.min(COLLEGES.length, state.shown + 1) }
      return state
  }
}

export function LiveDemoPreview() {
  const [state, dispatch] = useReducer(reduce, { kind: 'idle' } as Step)
  const wrapRef = useRef<HTMLDivElement>(null)
  const panelRef = useRef<HTMLDivElement>(null)
  const inView = useInView(wrapRef, { margin: '-10% 0px' })
  const reduced = useReducedMotion()

  useEffect(() => {
    if (reduced) {
      dispatch({ type: 'reset' })
      dispatch({ type: 'advance' }) // user
      dispatch({ type: 'advance' }) // thinking
      dispatch({ type: 'advance' }) // agent
      dispatch({ type: 'advance' }) // cards
      return
    }
    if (!inView) return
    let active = true
    let timers: ReturnType<typeof setTimeout>[] = []
    const wait = (ms: number) =>
      new Promise<void>((res) => {
        const t = setTimeout(() => res(), ms)
        timers.push(t)
      })

    async function run() {
      while (active) {
        dispatch({ type: 'reset' })
        await wait(500)
        if (!active) return
        dispatch({ type: 'advance' }) // -> user typing
        for (let i = 0; i < USER_MSG.length; i++) {
          if (!active) return
          await wait(22 + Math.random() * 22)
          dispatch({ type: 'tick' })
        }
        await wait(500)
        if (!active) return
        dispatch({ type: 'advance' }) // -> thinking
        await wait(1500)
        if (!active) return
        dispatch({ type: 'advance' }) // -> agent typing
        const steps = Math.ceil(AGENT_MSG.length / 2)
        for (let i = 0; i < steps; i++) {
          if (!active) return
          await wait(22)
          dispatch({ type: 'tick' })
        }
        await wait(400)
        if (!active) return
        dispatch({ type: 'advance' }) // -> cards
        for (let i = 0; i < COLLEGES.length; i++) {
          if (!active) return
          await wait(380)
          dispatch({ type: 'tick' })
        }
        await wait(3200)
        if (!active) return
        dispatch({ type: 'advance' }) // -> rest
        await wait(600)
      }
    }
    run()
    return () => {
      active = false
      timers.forEach(clearTimeout)
    }
  }, [inView, reduced])

  function onMouseMove(e: React.MouseEvent<HTMLDivElement>) {
    if (reduced) return
    const el = panelRef.current
    if (!el) return
    const r = el.getBoundingClientRect()
    const x = (e.clientX - r.left) / r.width - 0.5
    const y = (e.clientY - r.top) / r.height - 0.5
    el.style.transform = `perspective(1200px) rotateX(${(-y * 4).toFixed(2)}deg) rotateY(${(x * 5).toFixed(2)}deg)`
  }
  function onMouseLeave() {
    if (panelRef.current) panelRef.current.style.transform = 'perspective(1200px) rotateX(0) rotateY(0)'
  }

  const userTyped = state.kind === 'user' ? USER_MSG.slice(0, state.typed) : USER_MSG
  const agentTyped = state.kind === 'agent' ? AGENT_MSG.slice(0, state.typed) : state.kind === 'cards' || state.kind === 'rest' ? AGENT_MSG : ''
  const shownCards = state.kind === 'cards' ? state.shown : state.kind === 'rest' ? COLLEGES.length : 0

  return (
    <div ref={wrapRef} className="relative w-full" onMouseMove={onMouseMove} onMouseLeave={onMouseLeave}>
      <div
        ref={panelRef}
        className="relative rounded-2xl gradient-border bg-sparq-charcoal-light/80 shadow-card transition-transform duration-150 will-change-transform"
        style={{ transformStyle: 'preserve-3d' }}
      >
        <div className="relative overflow-hidden rounded-2xl">
          {/* Chrome */}
          <div className="flex items-center gap-2 border-b border-white/5 px-4 py-3">
            <div className="flex gap-1.5">
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
              <span className="h-2.5 w-2.5 rounded-full bg-white/15" />
            </div>
            <div className="mx-auto flex items-center gap-2 rounded-md bg-white/[0.04] px-3 py-1 text-xs text-white/40">
              <span className="h-1.5 w-1.5 rounded-full bg-sparq-lime shadow-[0_0_8px_#c8ff00]" />
              sparq-agent.ai
            </div>
            <div className="w-10" />
          </div>

          {/* Body */}
          <div className="relative min-h-[520px] p-5">
            <AnimatePresence mode="wait">
              {state.kind !== 'idle' && (
                <motion.div
                  key="user"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.35, ease: EASE }}
                  className="mb-4 flex justify-end"
                >
                  <div className="max-w-[80%] rounded-2xl rounded-br-sm bg-sparq-lime/15 px-4 py-2.5 text-sm text-white ring-1 ring-sparq-lime/30">
                    {userTyped}
                    {state.kind === 'user' && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-sparq-lime animate-blink" />}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>

            {state.kind === 'thinking' && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="mb-4 flex items-center gap-2 text-xs text-white/50"
              >
                <span className="relative block h-[3px] w-24 overflow-hidden rounded-full bg-white/10">
                  <span className="absolute inset-y-0 block bg-sparq-lime animate-thinking-progress" />
                </span>
                Thinking · searching every active flag football program
              </motion.div>
            )}

            {(state.kind === 'agent' || state.kind === 'cards' || state.kind === 'rest') && (
              <motion.div
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.35, ease: EASE }}
                className="mb-4 max-w-[92%] text-sm leading-relaxed text-white/80"
              >
                {agentTyped}
                {state.kind === 'agent' && <span className="ml-0.5 inline-block h-4 w-[2px] translate-y-0.5 bg-sparq-lime animate-blink" />}
              </motion.div>
            )}

            <div className="grid grid-cols-1 gap-2.5">
              {COLLEGES.slice(0, shownCards).map((c, i) => (
                <CollegeRow key={c.name} c={c} i={i} />
              ))}
            </div>

            {/* Soft bottom fade */}
            <div className="pointer-events-none absolute inset-x-0 bottom-0 h-12 bg-gradient-to-t from-sparq-charcoal-light/90 to-transparent" />
          </div>
        </div>
      </div>
    </div>
  )
}

function CollegeRow({ c, i }: { c: College; i: number }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.45, delay: i * 0.03, ease: [0.22, 1, 0.36, 1] }}
      className="group flex items-center gap-3 rounded-xl border border-white/5 bg-white/[0.02] px-3 py-2.5 transition-colors hover:border-sparq-lime/30"
    >
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-sparq-lime/15 text-xs font-semibold text-sparq-lime ring-1 ring-sparq-lime/30">
        {c.monogram}
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <div className="truncate text-sm font-medium text-white">{c.name}</div>
          <span className="rounded-full border border-white/10 px-1.5 py-0.5 text-[10px] uppercase tracking-wider text-white/50">
            {c.conference}
          </span>
        </div>
        <div className="mt-0.5 truncate text-xs text-white/50">{c.reason}</div>
      </div>
      <div className="flex flex-col items-end gap-1">
        <div className="text-xs font-semibold text-sparq-lime tabular">{c.fit}%</div>
        <div className="h-1 w-16 overflow-hidden rounded-full bg-white/10">
          <motion.div
            initial={{ width: 0 }}
            animate={{ width: `${c.fit}%` }}
            transition={{ duration: 0.9, delay: i * 0.04 + 0.2, ease: [0.22, 1, 0.36, 1] }}
            className="h-full bg-sparq-lime"
          />
        </div>
      </div>
    </motion.div>
  )
}
