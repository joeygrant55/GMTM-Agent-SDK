import WorkspaceShell from './components/WorkspaceShell'
import { Suspense } from 'react'
import CombineWorkspaceShell from './components/CombineWorkspaceShell'
import { isCombineSurface, isProfileSurface } from '@/lib/backend-config.cjs'
import ProfileWorkspaceShell from './components/ProfileWorkspaceShell'

export default function HomeLayout({
  children,
}: {
  children: React.ReactNode
}) {
  if (isProfileSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) {
    return <ProfileWorkspaceShell>{children}</ProfileWorkspaceShell>
  }
  if (isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) {
    return <Suspense fallback={<p role="status" className="p-6 text-gray-300">Loading your combine…</p>}><CombineWorkspaceShell>{children}</CombineWorkspaceShell></Suspense>
  }
  return <WorkspaceShell>{children}</WorkspaceShell>
}
