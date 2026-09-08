import WorkspaceShell from './components/WorkspaceShell'

export default function HomeLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return <WorkspaceShell>{children}</WorkspaceShell>
}
