import nextDynamic from 'next/dynamic'
import { redirect } from 'next/navigation'
import { isProfileSurface } from '@/lib/backend-config.cjs'

// Session hooks run client-side only
const HomeClient = nextDynamic(() => import('./HomeClient'), { ssr: false })

export default function HomePage() {
  // The middleware already required a SPARQ session.
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) redirect('/home/inbox')
  return <HomeClient />
}
