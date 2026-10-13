import { notFound } from 'next/navigation'
import { isProfileSurface } from '@/lib/backend-config.cjs'

// A static import: a lazy page waits for React's Suspense reveal delay (about 0.7 s measured live, 2026-10-13).
import ProfileWorkspace from '../components/ProfileWorkspace'

// Profile surface only (the middleware also denies it elsewhere on restricted surfaces).
export default function Page() {
  if (!isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) notFound()
  return <ProfileWorkspace view="progress" />
}
