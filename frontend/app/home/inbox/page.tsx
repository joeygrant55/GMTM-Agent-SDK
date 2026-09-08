import dynamic from 'next/dynamic'
import { isCombineSurface } from '@/lib/backend-config.cjs'

const InboxFeed = dynamic(() => import('../components/InboxFeed'), { ssr: false })
const CombineInbox = dynamic(() => import('../components/CombineInbox'), { ssr: false })

export default function InboxPage() {
  if (isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <CombineInbox />
  return <InboxFeed />
}
