import dynamic from 'next/dynamic'
import { notFound } from 'next/navigation'
import { isProfileSurface } from '@/lib/backend-config.cjs'

const ProfileEmails = dynamic(() => import('../components/ProfileColleges').then(m => m.ProfileEmails), { ssr: false })

// Profile surface only (the middleware also denies it elsewhere on restricted surfaces).
export default function Page() {
  if (!isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) notFound()
  return <ProfileEmails />
}
