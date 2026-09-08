import WorkspaceShell from './components/WorkspaceShell'
import { Suspense } from 'react'
import CombineWorkspaceShell from './components/CombineWorkspaceShell'
import { isCombineSurface } from '@/lib/backend-config.cjs'

export default function HomeLayout({
  children,
}: {
  children: React.ReactNode
}) {
  if (isCombineSurface(process.env.NEXT_PUBLIC_APP_SURFACE)) {
    return <Suspense fallback={<p role="status" className="p-6 text-gray-300">Loading your combine…</p>}><CombineWorkspaceShell>{children}</CombineWorkspaceShell></Suspense>
  }
  return <WorkspaceShell>{children}</WorkspaceShell>
}
