import dynamic from 'next/dynamic'
import { redirect } from 'next/navigation'
import { isCombineSurface, isProfileSurface } from '@/lib/backend-config.cjs'

const InboxFeed = dynamic(() => import('../components/InboxFeed'), { ssr: false })
const CombineInbox = dynamic(() => import('../components/CombineInbox'), { ssr: false })

export default function InboxPage() {
  // Old profile links (/home/inbox) land on the journey Home.
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) redirect('/home')
  if (isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <CombineInbox />
  return <InboxFeed />
}
