import nextDynamic from 'next/dynamic'
import { redirect } from 'next/navigation'
import { isProfileSurface } from '@/lib/backend-config.cjs'

// Clerk hooks cannot run during SSR — load home content client-side only
const HomeClient = nextDynamic(() => import('./HomeClient'), { ssr: false })

export default function HomePage() {
  // Profile has no Clerk; the middleware already required a SPARQ session.
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) redirect('/home/inbox')
  return <HomeClient />
}
