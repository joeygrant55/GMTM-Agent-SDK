import { ReactNode } from 'react'
import { Reveal } from './Reveal'

export function SectionHeader({
  eyebrow,
  title,
  sub,
  align = 'left',
  className = '',
}: {
  eyebrow?: string
  title: ReactNode
  sub?: ReactNode
  align?: 'left' | 'center'
  className?: string
}) {
  const alignCls = align === 'center' ? 'text-center mx-auto' : 'text-left'
  return (
    <div className={`max-w-3xl ${alignCls} ${className}`}>
      {eyebrow && (
        <Reveal>
          <div className="mb-5 flex items-center gap-2 text-eyebrow uppercase text-sparq-lime/80">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-sparq-lime" />
            {eyebrow}
          </div>
        </Reveal>
      )}
      <Reveal delay={0.05}>
        <h2 className="text-display-lg font-display font-semibold tracking-tight text-white">
          {title}
        </h2>
      </Reveal>
      {sub && (
        <Reveal delay={0.1}>
          <p className="mt-5 text-lg text-white/60 leading-relaxed max-w-2xl">
            {sub}
          </p>
        </Reveal>
      )}
    </div>
  )
}
