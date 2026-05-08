'use client'

import { useParams } from 'next/navigation'
import dynamic from 'next/dynamic'

const ArtifactViewer = dynamic(() => import('../../components/ArtifactViewer'), { ssr: false })

export default function ArtifactPage() {
  const params = useParams()
  const idParam = Array.isArray(params?.id) ? params.id[0] : params?.id
  const artifactId = Number(idParam)
  if (!Number.isFinite(artifactId)) {
    return <div className="p-8 text-gray-400">Invalid artifact id.</div>
  }
  return <ArtifactViewer artifactId={artifactId} />
}
