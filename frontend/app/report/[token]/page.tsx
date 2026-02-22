import { Metadata } from 'next'
import PublicReportClient from './PublicReportClient'

interface PageProps {
  params: Promise<{ token: string }>
}

export async function generateMetadata({ params }: PageProps): Promise<Metadata> {
  const { token } = await params
  const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'https://sparq-agent-backend.up.railway.app'

  try {
    const res = await fetch(`${backendUrl}/api/reports/public/${token}`, {
      next: { revalidate: 3600 },
    })
    if (!res.ok) throw new Error('not found')
    const report = await res.json()

    const athleteName = [report.first_name, report.last_name].filter(Boolean).join(' ')
    const title = report.title || `${athleteName} — SPARQ Report`
    const description = report.summary || `AI-generated recruiting report for ${athleteName}. Powered by SPARQ Agent.`

    return {
      title: `${title} | SPARQ Agent`,
      description,
      openGraph: {
        title,
        description,
        siteName: 'SPARQ Agent',
        type: 'article',
      },
      twitter: {
        card: 'summary_large_image',
        title,
        description,
      },
    }
  } catch {
    return {
      title: 'SPARQ Report | SPARQ Agent',
      description: 'AI-powered athlete recruiting report by SPARQ Agent.',
    }
  }
}

export default async function PublicReportPage({ params }: PageProps) {
  const { token } = await params
  return <PublicReportClient token={token} />
}
