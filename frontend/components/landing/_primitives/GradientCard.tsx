import { ReactNode } from 'react'

export function GradientCard({
  children,
  className = '',
  animated = false,
  inner = 'bg-white/[0.035]',
}: {
  children: ReactNode
  className?: string
  animated?: boolean
  inner?: string
}) {
  return (
    <div
      className={`relative rounded-2xl gradient-border ${animated ? 'gradient-border-animated' : ''} ${className}`}
    >
      <div
        className={`relative h-full w-full rounded-2xl ${inner} backdrop-blur-[2px]`}
      >
        {children}
      </div>
    </div>
  )
}
