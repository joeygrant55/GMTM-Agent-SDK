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
  return (
    <ClerkProvider>
      <html lang="en">
        <body className="bg-gray-50">{children}</body>
      </html>
    </ClerkProvider>
  )
}
