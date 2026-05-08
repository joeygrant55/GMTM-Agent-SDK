'use client'

import { SPECIALISTS, SpecialistId } from './artifactStatus'

interface Props {
  agentId: SpecialistId | string | null | undefined
  size?: 'sm' | 'md'
  showName?: boolean
}

export default function SpecialistAvatar({ agentId, size = 'sm', showName = true }: Props) {
  const meta = (agentId && SPECIALISTS[agentId as SpecialistId]) || null
  const emoji = meta?.emoji ?? '🤖'
  const name = meta?.name ?? 'Agent'
  const dim = size === 'md' ? 'w-9 h-9 text-base' : 'w-7 h-7 text-sm'

  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`${dim} inline-flex items-center justify-center rounded-xl bg-sparq-lime/10 border border-sparq-lime/20 leading-none`}
        title={meta?.blurb ?? 'Agent'}
      >
        {emoji}
      </span>
      {showName && <span className="text-xs text-gray-300 font-medium">{name}</span>}
    </span>
  )
}
