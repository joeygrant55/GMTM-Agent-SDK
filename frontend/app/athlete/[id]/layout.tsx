import { Metadata } from 'next'

interface Props {
  params: { id: string }
  children: React.ReactNode
}

export async function generateMetadata({ params }: Props): Promise<Metadata> {
  const id = params.id
  const ogUrl = `https://sparq-agent.vercel.app/api/og/athlete?name=SPARQ+Athlete&sport=Football&position=ATH&rating=0`

  // Try to fetch athlete data for dynamic meta
  let title = `Athlete ${id} — SPARQ Agent`
  let description = 'AI-powered recruiting profile — powered by SPARQ Agent'
  let dynamicOg = ogUrl

  try {
    const backendUrl = process.env.NEXT_PUBLIC_BACKEND_URL || 'http://localhost:8000'
    const res = await fetch(`${backendUrl}/api/athlete/${id}`, { next: { revalidate: 300 } })
    if (res.ok) {
      const data = await res.json()
      const name = `${data.first_name} ${data.last_name}`
      title = `${name} — SPARQ Agent`
      description = `${name} | ${data.position || 'Athlete'} | AI-powered recruiting profile`
      const ogParams = new URLSearchParams({
        name,
        sport: data.sport || 'Football',
        position: data.position || 'ATH',
        rating: '0',
      })
      dynamicOg = `https://sparq-agent.vercel.app/api/og/athlete?${ogParams.toString()}`
    }
  } catch {
    // Fall through to defaults
  }

  return {
    title,
    description,
    openGraph: {
      title,
      description,
      images: [{ url: dynamicOg, width: 1200, height: 630, alt: title }],
      type: 'profile',
      siteName: 'SPARQ Agent',
    },
    twitter: {
      card: 'summary_large_image',
      title,
      description,
      images: [dynamicOg],
    },
  }
}

export default function AthleteLayout({ children }: Props) {
  return <>{children}</>
}
