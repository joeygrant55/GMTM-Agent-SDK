import type { Metadata } from 'next'
import { ClerkProvider } from '@clerk/nextjs'
import './globals.css'

export const metadata: Metadata = {
  title: 'SPARQ Agent - Your AI Recruiting Coordinator',
  description: '24/7 AI agent helping athletes get recruited',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  const clerkKey = process.env.NEXT_PUBLIC_CLERK_PUBLISHABLE_KEY

  if (clerkKey) {
    return (
      <ClerkProvider publishableKey={clerkKey}>
        <html lang="en">
          <body className="bg-gray-50">{children}</body>
        </html>
      </ClerkProvider>
    )
  }

  return (
    <html lang="en">
      <body className="bg-gray-50">{children}</body>
    </html>
  )
}
