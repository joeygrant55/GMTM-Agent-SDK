import dynamic from 'next/dynamic'

const InboxFeed = dynamic(() => import('../components/InboxFeed'), { ssr: false })

export default function InboxPage() {
  return <InboxFeed />
}
