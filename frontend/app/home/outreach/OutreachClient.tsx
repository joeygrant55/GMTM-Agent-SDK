import dynamic from 'next/dynamic'

const OutreachClient = dynamic(() => import('./OutreachClient'), { ssr: false })

export default function OutreachPage() {
  return <OutreachClient />
}
