import dynamic from 'next/dynamic'

const TimelineClient = dynamic(() => import('./TimelineClient'), { ssr: false })

export default function TimelinePage() {
  return <TimelineClient />
}
