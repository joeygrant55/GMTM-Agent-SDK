import dynamic from 'next/dynamic'

const WorkspaceSidebar = dynamic(() => import('./components/WorkspaceSidebar'), { ssr: false })
const WorkspaceAIPanel = dynamic(() => import('./components/WorkspaceAIPanel'), { ssr: false })

export default function HomeLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="h-screen overflow-hidden flex bg-sparq-charcoal font-display">
      <WorkspaceSidebar />
      <main className="flex-1 overflow-y-auto">{children}</main>
      <WorkspaceAIPanel />
    </div>
  )
}
