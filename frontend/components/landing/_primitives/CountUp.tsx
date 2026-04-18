'use client'

import { useEffect, useRef, useState } from 'react'
import { useInView } from 'framer-motion'

export function CountUp({
  to,
  duration = 1400,
  format = (n: number) => Math.round(n).toLocaleString(),
  className,
  suffix = '',
  prefix = '',
}: {
  to: number
  duration?: number
  format?: (n: number) => string
  className?: string
  suffix?: string
  prefix?: string
}) {
  const ref = useRef<HTMLSpanElement>(null)
  const inView = useInView(ref, { once: true, margin: '-10% 0px' })
  const [val, setVal] = useState(0)

  useEffect(() => {
    if (!inView) return
    let raf = 0
    const start = performance.now()
    const ease = (t: number) => 1 - Math.pow(1 - t, 4)
    const step = (now: number) => {
      const t = Math.min(1, (now - start) / duration)
      setVal(to * ease(t))
      if (t < 1) raf = requestAnimationFrame(step)
    }
    raf = requestAnimationFrame(step)
    return () => cancelAnimationFrame(raf)
  }, [inView, to, duration])

  return (
    <span ref={ref} className={`tabular ${className ?? ''}`}>
      {prefix}
      {format(val)}
      {suffix}
    </span>
  )
}
