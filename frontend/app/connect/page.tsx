import ConnectClient from './ConnectClient'
import CombineConnectionRecovery from './CombineConnectionRecovery'
import { isRestrictedSurface, isProfileSurface } from '@/lib/backend-config.cjs'

export const dynamic = 'force-dynamic'

export const metadata = {
  title: 'Connect Your Profile | SPARQ Agent',
  description: 'Link your GMTM athlete profile to SPARQ Agent.',
}

export default function ConnectPage({ searchParams }: { searchParams?: Record<string, string | string[] | undefined> }) {
  // This is only a public combine choice, never an athlete or return URL.
  // Repeated and unsupported values must not silently choose a division.
  const requestedEvent = searchParams?.event_id
  const eventId = requestedEvent === '1317' ? 1317 : requestedEvent === '1318' ? 1318 : null
  if (isRestrictedSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <CombineConnectionRecovery eventId={eventId} profileMode={isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)} />
  return <ConnectClient eventId={eventId} />
}
