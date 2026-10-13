import nextDynamic from 'next/dynamic'
import { isProfileSurface } from '@/lib/backend-config.cjs'
// A static import: a lazy page waits for React's Suspense reveal delay (about 0.7 s measured live, 2026-10-13).
import ProfileWorkspace from './components/ProfileWorkspace'

// Session hooks run client-side only
const HomeClient = nextDynamic(() => import('./HomeClient'), { ssr: false })

export default function HomePage() {
  // The middleware already required a SPARQ session. Profile: /home is the journey Home.
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <ProfileWorkspace view="home" />
  return <HomeClient />
}
