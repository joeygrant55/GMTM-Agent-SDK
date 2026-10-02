import nextDynamic from 'next/dynamic'
import { isProfileSurface } from '@/lib/backend-config.cjs'

// Session hooks run client-side only
const HomeClient = nextDynamic(() => import('./HomeClient'), { ssr: false })
const ProfileWorkspace = nextDynamic(() => import('./components/ProfileWorkspace'), { ssr: false })

export default function HomePage() {
  // The middleware already required a SPARQ session. Profile: /home is the journey Home.
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) return <ProfileWorkspace view="home" />
  return <HomeClient />
}
