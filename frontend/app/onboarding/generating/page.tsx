'use client'

import { useEffect, useRef, useState } from 'react'
import { useRouter } from 'next/navigation'

const STEPS = [
  'Importing MaxPreps profile...',
  'Analyzing your season stats...',
  'Running against 75,000 athletes...',
  'Computing percentile rankings...',
  'Matching 2,932 college programs...',
  'Building your college target list...',
  'Recruiting workspace ready...',
]

const STEP_DURATIONS_MS = [450, 750, 1200, 900, 1200, 950, 550]

function AgentToolCallFeed() {
  const [visibleCount, setVisibleCount] = useState(0)
  const [completedSteps, setCompletedSteps] = useState(-1)

  useEffect(() => {
    const timers: ReturnType<typeof setTimeout>[] = []
    let elapsed = 0

    STEPS.forEach((_, index) => {
      timers.push(setTimeout(() => setVisibleCount(index + 1), elapsed))
      elapsed += STEP_DURATIONS_MS[index]
      timers.push(setTimeout(() => setCompletedSteps(index), elapsed))
    })

    return () => timers.forEach(clearTimeout)
  }, [])

  return (
    <div className="rounded-xl border border-white/10 bg-black/40 overflow-hidden">
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/5 bg-white/[0.02]">
        <div className="flex gap-1.5">
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
          <div className="w-2.5 h-2.5 rounded-full bg-white/10" />
        </div>
        <span className="text-[11px] text-gray-500 font-mono ml-2">sparq-agent onboarding</span>
      </div>
      <div className="px-4 py-3 space-y-1">
        {STEPS.map((step, index) => {
          if (index >= visibleCount) return null
          const isDone = index <= completedSteps
          const isCurrent = index === visibleCount - 1 && !isDone

          return (
            <div key={step} className="flex items-center gap-2.5 font-mono text-sm animate-fadeIn">
              <span className="w-4 text-center">
                {isDone ? (
                  <span className="text-sparq-lime font-bold">✓</span>
                ) : isCurrent ? (
                  <span className="inline-block w-3.5 h-3.5 border-2 border-sparq-lime border-t-transparent rounded-full animate-spin" />
                ) : (
                  <span className="text-gray-600">○</span>
                )}
              </span>
              <span className={isDone ? 'text-gray-400' : isCurrent ? 'text-white' : 'text-gray-600'}>{step}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

export default function GeneratingPage() {
  const router = useRouter()
  const redirected = useRef(false)

  useEffect(() => {
    const total = STEP_DURATIONS_MS.reduce((acc, value) => acc + value, 0)
    const timer = setTimeout(() => {
      if (redirected.current) return
      redirected.current = true
      router.push('/onboarding/welcome')
    }, total)

    return () => clearTimeout(timer)
  }, [router])

  return (
    <div className="min-h-screen bg-sparq-charcoal text-white flex items-center justify-center px-4">
      <div className="w-full max-w-2xl">
        <div className="text-center mb-8">
          <p className="text-sm font-semibold tracking-widest text-sparq-lime uppercase">Step 4 of 4</p>
          <h1 className="mt-3 text-4xl font-black">Building Your Workspace</h1>
          <p className="mt-3 text-gray-400">We&apos;re creating your recruiting profile and target list.</p>
        </div>

        <AgentToolCallFeed />
      </div>
    </div>
  )
}
