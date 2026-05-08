'use client'

import { Artifact, pillForArtifact } from './artifactStatus'

export default function ArtifactStatusPill({ artifact }: { artifact: Pick<Artifact, 'state' | 'type'> }) {
  const style = pillForArtifact(artifact.state, artifact.type)
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-md text-[10px] uppercase tracking-wide font-bold ${style.className}`}>
      {style.label}
    </span>
  )
}
