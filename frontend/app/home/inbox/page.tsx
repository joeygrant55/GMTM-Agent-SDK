import dynamic from 'next/dynamic'
import { isCombineSurface, isProfileSurface } from '@/lib/backend-config.cjs'

const InboxFeed = dynamic(() => import('../components/InboxFeed'), { ssr: false })
const CombineInbox = dynamic(() => import('../components/CombineInbox'), { ssr: false })
const ProfileWorkspace = dynamic(() => import('../components/ProfileWorkspace'), { ssr: false })

export default function InboxPage() {
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <ProfileWorkspace />
  if (isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <CombineInbox />
  return <InboxFeed />
}
