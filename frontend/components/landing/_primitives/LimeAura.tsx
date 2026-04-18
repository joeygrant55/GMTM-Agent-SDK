import { CSSProperties } from 'react'

export function LimeAura({
  size = 600,
  opacity = 0.2,
  pulse = false,
  className = '',
  style,
}: {
  size?: number
  opacity?: number
  pulse?: boolean
  className?: string
  style?: CSSProperties
}) {
  return (
    <div
      aria-hidden
      className={`pointer-events-none absolute rounded-full blur-[120px] ${pulse ? 'animate-aura-pulse' : ''} ${className}`}
      style={{
        width: size,
        height: size,
        background: '#c8ff00',
        opacity,
        willChange: 'opacity',
        ...style,
      }}
    />
  )
}
