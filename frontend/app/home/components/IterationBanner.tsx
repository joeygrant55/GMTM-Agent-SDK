'use client'

import { ARTIFACT_TYPE_LABEL, Artifact } from './artifactStatus'

interface Props {
  artifact: Pick<Artifact, 'id' | 'type' | 'title' | 'agent_id'>
  onExit: () => void
}

export default function IterationBanner({ artifact, onExit }: Props) {
  const typeLabel = ARTIFACT_TYPE_LABEL[artifact.type] ?? 'Artifact'
  const titleText = artifact.title || typeLabel
  return (
    <div className="px-4 py-2 bg-sparq-lime/10 border-b border-sparq-lime/20 flex items-center justify-between">
      <div className="text-xs text-sparq-lime font-medium truncate">
        💬 Iterating: <span className="font-bold">{typeLabel}</span>
        <span className="text-sparq-lime/70"> — {titleText}</span>
      </div>
      <button
        onClick={onExit}
        className="text-[11px] text-sparq-lime/80 hover:text-white transition-colors shrink-0 ml-3"
        title="Exit iteration mode"
      >
        ✕ Unscope
      </button>
    </div>
  )
}
