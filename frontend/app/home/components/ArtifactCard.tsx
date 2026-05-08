'use client'

import { useRouter } from 'next/navigation'
import { Artifact, ARTIFACT_TYPE_ICON } from './artifactStatus'
import SpecialistAvatar from './SpecialistAvatar'
import ArtifactStatusPill from './ArtifactStatusPill'

function timeAgo(iso: string | null): string {
  if (!iso) return ''
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const diff = Math.max(0, Date.now() - t)
  const m = Math.floor(diff / 60000)
  if (m < 1) return 'just now'
  if (m < 60) return `${m}m ago`
  const h = Math.floor(m / 60)
  if (h < 24) return `${h}h ago`
  const d = Math.floor(h / 24)
  return `${d}d ago`
}

interface Props {
  artifact: Artifact
  onApprove?: (id: number) => void
  onDiscard?: (id: number) => void
  pending?: boolean
}

export default function ArtifactCard({ artifact, onApprove, onDiscard, pending }: Props) {
  const router = useRouter()
  const icon = ARTIFACT_TYPE_ICON[artifact.type] ?? '📄'
  const approveLabel = artifact.type === 'outreach_draft' ? 'Approve & send' : 'Approve'

  const open = () => router.push(`/home/artifact/${artifact.id}`)

  return (
    <div className="bg-white/[0.04] border border-white/10 rounded-2xl p-5 hover:border-sparq-lime/30 transition-colors">
      <div className="flex items-center justify-between mb-3">
        <div className="flex items-center gap-3">
          <SpecialistAvatar agentId={artifact.agent_id} />
          <span className="text-xs text-gray-500">{timeAgo(artifact.updated_at)}</span>
        </div>
        <ArtifactStatusPill artifact={artifact} />
      </div>

      <button onClick={open} className="block w-full text-left">
        <h3 className="font-bold text-white text-base flex items-center gap-2">
          <span aria-hidden>{icon}</span>
          <span>{artifact.title || 'Untitled artifact'}</span>
        </h3>
        {artifact.summary && (
          <p className="text-sm text-gray-400 mt-1.5 line-clamp-2">{artifact.summary}</p>
        )}
      </button>

      {artifact.sources?.length > 0 && (
        <div className="mt-3 flex flex-wrap gap-1.5">
          {artifact.sources.slice(0, 3).map((s, i) => (
            <span key={i} className="text-[10px] text-gray-500 bg-white/[0.03] border border-white/5 rounded px-1.5 py-0.5">
              {s.label}
            </span>
          ))}
          {artifact.sources.length > 3 && (
            <span className="text-[10px] text-gray-500">+{artifact.sources.length - 3} more</span>
          )}
        </div>
      )}

      <div className="mt-4 flex items-center gap-2">
        <button
          onClick={open}
          className="text-xs px-3 py-1.5 rounded-lg bg-white/[0.06] border border-white/10 text-white hover:bg-white/[0.1]"
        >
          Open
        </button>
        <button
          onClick={() => onApprove?.(artifact.id)}
          disabled={pending}
          className="text-xs px-3 py-1.5 rounded-lg bg-sparq-lime text-sparq-charcoal font-bold hover:bg-sparq-lime-light disabled:opacity-40"
        >
          {approveLabel}
        </button>
        <button
          onClick={() => onDiscard?.(artifact.id)}
          disabled={pending}
          className="text-xs px-3 py-1.5 rounded-lg text-gray-400 hover:text-red-300 disabled:opacity-40"
        >
          Discard
        </button>
      </div>
    </div>
  )
}
